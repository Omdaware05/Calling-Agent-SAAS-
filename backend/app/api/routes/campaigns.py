import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.schemas.campaign import CampaignResponse, CreateCampaignRequest
from app.services.campaign_service import campaign_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(verify_app_client)])


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    agent_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    business_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all campaigns with optional agent or business filtering.
    """
    t_id = tenant_id or business_id
    return await campaign_service.list_campaigns(db, agent_id=agent_id, tenant_id=t_id)


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    payload: CreateCampaignRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new calling campaign.
    """
    return await campaign_service.create_campaign(db, payload)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve campaign by ID.
    """
    c = await campaign_service.get_campaign(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Start/launch a campaign.
    """
    c = await campaign_service.start_campaign(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"success": True, "message": "Campaign started successfully", "campaign": c}


@router.post("/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Stop a campaign.
    """
    c = await campaign_service.stop_campaign(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"success": True, "message": "Campaign stopped successfully", "campaign": c}
