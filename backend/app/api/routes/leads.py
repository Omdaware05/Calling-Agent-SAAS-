from datetime import UTC, datetime
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.models.lead import Lead
from app.schemas.lead import LeadResponse, UpdateLeadRequest

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
        created_at=l.created_at.isoformat() if l.created_at else datetime.now(UTC).isoformat(),
        updated_at=l.updated_at.isoformat() if l.updated_at else None,
    )


@router.get("", response_model=List[LeadResponse])
async def list_leads(
    agent_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    business_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List persisted leads.
    """
    t_id = tenant_id or business_id
    stmt = select(Lead).order_by(Lead.created_at.desc())
    if agent_id:
        stmt = stmt.where(Lead.agent_id == agent_id)
    if t_id:
        stmt = stmt.where(Lead.tenant_id == t_id)
    stmt = stmt.offset(skip).limit(limit)

    res = await db.execute(stmt)
    leads = res.scalars().all()
    return [map_lead_to_response(l) for l in leads]


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
