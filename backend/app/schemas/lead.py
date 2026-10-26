from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UpdateLeadRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    score: Optional[float] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LeadResponse(BaseModel):
    id: str
    lead_id: str
    tenant_id: Optional[str] = None
    contact_id: Optional[str] = None
    agent_id: Optional[str] = None
    call_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    status: str = "new"
    score: float = 0.0
    confidence_score: float = 0.0
    reason: Optional[str] = None
    reasoning: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: Optional[str] = None


class UpdateFollowupRequest(BaseModel):
    status: Optional[str] = None
    scheduled_at: Optional[str] = None
    notes: Optional[str] = None


class FollowupResponse(BaseModel):
    id: str
    followup_id: str
    tenant_id: Optional[str] = None
    contact_id: Optional[str] = None
    agent_id: Optional[str] = None
    call_id: Optional[str] = None
    phone_number: str
    scheduled_at: Optional[str] = None
    status: str = "pending"
    notes: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
