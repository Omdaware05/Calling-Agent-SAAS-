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
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.lead import Followup
from app.schemas.call import InitiateCallRequest
from app.services.call_service import CallService

logger = logging.getLogger(__name__)

ATTEMPT_MARKER = "Auto-call attempt"
MAX_ATTEMPTS = 3
POLL_SECONDS = 60


def _as_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    # Rows written by older code paths can be naive; they were recorded
    # against UTC clocks, so interpret them as UTC.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


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
        due = [f for f in rows if (_as_aware(f.scheduled_at) or now) <= now]

        for followup in due:
            attempts = (followup.notes or "").count(ATTEMPT_MARKER)
            try:
                if not followup.agent_id:
                    raise ValueError("follow-up has no agent assigned")
                if not followup.phone_number:
                    raise ValueError("follow-up has no phone number")
                call = await CallService.initiate_call(
                    session,
                    InitiateCallRequest(
                        phone_number=followup.phone_number,
                        agent_id=followup.agent_id,
                        tenant_id=followup.tenant_id,
                        contact_id=followup.contact_id,
                        initial_context={
                            "auto_callback": True,
                            "followup_id": followup.id,
                            "reason": "Customer-requested callback (auto-scheduled)",
                        },
                    ),
                )
                followup.status = "completed"
                followup.notes = (
                    (followup.notes or "")
                    + f" | Auto-call placed {now.strftime('%d %b %Y, %H:%M UTC')} (call {call.id})."
                )
                await session.commit()
                placed += 1
                logger.info(f"Auto-callback placed for follow-up {followup.id} -> call {call.id}")
            except Exception as e:
                await session.rollback()
                attempts += 1
                followup.notes = (
                    (followup.notes or "")
                    + f" | {ATTEMPT_MARKER} {attempts} failed {now.strftime('%d %b %Y, %H:%M UTC')}: {type(e).__name__}"
                )
                if attempts >= MAX_ATTEMPTS:
                    followup.status = "cancelled"
                    followup.notes += " Auto-call abandoned after 3 failed attempts."
                try:
                    await session.commit()
                except Exception:
                    await session.rollback()
                logger.warning(f"Auto-callback failed for follow-up {followup.id}: {e}")
    return placed


async def run_dispatcher_forever() -> None:
    logger.info("Follow-up dispatcher started (checks every 60s).")
    while True:
        try:
            placed = await dispatch_due_followups()
            if placed:
                logger.info(f"Follow-up dispatcher placed {placed} call(s).")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # never let one bad tick kill the loop
            logger.warning(f"Follow-up dispatcher tick failed: {e}")
        await asyncio.sleep(POLL_SECONDS)
