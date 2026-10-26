from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    agent_id: str
    tenant_id: Optional[str] = None
    business_id: Optional[str] = None
    questionnaire_id: Optional[str] = None
    phone_numbers: List[str] = Field(default_factory=list)
    concurrency: Optional[int] = 1
    provider: Optional[str] = "vobiz"


class CampaignResponse(BaseModel):
    id: str
    campaign_id: str
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    questionnaire_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    status: str = "CREATED"
    concurrency: int = 1
    provider: str = "vobiz"
    phone_numbers: List[str] = Field(default_factory=list)
    total_contacts: int = 0
    completed_calls: int = 0
    pending_calls: int = 0
    created_at: str
    updated_at: Optional[str] = None
