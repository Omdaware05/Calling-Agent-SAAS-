import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.schemas.contact import ContactResponse, CreateContactRequest, CsvImportResponse
from app.services.contact_service import contact_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"], dependencies=[Depends(verify_app_client)])


@router.get("", response_model=List[ContactResponse])
async def list_contacts(
    agent_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    business_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List persisted contacts with optional agent or business filtering.
    """
    t_id = tenant_id or business_id
    return await contact_service.list_contacts(db, agent_id=agent_id, tenant_id=t_id, limit=limit, skip=skip)


@router.post("", response_model=ContactResponse, status_code=201)
async def create_or_update_contact(
    payload: CreateContactRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update a contact.
    """
    return await contact_service.create_or_update_contact(db, payload)


@router.post("/import-csv", response_model=CsvImportResponse)
async def import_contacts_csv(
    file: UploadFile = File(...),
    agent_id: Optional[str] = Form(None),
    business_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Import contacts from uploaded CSV file.
    """
    try:
        contents = await file.read()
        text_content = contents.decode("utf-8-sig")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV file: {e}")

    return await contact_service.import_csv(db, text_content, agent_id=agent_id, tenant_id=business_id)
