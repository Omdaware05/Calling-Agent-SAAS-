from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderFieldOption(BaseModel):
    label: str
    value: str


class ProviderFieldSchema(BaseModel):
    name: str
    label: str
    type: str  # text, password, textarea, bool, string-array
    required: bool = False
    sensitive: bool = False
    description: Optional[str] = None
    placeholder: Optional[str] = None
    options: Optional[List[ProviderFieldOption]] = None
    visible_when: Optional[Dict[str, Any]] = None
    section: Optional[str] = None


class ProviderMetadataSchema(BaseModel):
    provider: str
    display_name: str
    connectivity: str
    fields: List[ProviderFieldSchema] = Field(default_factory=list)
    docs_url: Optional[str] = None


class ProvidersListResponse(BaseModel):
    providers: List[ProviderMetadataSchema]


class TelephonyConfigRequest(BaseModel):
    provider: str
    name: str
    credentials: Dict[str, Any] = Field(default_factory=dict)
    from_numbers: List[str] = Field(default_factory=list)
    default_from_number: Optional[str] = None
    is_default_outbound: bool = True


class TelephonyConfigResponse(BaseModel):
    id: str
    provider: str
    name: str
    dograh_config_id: Optional[int] = None
    masked_credentials: Dict[str, Any] = Field(default_factory=dict)
    from_numbers: List[str] = Field(default_factory=list)
    default_from_number: Optional[str] = None
    is_default_outbound: bool = True
    is_ready_for_outbound: bool = False
    outbound_blocked_reason: Optional[str] = None
    status: str = "incomplete"
    last_tested_at: Optional[datetime] = None
    last_test_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TelephonyTestRequest(BaseModel):
    provider: str
    credentials: Dict[str, Any] = Field(default_factory=dict)
    phone_number: Optional[str] = None


class TelephonyTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class ReadinessCheckStep(BaseModel):
    step: str
    passed: bool
    message: str


class TelephonyReadinessResponse(BaseModel):
    is_ready: bool
    provider: Optional[str] = None
    default_caller_id: Optional[str] = None
    blocked_reason: Optional[str] = None
    steps: List[ReadinessCheckStep] = Field(default_factory=list)
