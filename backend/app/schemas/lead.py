from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class UpdateLeadRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    score: Optional[float] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LeadResponse(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _sync_orm_aliases(cls, data):
        # The Lead ORM model has no lead_id / confidence_score / notes /
        # metadata attributes (it stores metadata_json and score);
        # validating an ORM object directly used to fail. Routes
        # hand-build dicts today, which pass through untouched.
        if not isinstance(data, dict) and hasattr(data, "id"):
            created = getattr(data, "created_at", None)
            updated = getattr(data, "updated_at", None)
            return {
                "id": str(data.id),
                "lead_id": str(data.id),
                "tenant_id": getattr(data, "tenant_id", None),
                "contact_id": getattr(data, "contact_id", None),
                "agent_id": getattr(data, "agent_id", None),
                "call_id": getattr(data, "call_id", None),
                "name": getattr(data, "name", None),
                "phone_number": getattr(data, "phone_number", ""),
                "email": getattr(data, "email", None),
                "status": getattr(data, "status", "new") or "new",
                "score": getattr(data, "score", 0.0) or 0.0,
                "confidence_score": getattr(data, "score", 0.0) or 0.0,
                "reason": getattr(data, "reason", None),
                "reasoning": getattr(data, "reason", None),
                "notes": None,
                "metadata": getattr(data, "metadata_json", None) or {},
                "created_at": created.isoformat() if created else "",
                "updated_at": updated.isoformat() if updated else None,
            }
        return data

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
