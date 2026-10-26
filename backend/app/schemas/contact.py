from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateContactRequest(BaseModel):
    phone_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None
    business_id: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ContactResponse(BaseModel):
    id: str
    contact_id: str
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    status: str = "active"
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: Optional[str] = None


class CsvImportResponse(BaseModel):
    total: int
    imported: int
    duplicates: int = 0
    errors: List[str] = Field(default_factory=list)
