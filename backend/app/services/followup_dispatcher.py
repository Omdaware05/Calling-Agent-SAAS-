"""
Automatic follow-up dispatcher.

Every minute it looks for follow-ups whose scheduled time has arrived
(status pending/scheduled) and places the outbound call through the
normal CallService path — the same one the UI's quick-dial uses. No API
keys and no external scheduler: it is a plain asyncio loop started in
the FastAPI lifespan.

Outcomes are written back onto the follow-up itself:
- success -> status 'completed', note records the new call id;
- failure -> an attempt marker is appended; after 3 failed attempts
  the follow-up is 'cancelled' so a broken number cannot loop forever.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models.call import Call
from app.models.lead import Followup
from app.schemas.call import InitiateCallRequest
from app.services.call_service import CallService

logger = logging.getLogger(__name__)

ATTEMPT_MARKER = "Auto-call attempt"
MAX_ATTEMPTS = 3
POLL_SECONDS = 60
PROCESSING_STALE_MINUTES = 10
CALL_STALE_MINUTES = 10


def _as_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    # Rows written by older code paths can be naive; they were recorded
    # against UTC clocks, so interpret them as UTC.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


async def _housekeeping() -> None:
    """Per-tick maintenance that used to hide inside read endpoints or
    not happen at all:
    1. sync qualifying finished calls (busy / no-answer / failed) into
       retry follow-ups — this ran inside GET /followups before, so
       merely VIEWING the Follow-ups page created rows the dispatcher
       would then dial;
    2. un-stick follow-ups claimed by a worker that died mid-call
       (status 'processing' older than the stale window -> pending);
    3. expire outbound calls stuck in initiating/ringing (e.g. VoBiz
       calls that were never answered never open their media stream, so
       nothing else ever finalizes them).
    """
    try:
        from app.api.routes.followups import sync_qualifying_calls_to_followups

        async with AsyncSessionLocal() as session:
            await sync_qualifying_calls_to_followups(session)
    except Exception as e:
        logger.warning(f"Dispatcher housekeeping (followup sync) failed: {e}")

    now = datetime.now(UTC)
    try:
        async with AsyncSessionLocal() as session:
            stale_processing = now - timedelta(minutes=PROCESSING_STALE_MINUTES)
            await session.execute(
                update(Followup)
                .where(Followup.status == "processing", Followup.updated_at <= stale_processing)
                .values(status="pending")
            )
            stale_call_cutoff = now - timedelta(minutes=CALL_STALE_MINUTES)
            res = await session.execute(
                update(Call)
                .where(
                    Call.status.in_(["initiating", "ringing"]),
                    Call.created_at <= stale_call_cutoff,
                )
                .values(status="failed", termination_reason="expired_unanswered", ended_at=now)
            )
            await session.commit()
            if res.rowcount:
                logger.info(f"Expired {res.rowcount} stale unanswered call(s).")
    except Exception as e:
        logger.warning(f"Dispatcher housekeeping (stale sweep) failed: {e}")


async def dispatch_due_followups() -> int:
    """Place calls for every follow-up that is due. Returns calls placed."""
    placed = 0
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Followup)
            .where(
                Followup.status.in_(["pending", "scheduled"]),
                Followup.scheduled_at.isnot(None),
                Followup.scheduled_at <= now,
            )
            .order_by(Followup.scheduled_at.asc())
            .limit(50)
        )
        rows = list((await session.execute(stmt)).scalars().all())
        # Work with plain ids from here: initiate_call commits/rolls back
        # on this shared session, which EXPIRES every ORM object loaded
        # earlier — touching a stale object's attributes on a later
        # iteration then triggers a lazy load outside an await
        # (MissingGreenlet) and kills the tick mid-loop.
        due_ids = [f.id for f in rows if (_as_aware(f.scheduled_at) or now) <= now]

        for followup_id in due_ids:
            followup = await session.get(Followup, followup_id)
            if followup is None:
                continue
            try:
                # Atomic claim: flip to 'processing' in a conditional
                # UPDATE first. Two workers (or a crash between placing
                # the call and committing) used to be able to dial the
                # same customer twice; now only the worker whose UPDATE
                # matched may call. The claim lives INSIDE the per-row
                # try: a transient DB error on one row must never abort
                # the whole tick for the remaining rows.
                claim = await session.execute(
                    update(Followup)
                    .where(
                        Followup.id == followup.id,
                        Followup.status.in_(["pending", "scheduled"]),
                    )
                    .values(status="processing")
                )
                await session.commit()
                if not claim.rowcount:
                    continue
                await session.refresh(followup)
            except Exception as claim_err:
                await session.rollback()
                logger.warning(f"Auto-callback claim failed for follow-up {followup.id}: {claim_err}")
                continue

            # Snapshot the fields initiate_call needs BEFORE calling it:
            # initiate commits/rolls back on this session, expiring the
            # ORM object — reading its attributes afterwards can trigger
            # a lazy load outside an await (MissingGreenlet).
            attempts = (followup.notes or "").count(ATTEMPT_MARKER)
            notes_snapshot = followup.notes or ""
            req_fields = {
                "phone_number": followup.phone_number,
                "agent_id": followup.agent_id,
                "tenant_id": followup.tenant_id,
                "contact_id": followup.contact_id,
            }
            try:
                if not req_fields["agent_id"]:
                    raise ValueError("follow-up has no agent assigned")
                if not req_fields["phone_number"]:
                    raise ValueError("follow-up has no phone number")
                call = await CallService.initiate_call(
                    session,
                    InitiateCallRequest(
                        **req_fields,
                        initial_context={
                            "auto_callback": True,
                            "followup_id": followup_id,
                            "reason": "Customer-requested callback (auto-scheduled)",
                        },
                    ),
                )
                # Re-load (awaited) before mutating: the object was
                # expired by initiate_call's internal commits.
                await session.refresh(followup)
                followup.status = "completed"
                followup.notes = (
                    notes_snapshot
                    + f" | Auto-call placed {now.strftime('%d %b %Y, %H:%M UTC')} (call {call.id})."
                )
                await session.commit()
                placed += 1
                logger.info(f"Auto-callback placed for follow-up {followup_id} -> call {call.id}")
            except Exception as e:
                await session.rollback()
                attempts += 1
                try:
                    await session.refresh(followup)
                    followup.notes = (
                        notes_snapshot
                        + f" | {ATTEMPT_MARKER} {attempts} failed {now.strftime('%d %b %Y, %H:%M UTC')}: {type(e).__name__}"
                    )
                    # Release the claim so the next tick can retry —
                    # unless the attempt budget is exhausted.
                    followup.status = "cancelled" if attempts >= MAX_ATTEMPTS else "pending"
                    if attempts >= MAX_ATTEMPTS:
                        followup.notes += " Auto-call abandoned after 3 failed attempts."
                    await session.commit()
                except Exception:
                    await session.rollback()
                logger.warning(f"Auto-callback failed for follow-up {followup_id}: {e}")
    return placed


async def run_dispatcher_forever() -> None:
    logger.info("Follow-up dispatcher started (checks every 60s).")
    while True:
        try:
            await _housekeeping()
            placed = await dispatch_due_followups()
            if placed:
                logger.info(f"Follow-up dispatcher placed {placed} call(s).")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # never let one bad tick kill the loop
            logger.warning(f"Follow-up dispatcher tick failed: {e}")
        await asyncio.sleep(POLL_SECONDS)
