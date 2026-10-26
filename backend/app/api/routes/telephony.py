import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.schemas.telephony import (
    ProvidersListResponse,
    TelephonyConfigRequest,
    TelephonyConfigResponse,
    TelephonyReadinessResponse,
    TelephonyTestRequest,
    TelephonyTestResponse,
)
from app.services.telephony_service import telephony_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telephony", tags=["telephony"], dependencies=[Depends(verify_app_client)])


@router.get("/providers", response_model=ProvidersListResponse)
async def get_providers():
    """
    Get metadata, UI schemas, and fields for all 7 supported telephony providers:
    Twilio, Plivo, Telnyx, Vonage, Vobiz, Cloudonix, and Asterisk ARI.
    """
    providers = await telephony_service.get_providers_metadata()
    return ProvidersListResponse(providers=providers)


@router.get("/config", response_model=Optional[TelephonyConfigResponse])
async def get_active_config(db: AsyncSession = Depends(get_db)):
    """
    Get the currently active telephony provider configuration with sensitive credentials masked.
    """
    return await telephony_service.get_active_config(db)


@router.post("/config", response_model=TelephonyConfigResponse)
async def save_config(
    request: TelephonyConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Save or replace telephony provider configuration, registering phone numbers
    and setting it as default outbound in Dograh.
    """
    try:
        return await telephony_service.save_config(db, request)
    except Exception as e:
        logger.error(f"Failed to save telephony config: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "TELEPHONY_SAVE_FAILED", "message": str(e)},
        )


@router.put("/config", response_model=TelephonyConfigResponse)
async def update_config(
    request: TelephonyConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update telephony provider configuration.
    """
    try:
        return await telephony_service.save_config(db, request)
    except Exception as e:
        logger.error(f"Failed to update telephony config: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "TELEPHONY_UPDATE_FAILED", "message": str(e)},
        )


@router.post("/test", response_model=TelephonyTestResponse)
async def test_connection(
    request: TelephonyTestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Test credentials against upstream provider (e.g. Twilio API, Plivo API, etc.).
    """
    return await telephony_service.test_config(db, request)


@router.delete("/config")
async def delete_config(db: AsyncSession = Depends(get_db)):
    """
    Delete active telephony configuration from DB and voice engine.
    """
    deleted = await telephony_service.delete_config(db)
    return {"success": deleted, "message": "Telephony configuration deleted" if deleted else "No configuration found"}


@router.get("/readiness", response_model=TelephonyReadinessResponse)
async def get_outbound_readiness(db: AsyncSession = Depends(get_db)):
    """
    Quick check of outbound calling readiness for mobile app preflight.
    """
    return await telephony_service.get_outbound_readiness(db)
