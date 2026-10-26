import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.schemas.business import BusinessResponse, CreateBusinessRequest, UpdateBusinessRequest
from app.services.business_service import business_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/businesses", tags=["businesses"], dependencies=[Depends(verify_app_client)])


@router.get("", response_model=List[BusinessResponse])
async def list_businesses(
    org_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List all registered businesses / tenants.
    """
    return await business_service.list_businesses(db, org_id=org_id, is_active=is_active, limit=limit, skip=skip)


@router.post("", response_model=BusinessResponse, status_code=201)
async def create_business(
    req: CreateBusinessRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new business / tenant.
    """
    return await business_service.create_business(db, req)


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve business by its unique ID.
    """
    b = await business_service.get_business(db, business_id)
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")
    return b


@router.put("/{business_id}", response_model=BusinessResponse)
async def update_business(
    business_id: str,
    req: UpdateBusinessRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing business.
    """
    b = await business_service.update_business(db, business_id, req)
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")
    return b


@router.delete("/{business_id}")
async def delete_business(
    business_id: str,
    hard_delete: bool = Query(False, alias="hard_delete"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete or deactivate a business.
    """
    success = await business_service.delete_business(db, business_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"success": True, "business_id": business_id}


@router.post("/{business_id}/agents/{agent_id}/assign")
async def assign_agent_to_business(
    business_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Assign an agent to a business.
    """
    success = await business_service.assign_agent(db, business_id, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"success": True, "business_id": business_id, "agent_id": agent_id}


@router.post("/{business_id}/agents/{agent_id}/unassign")
async def unassign_agent_from_business(
    business_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Unassign an agent from a business.
    """
    success = await business_service.unassign_agent(db, business_id, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"success": True, "business_id": business_id, "agent_id": agent_id}


@router.get("/{business_id}/dashboard")
async def get_business_dashboard(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard metrics for a business.
    """
    return await business_service.get_dashboard(db, business_id)
