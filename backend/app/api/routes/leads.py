from datetime import UTC, datetime
import io
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import resolve_tenant_id, verify_app_client
from app.models.lead import Lead
from app.schemas.lead import LeadResponse, UpdateLeadRequest
from app.utils.datetime_utils import to_iso_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"], dependencies=[Depends(verify_app_client)])


def map_lead_to_response(l: Lead) -> LeadResponse:
    return LeadResponse(
        id=l.id,
        lead_id=l.id,
        tenant_id=l.tenant_id,
        contact_id=l.contact_id,
        agent_id=l.agent_id,
        call_id=l.call_id,
        name=l.name,
        phone_number=l.phone_number,
        email=l.email,
        status=l.status or "new",
        score=l.score or 0.0,
        confidence_score=l.score or 0.0,
        reason=l.reason,
        reasoning=l.reason,
        notes=l.reason,
        metadata=l.metadata_json or {},
        created_at=to_iso_utc(l.created_at) or to_iso_utc(datetime.now(UTC)),
        updated_at=to_iso_utc(l.updated_at),
    )


@router.get("", response_model=List[LeadResponse])
async def list_leads(
    agent_id: Optional[str] = None,
    tenant_id: Optional[str] = Depends(resolve_tenant_id),
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List persisted leads.
    """
    t_id = tenant_id
    stmt = select(Lead).order_by(Lead.created_at.desc())
    if agent_id:
        stmt = stmt.where(Lead.agent_id == agent_id)
    if t_id:
        stmt = stmt.where(Lead.tenant_id == t_id)
    stmt = stmt.offset(skip).limit(limit)

    res = await db.execute(stmt)
    leads = res.scalars().all()
    return [map_lead_to_response(l) for l in leads]


@router.get("/export.xlsx")
async def export_leads_excel(
    status: Optional[str] = Query(
        None,
        description="Filter by lead status, e.g. interested, not_interested, "
                    "qualified, closed. Omit for all leads."),
    tenant_id: Optional[str] = Depends(resolve_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Download leads as an Excel (.xlsx) file — customer name, what they said,
    when to call again, service interested, phone, email, status, score,
    and Gemini extracted analysis.
    Defined before /{lead_id} so 'export.xlsx' is not captured as an id.
    """
    from openpyxl import Workbook

    t_id = tenant_id
    stmt = select(Lead).order_by(Lead.created_at.desc())
    if status:
        stmt = stmt.where(Lead.status == status)
    if t_id:
        stmt = stmt.where(Lead.tenant_id == t_id)
    res = await db.execute(stmt)
    leads = res.scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    headers = [
        "Customer Name",
        "Phone Number",
        "Status",
        "What Customer Said",
        "When to Call Again (Callback Time)",
        "Service Interested",
        "Email",
        "Score",
        "Reason / Notes",
        "City",
        "Budget (INR)",
        "Why Interested",
        "Why Not Interested",
        "Call ID",
        "Created At",
    ]
    ws.append(headers)

    def _reasons_text(items) -> str:
        parts = []
        for r in items or []:
            if isinstance(r, dict):
                parts.append(f"{r.get('reason', '')} — \"{r.get('evidence', '')}\"")
            else:
                parts.append(str(r))
        return "; ".join(parts)

    for l in leads:
        meta = l.metadata_json or {}
        ci = meta.get("customer_info") or {}
        cust_name = l.name or meta.get("customer_name") or ci.get("name") or "Unknown Prospect"
        what_said = meta.get("what_they_said") or l.reason or ""
        when_to_call = meta.get("preferred_callback_time") or ""
        service = meta.get("service_interested") or ci.get("product_interest") or ""
        ws.append([
            cust_name,
            l.phone_number,
            l.status,
            what_said,
            when_to_call,
            service,
            l.email or ci.get("email"),
            l.score,
            l.reason,
            ci.get("city"),
            ci.get("budget_inr"),
            _reasons_text(meta.get("why_interested")),
            _reasons_text(meta.get("why_not_interested")),
            l.call_id,
            l.created_at.isoformat() if l.created_at else None,
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    suffix = status or "all"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="leads_{suffix}.xlsx"'},
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Lead).where(Lead.id == lead_id)
    res = await db.execute(stmt)
    l = res.scalar_one_or_none()
    if not l:
        raise HTTPException(status_code=404, detail="Lead not found")
    return map_lead_to_response(l)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: str, payload: UpdateLeadRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Lead).where(Lead.id == lead_id)
    res = await db.execute(stmt)
    l = res.scalar_one_or_none()
    if not l:
        raise HTTPException(status_code=404, detail="Lead not found")

    if payload.status is not None:
        l.status = payload.status
    if payload.notes is not None:
        l.reason = payload.notes
    if payload.reason is not None:
        l.reason = payload.reason
    if payload.score is not None:
        l.score = payload.score
    if payload.metadata is not None:
        meta = dict(l.metadata_json or {})
        meta.update(payload.metadata)
        l.metadata_json = meta

    l.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(l)
    return map_lead_to_response(l)
