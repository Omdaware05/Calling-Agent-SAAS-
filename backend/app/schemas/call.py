from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class InitiateCallRequest(BaseModel):
    phone_number: str = Field(..., description="Target phone number in international format (+E.164)")
    agent_id: str = Field(..., description="Application agent ID to run")
    tenant_id: Optional[str] = None
    business_id: Optional[str] = None
    campaign_id: Optional[str] = None
    contact_id: Optional[str] = None
    initial_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional extra context variables")


class InitiateCallResponse(BaseModel):
    success: bool = True
    call_id: str
    status: str = "initiated"
    message: Optional[str] = None


class CallStatusResponse(BaseModel):
    call_id: str
    status: str  # initiating, ringing, in_progress, completed, busy, no_answer, failed
    phone_number: str
    agent_id: str
    agent_name: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[float] = None
    disposition: Optional[str] = None
    transcript_url: Optional[str] = None
    recording_url: Optional[str] = None


class CallHistoryItem(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _sync_orm_aliases(cls, data):
        # Call ORM objects carry `id`, not `call_id` — validating one
        # directly used to raise ValidationError despite
        # from_attributes=True inviting exactly that usage.
        if not isinstance(data, dict) and hasattr(data, "id"):
            return {
                "call_id": str(data.id),
                "dograh_run_id": getattr(data, "dograh_run_id", None),
                "phone_number": getattr(data, "phone_number", ""),
                "agent_id": getattr(data, "agent_id", ""),
                "tenant_id": getattr(data, "tenant_id", None),
                "campaign_id": getattr(data, "campaign_id", None),
                "status": getattr(data, "status", ""),
                "started_at": getattr(data, "started_at", None) or getattr(data, "created_at", None),
                "ended_at": getattr(data, "ended_at", None),
                "duration": getattr(data, "duration", None),
                "disposition": getattr(data, "disposition", None),
                "transcript_url": getattr(data, "transcript_url", None),
                "recording_url": getattr(data, "recording_url", None),
                "created_at": getattr(data, "created_at", None),
            }
        return data

    call_id: str
    dograh_run_id: Optional[int] = None
    phone_number: str
    agent_id: str
    tenant_id: Optional[str] = None
    campaign_id: Optional[str] = None
    agent_name: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[float] = None
    disposition: Optional[str] = None
    transcript_url: Optional[str] = None
    recording_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CallHistoryResponse(BaseModel):
    success: bool = True
    calls: List[CallHistoryItem]
    total: int


class DograhWebhookPayload(BaseModel):
    """Payload sent by Dograh Webhook Node upon call completion."""
    call_id: Optional[str] = None
    workflow_run_id: Optional[int] = None
    workflow_id: Optional[int] = None
    status: Optional[str] = None
    disposition: Optional[str] = None
    outcome: Optional[str] = None
    duration: Optional[float] = None
    recording_url: Optional[str] = None
    user_recording_url: Optional[str] = None
    bot_recording_url: Optional[str] = None
    transcript_url: Optional[str] = None
    transcript_text: Optional[str] = None
    transcript_segments: Optional[List[Dict[str, Any]]] = None
    initial_context: Optional[Dict[str, Any]] = None
    gathered_context: Optional[Dict[str, Any]] = None
    annotations: Optional[Dict[str, Any]] = None
