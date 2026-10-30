"""
Calendar API — what happened on any given date.

Powers the Calendar page: per-day counts for a whole month, and the
full detail (calls, leads, follow-ups) for one selected day. Pure SQL
aggregation over existing tables; no external services.

Note: dates are bucketed by the stored (UTC) timestamps, matching how
the rest of the backend records events.
"""

import calendar as _calendar
from datetime import date, datetime, time, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.datetime_utils import to_iso_utc
from app.dependencies import verify_app_client
from app.models.call import Call
from app.models.lead import Followup, Lead

router = APIRouter(prefix="/calendar", tags=["calendar"], dependencies=[Depends(verify_app_client)])


def _day_range(d: date):
    start = datetime.combine(d, time.min)
    return start, start + timedelta(days=1)


@router.get("/summary")
async def calendar_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Per-day counts of calls, leads and scheduled follow-ups for a month."""
    first = date(year, month, 1)
    last_day = _calendar.monthrange(year, month)[1]
    start = datetime.combine(first, time.min)
    end = datetime.combine(date(year, month, last_day), time.min) + timedelta(days=1)

    days: Dict[str, Dict[str, int]] = {}

    def bump(key: Any, field: str, count: int) -> None:
        if key is None:
            return
        k = str(key)
        entry = days.setdefault(k, {"calls": 0, "leads": 0, "followups": 0})
        entry[field] += int(count)

    for model, column, field in (
        (Call, Call.created_at, "calls"),
        (Lead, Lead.created_at, "leads"),
        (Followup, Followup.scheduled_at, "followups"),
    ):
        stmt = (
            select(func.date(column), func.count(model.id))
            .where(column >= start, column < end)
            .group_by(func.date(column))
        )
        for day_key, count in (await db.execute(stmt)).all():
            bump(day_key, field, count)

    return {"year": year, "month": month, "days": days}


@router.get("/day")
async def calendar_day(
    day: date = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Everything that happened on one date: calls, leads, follow-ups."""
    start, end = _day_range(day)

    calls = (
        await db.execute(
            select(Call)
            .where(Call.created_at >= start, Call.created_at < end)
            .order_by(Call.created_at.desc())
            .limit(200)
        )
    ).scalars().all()

    leads = (
        await db.execute(
            select(Lead)
            .where(Lead.created_at >= start, Lead.created_at < end)
            .order_by(Lead.created_at.desc())
            .limit(200)
        )
    ).scalars().all()

    followups = (
        await db.execute(
            select(Followup)
            .where(Followup.scheduled_at >= start, Followup.scheduled_at < end)
            .order_by(Followup.scheduled_at.asc())
            .limit(200)
        )
    ).scalars().all()

    return {
        "date": day.isoformat(),
        "calls": [
            {
                "call_id": c.id,
                "phone_number": c.phone_number,
                "agent_id": c.agent_id,
                "state": (c.status or "").upper(),
                "duration": c.duration,
                "created_at": to_iso_utc(c.created_at),
            }
            for c in calls
        ],
        "leads": [
            {
                "lead_id": l.id,
                "name": l.name,
                "phone_number": l.phone_number,
                "status": l.status,
                "score": l.score,
                "created_at": to_iso_utc(l.created_at),
            }
            for l in leads
        ],
        "followups": [
            {
                "followup_id": f.id,
                "phone_number": f.phone_number,
                "status": f.status,
                "notes": f.notes,
                "scheduled_at": to_iso_utc(f.scheduled_at),
            }
            for f in followups
        ],
    }
