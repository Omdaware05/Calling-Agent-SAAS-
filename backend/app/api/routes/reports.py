import csv
from datetime import UTC, datetime, timedelta
import io
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.models.tenant import Tenant
from app.models.call import Call
from app.models.lead import Lead
from app.models.agent import Agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(verify_app_client)])


@router.get("")
@router.get("/summary")
async def get_general_report(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - timedelta(days=days)
    calls_stmt = select(Call).where(Call.created_at >= since)
    calls_res = await db.execute(calls_stmt)
    calls = list(calls_res.scalars().all())

    leads_stmt = select(Lead).where(Lead.created_at >= since)
    leads_res = await db.execute(leads_stmt)
    leads = list(leads_res.scalars().all())

    total_calls = len(calls)
    completed_calls = sum(1 for c in calls if c.status == "completed")
    failed_calls = sum(1 for c in calls if c.status in ("failed", "busy", "no_answer"))
    durations = [c.duration for c in calls if c.duration is not None]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

    total_leads = len(leads)
    qualified_leads = sum(1 for l in leads if l.status in ("qualified", "interested"))
    conversion_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    return {
        "days": days,
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "failed_calls": failed_calls,
        "average_duration_seconds": avg_duration,
        "total_leads": total_leads,
        "qualified_leads": qualified_leads,
        "conversion_rate_percent": conversion_rate,
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/business/{business_id}")
async def get_business_report(
    business_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).where(Tenant.id == business_id)
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    biz_name = tenant.name if tenant else "Business"

    since = datetime.now(UTC) - timedelta(days=days)

    calls_stmt = select(Call).where(Call.tenant_id == business_id, Call.created_at >= since)
    calls_res = await db.execute(calls_stmt)
    calls = calls_res.scalars().all()

    leads_stmt = select(Lead).where(Lead.tenant_id == business_id, Lead.created_at >= since)
    leads_res = await db.execute(leads_stmt)
    leads = leads_res.scalars().all()

    agents_res = await db.execute(select(Agent))
    agent_map = {a.id: a.name for a in agents_res.scalars().all()}

    total_calls = len(calls)
    completed_calls = sum(1 for c in calls if c.status == "completed")
    failed_calls = sum(1 for c in calls if c.status in ("failed", "busy", "no_answer"))
    durations = [c.duration for c in calls if c.duration is not None]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0
    answer_rate = round((completed_calls / total_calls * 100), 1) if total_calls > 0 else 0.0

    total_leads = len(leads)
    qualified_leads = sum(1 for l in leads if l.status in ("qualified", "interested"))
    hot_leads = sum(1 for l in leads if (l.score and l.score >= 70) or l.status == "hot")
    converted_leads = sum(1 for l in leads if l.status in ("converted", "closed_won"))
    qualification_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0
    conversion_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    lead_status_distribution: Dict[str, int] = {}
    for l in leads:
        st = l.status or "new"
        lead_status_distribution[st] = lead_status_distribution.get(st, 0) + 1

    agent_performance: Dict[str, Dict[str, int]] = {}
    for c in calls:
        ag_name = agent_map.get(c.agent_id, c.agent_id or "Direct Calling Agent")
        if ag_name not in agent_performance:
            agent_performance[ag_name] = {"calls": 0, "completed": 0, "leads": 0, "qualified": 0}
        agent_performance[ag_name]["calls"] += 1
        if c.status == "completed":
            agent_performance[ag_name]["completed"] += 1

    for l in leads:
        # Credit each lead to ITS OWN agent (this used to dump every lead
        # on the first agent in the dict, making per-agent reports wrong
        # whenever more than one agent existed).
        ag_name = agent_map.get(l.agent_id, l.agent_id or "Direct Calling Agent")
        if ag_name not in agent_performance:
            agent_performance[ag_name] = {"calls": 0, "completed": 0, "leads": 0, "qualified": 0}
        agent_performance[ag_name]["leads"] += 1
        if l.status in ("qualified", "interested"):
            agent_performance[ag_name]["qualified"] += 1

    dispositions: Dict[str, int] = {}
    for c in calls:
        d = c.disposition or c.status or "unknown"
        dispositions[d] = dispositions.get(d, 0) + 1

    return {
        "report_id": f"rep-{business_id[:8]}-{int(datetime.now(UTC).timestamp())}",
        "business_id": business_id,
        "business_name": biz_name,
        "period_days": days,
        "days": days,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "failed_calls": failed_calls,
            "answer_rate": answer_rate,
            "avg_duration_seconds": avg_duration,
            "average_duration_seconds": avg_duration,
            "total_leads": total_leads,
            "qualified_leads": qualified_leads,
            "hot_leads": hot_leads,
            "converted_leads": converted_leads,
            "qualification_rate": qualification_rate,
            "conversion_rate": conversion_rate,
        },
        "lead_status_distribution": lead_status_distribution,
        "agent_performance": agent_performance,
        "timeline": [],
        "dispositions": dispositions,
    }


@router.get("/agency/overview")
async def get_agency_overview(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - timedelta(days=days)

    calls_stmt = select(Call).where(Call.created_at >= since)
    calls_res = await db.execute(calls_stmt)
    calls = calls_res.scalars().all()

    leads_stmt = select(Lead).where(Lead.created_at >= since)
    leads_res = await db.execute(leads_stmt)
    leads = leads_res.scalars().all()

    agents_res = await db.execute(select(Agent))
    agent_map = {a.id: a.name for a in agents_res.scalars().all()}

    total_calls = len(calls)
    completed_calls = sum(1 for c in calls if c.status == "completed")
    failed_calls = sum(1 for c in calls if c.status in ("failed", "busy", "no_answer"))
    durations = [c.duration for c in calls if c.duration is not None]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0
    answer_rate = round((completed_calls / total_calls * 100), 1) if total_calls > 0 else 0.0

    total_leads = len(leads)
    qualified_leads = sum(1 for l in leads if l.status in ("qualified", "interested"))
    hot_leads = sum(1 for l in leads if (l.score and l.score >= 70) or l.status == "hot")
    converted_leads = sum(1 for l in leads if l.status in ("converted", "closed_won"))
    qualification_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0
    conversion_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    lead_status_distribution: Dict[str, int] = {}
    for l in leads:
        st = l.status or "new"
        lead_status_distribution[st] = lead_status_distribution.get(st, 0) + 1

    agent_performance: Dict[str, Dict[str, int]] = {}
    for c in calls:
        ag_name = agent_map.get(c.agent_id, c.agent_id or "Direct Calling Agent")
        if ag_name not in agent_performance:
            agent_performance[ag_name] = {"calls": 0, "completed": 0, "leads": 0, "qualified": 0}
        agent_performance[ag_name]["calls"] += 1
        if c.status == "completed":
            agent_performance[ag_name]["completed"] += 1

    for l in leads:
        # Credit each lead to ITS OWN agent (this used to dump every lead
        # on the first agent in the dict, making per-agent reports wrong
        # whenever more than one agent existed).
        ag_name = agent_map.get(l.agent_id, l.agent_id or "Direct Calling Agent")
        if ag_name not in agent_performance:
            agent_performance[ag_name] = {"calls": 0, "completed": 0, "leads": 0, "qualified": 0}
        agent_performance[ag_name]["leads"] += 1
        if l.status in ("qualified", "interested"):
            agent_performance[ag_name]["qualified"] += 1

    dispositions: Dict[str, int] = {}
    for c in calls:
        d = c.disposition or c.status or "unknown"
        dispositions[d] = dispositions.get(d, 0) + 1

    return {
        "report_id": f"rep-agency-{int(datetime.now(UTC).timestamp())}",
        "business_id": "all",
        "business_name": "Agency Overview",
        "period_days": days,
        "days": days,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "failed_calls": failed_calls,
            "answer_rate": answer_rate,
            "avg_duration_seconds": avg_duration,
            "average_duration_seconds": avg_duration,
            "total_leads": total_leads,
            "qualified_leads": qualified_leads,
            "hot_leads": hot_leads,
            "converted_leads": converted_leads,
            "qualification_rate": qualification_rate,
            "conversion_rate": conversion_rate,
        },
        "lead_status_distribution": lead_status_distribution,
        "agent_performance": agent_performance,
        "timeline": [],
        "dispositions": dispositions,
    }


@router.get("/business/{business_id}/export")
async def export_business_report(
    business_id: str,
    type: str = Query("leads", pattern="^(leads|calls)$"),
    db: AsyncSession = Depends(get_db),
):
    out = io.StringIO()
    writer = csv.writer(out)

    if type == "leads":
        stmt = select(Lead).order_by(Lead.created_at.desc())
        if business_id != "all":
            stmt = stmt.where(Lead.tenant_id == business_id)
        res = await db.execute(stmt)
        leads = res.scalars().all()

        writer.writerow(["Lead ID", "Name", "Phone Number", "Email", "Status", "Score", "Reason", "Created At"])
        for l in leads:
            writer.writerow([l.id, l.name or "", l.phone_number, l.email or "", l.status, l.score, l.reason or "", l.created_at])

        filename = f"leads_export_{business_id}.csv"
    else:
        stmt = select(Call).order_by(Call.created_at.desc())
        if business_id != "all":
            stmt = stmt.where(Call.tenant_id == business_id)
        res = await db.execute(stmt)
        calls = res.scalars().all()

        writer.writerow(["Call ID", "Phone Number", "Status", "Duration (s)", "Disposition", "Started At", "Ended At"])
        for c in calls:
            writer.writerow([c.id, c.phone_number, c.status, c.duration or 0, c.disposition or "", c.started_at, c.ended_at])

        filename = f"calls_export_{business_id}.csv"

    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
