from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateBusinessRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    industry: Optional[str] = "General"
    primary_contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = "UTC"
    country: Optional[str] = "US"
    preferred_languages: Optional[List[str]] = ["en"]
    settings: Optional[Dict[str, Any]] = None


class UpdateBusinessRequest(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    primary_contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    country: Optional[str] = None
    preferred_languages: Optional[List[str]] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    assigned_agent_ids: Optional[List[str]] = None


class BusinessResponse(BaseModel):
    id: str
    business_id: str
    org_id: str = "org_default"
    name: str
    slug: Optional[str] = None
    industry: str = "General"
    primary_contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    timezone: str = "UTC"
    country: str = "US"
    preferred_languages: List[str] = Field(default_factory=lambda: ["en"])
    assigned_agent_ids: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    status: str = "active"
    total_calls: int = 0
    total_leads: int = 0
    qualified_leads: int = 0
    conversion_rate: float = 0.0
    created_at: str
    updated_at: Optional[str] = None
