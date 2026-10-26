import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import verify_app_client
from app.models.call import Call
from app.services.call_service import normalize_dograh_status, persist_post_call_artifacts, TERMINAL_STATES
from app.services.dograh_service import dograh_service
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stats"], dependencies=[Depends(verify_app_client)])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get aggregated call telemetry metrics for dashboard.
    """
    # Count calls by status
    stmt = select(Call.status, func.count(Call.id)).group_by(Call.status)
    res = await db.execute(stmt)
    counts = dict(res.all())

    total = sum(counts.values())
    queued = counts.get("initiating", 0)
    active = counts.get("in_progress", 0) + counts.get("ringing", 0)
    completed = counts.get("completed", 0)
    failed = counts.get("failed", 0)
    busy = counts.get("busy", 0)
    no_answer = counts.get("no_answer", 0)

    # Average duration
    dur_stmt = select(func.avg(Call.duration)).where(Call.duration.isnot(None))
    dur_res = await db.execute(dur_stmt)
    avg_dur = dur_res.scalar() or 0.0

    # Provider breakdown (Voxora primary carrier is VoBiz telephony)
    prov_counts: Dict[str, Dict[str, int]] = {
        "vobiz": {"total": total, "completed": completed, "failed": failed + busy + no_answer},
        "twilio": {"total": 0, "completed": 0, "failed": 0},
    }

    return {
        "total_calls": total,
        "queued": queued,
        "active": active,
        "completed": completed,
        "failed": failed,
        "busy": busy,
        "no_answer": no_answer,
        "average_duration_seconds": round(float(avg_dur), 1),
        "vobiz": prov_counts.get("vobiz", {"total": 0, "completed": 0, "failed": 0}),
        "twilio": prov_counts.get("twilio", {"total": 0, "completed": 0, "failed": 0}),
    }


@router.get("/active-calls")
async def get_active_calls(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    List currently live / in-flight voice calls.
    Immediately syncs live calls with Dograh so as soon as callee hangs up,
    the call transitions to completed and disappears from the live ringing/in-progress list.
    """
    stmt = (
        select(Call)
        .options(selectinload(Call.agent))
        .where(Call.status.in_(["initiating", "ringing", "in_progress"]))
        .order_by(Call.created_at.desc())
    )
    res = await db.execute(stmt)
    calls = list(res.scalars().all())

    needs_commit = False
    now_utc = datetime.now(UTC)

    for call in calls:
        # 1. Immediately expire any stale calls older than 4 minutes
        created = call.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if created and (now_utc - created > timedelta(minutes=4)):
            call.status = "failed"
            call.ended_at = now_utc
            needs_commit = True
            try:
                await redis_service.update_call_status(call.id, "failed")
                if call.agent_id:
                    await redis_service.release_concurrency_slot(call.agent_id)
            except Exception:
                pass
            continue

        # 2. Only query Dograh if running in Dograh engine mode and run_id exists
        voice_engine = getattr(settings, "VOICE_ENGINE", "sarvam").lower()
        has_run = bool(call.dograh_run_id)

        if voice_engine != "sarvam" and has_run and call.agent and call.agent.dograh_workflow_id:
            try:
                run_data = await asyncio.wait_for(
                    dograh_service.get_run_details(call.agent.dograh_workflow_id, call.dograh_run_id),
                    timeout=0.6,
                )
                if run_data:
                    is_completed = run_data.get("is_completed", False)
                    callbacks = (run_data.get("logs") or {}).get("telephony_status_callbacks", [])
                    if callbacks:
                        latest = callbacks[-1]
                        raw_st = latest.get("status")
                        new_status = normalize_dograh_status(raw_st)
                        if new_status != call.status:
                            call.status = new_status
                            needs_commit = True
                        if "duration" in latest and latest["duration"]:
                            try:
                                call.duration = float(latest["duration"])
                            except Exception:
                                pass
                    if is_completed and call.status not in TERMINAL_STATES:
                        call.status = "completed"
                        needs_commit = True
                    if call.status in TERMINAL_STATES:
                        if not call.ended_at:
                            call.ended_at = now_utc
                        needs_commit = True
                        try:
                            await redis_service.update_call_status(call.id, call.status, duration=call.duration)
                            if call.agent_id:
                                await redis_service.release_concurrency_slot(call.agent_id)
                        except Exception:
                            pass
                        await persist_post_call_artifacts(db, call, run_data)
            except Exception as e:
                logger.debug(f"Live sync notice for call {call.id}: {e}")

    if needs_commit:
        try:
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to commit stale call status updates: {e}")

    state_map = {
        "initiating": "QUEUED",
        "ringing": "RINGING",
        "in_progress": "CONNECTED",
    }

    # Return only still-active calls after sync
    items = [
        {
            "call_id": c.id,
            "phone_number": c.phone_number,
            "provider": (c.context_data or {}).get("provider", "vobiz"),
            "state": state_map.get(c.status, "RINGING"),
            "duration": c.duration or 0.0,
            "agent_id": c.agent_id,
        }
        for c in calls
        if c.status not in TERMINAL_STATES
    ]

    return {
        "active_count": len(items),
        "calls": items,
    }


@router.get("/queue")
async def get_queue(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Queue runner status with real-time queued calls count.
    """
    stmt = select(func.count(Call.id)).where(Call.status.in_(["initiating", "queued"]))
    res = await db.execute(stmt)
    queued_count = res.scalar() or 0

    return {
        "queued_count": queued_count,
        "is_running": True,
        "stop_requested": False,
    }


@router.get("/stats/providers")
async def get_provider_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Provider breakdown calculated dynamically from real database records.
    """
    total_stmt = select(func.count(Call.id))
    completed_stmt = select(func.count(Call.id)).where(Call.status == "completed")
    failed_stmt = select(func.count(Call.id)).where(Call.status.in_(["failed", "busy", "no_answer"]))

    total = (await db.execute(total_stmt)).scalar() or 0
    completed = (await db.execute(completed_stmt)).scalar() or 0
    failed = (await db.execute(failed_stmt)).scalar() or 0

    return {
        "vobiz": {"total": total, "completed": completed, "failed": failed},
        "twilio": {"total": 0, "completed": 0, "failed": 0},
    }
