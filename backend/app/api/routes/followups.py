from datetime import UTC, datetime, timedelta
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.models.lead import Followup
from app.models.call import Call
from app.schemas.lead import FollowupResponse, UpdateFollowupRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/followups", tags=["followups"], dependencies=[Depends(verify_app_client)])


def map_followup_to_response(f: Followup) -> FollowupResponse:
    return FollowupResponse(
        id=f.id,
        followup_id=f.id,
        tenant_id=f.tenant_id,
        contact_id=f.contact_id,
        agent_id=f.agent_id,
        call_id=f.call_id,
        phone_number=f.phone_number,
        scheduled_at=f.scheduled_at.isoformat() if f.scheduled_at else None,
        status=f.status or "pending",
        notes=f.notes,
        created_at=f.created_at.isoformat() if f.created_at else datetime.now(UTC).isoformat(),
        updated_at=f.updated_at.isoformat() if f.updated_at else None,
    )


async def sync_qualifying_calls_to_followups(db: AsyncSession):
    """
    Evaluates all qualifying calls (busy, unanswered, failed, line busy, short disconnect)
    and ensures each has a corresponding Followup record in PostgreSQL.
    """
    try:
        qualifying_statuses = ["busy", "line_busy", "no_answer", "unanswered", "failed", "cancelled"]
        stmt = (
            select(Call)
            .where(
                (Call.status.in_(qualifying_statuses))
                | (Call.termination_reason.in_(qualifying_statuses))
                | ((Call.duration != None) & (Call.duration < 5.0) & (Call.status.notin_(["initiating", "ringing", "in_progress"])))
            )
            .order_by(Call.created_at.desc())
            .limit(100)
        )
        res = await db.execute(stmt)
        candidate_calls = res.scalars().all()

        if not candidate_calls:
            return

        candidate_ids = [c.id for c in candidate_calls]
        f_stmt = select(Followup.call_id).where(Followup.call_id.in_(candidate_ids))
        existing_call_ids = set((await db.execute(f_stmt)).scalars().all())

        new_count = 0
        now = datetime.now(UTC)

        for call in candidate_calls:
            if call.id in existing_call_ids:
                continue

            call_phone = call.phone_number or call.caller_number
            if not call_phone:
                continue

            st = (call.status or "").lower()
            term = (call.termination_reason or "").lower()

            if st in ("busy", "line_busy") or term in ("busy", "line_busy"):
                sched = now + timedelta(minutes=30)
                notes = "Category 2: PHONE / LINE BUSY. Status: busy. Action: Retry call after 30 minutes"
            elif st in ("no_answer", "unanswered") or term in ("no_answer", "unanswered"):
                sched = now + timedelta(minutes=60)
                notes = "Category 3: CALL NOT ANSWERED / NO RESPONSE. Status: no_answer. Action: Retry call in 1 hour"
            elif st in ("failed", "cancelled") or term in ("failed", "cancelled"):
                sched = now + timedelta(minutes=45)
                notes = f"Category 4: CALL DISCONNECTED WITHOUT CONVERSATION. Status: {call.status}. Action: Retry call in 45 minutes"
            else:
                sched = now + timedelta(minutes=60)
                notes = "Category 3: CALL NOT ANSWERED / NO RESPONSE. Action: Retry call in 1 hour. (Matched: 'Short call / no conversation')"

            new_f = Followup(
                tenant_id=call.tenant_id,
                contact_id=call.contact_id,
                agent_id=call.agent_id,
                call_id=call.id,
                phone_number=call_phone,
                scheduled_at=sched,
                status="pending",
                notes=notes,
                created_at=call.created_at or now,
            )
            db.add(new_f)
            existing_call_ids.add(call.id)
            new_count += 1

        if new_count > 0:
            await db.commit()
            logger.info(f"Auto-synced {new_count} qualifying calls into Followup table")
    except Exception as e:
        logger.warning(f"Notice during call-to-followup auto-sync: {e}")


@router.get("", response_model=List[FollowupResponse])
async def list_followups(
    agent_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    business_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List scheduled followups, automatically checking and syncing all qualifying calls.
    """
    # 1. Silently sync any recent busy / unanswered / failed calls into followups
    await sync_qualifying_calls_to_followups(db)

    t_id = tenant_id or business_id
    stmt = select(Followup).order_by(Followup.created_at.desc())
    if agent_id:
        stmt = stmt.where(Followup.agent_id == agent_id)
    if t_id:
        stmt = stmt.where(Followup.tenant_id == t_id)
    stmt = stmt.offset(skip).limit(limit)

    res = await db.execute(stmt)
    items = res.scalars().all()
    return [map_followup_to_response(f) for f in items]


@router.get("/{followup_id}", response_model=FollowupResponse)
async def get_followup(followup_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Followup).where(Followup.id == followup_id)
    res = await db.execute(stmt)
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Followup not found")
    return map_followup_to_response(f)


@router.patch("/{followup_id}", response_model=FollowupResponse)
async def update_followup(followup_id: str, payload: UpdateFollowupRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Followup).where(Followup.id == followup_id)
    res = await db.execute(stmt)
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Followup not found")

    if payload.status is not None:
        f.status = payload.status
    if payload.notes is not None:
        f.notes = payload.notes
    if payload.scheduled_at is not None:
        try:
            f.scheduled_at = datetime.fromisoformat(payload.scheduled_at.replace("Z", "+00:00"))
        except Exception:
            pass

    f.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(f)
    return map_followup_to_response(f)
