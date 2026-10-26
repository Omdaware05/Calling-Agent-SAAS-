from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Agent display name")
    purpose: str = Field(default="", max_length=1024, description="High-level purpose of the agent")
    instructions: str = Field(default="", description="Detailed system instructions")
    allowed_topics: List[str] = Field(default_factory=list, description="Topics agent is allowed to discuss")
    restricted_topics: List[str] = Field(default_factory=list, description="Topics agent must avoid")
    behavior_rules: List[str] = Field(default_factory=list, description="Conditional behavioral instructions")
    enabled: bool = Field(default=True, description="Whether the agent is active")

    # Voice Configuration
    voice_gender: str = Field(default="male", description="female, male, neutral")
    voice_id: str = Field(default="hm_omega", description="Dograh/TTS Voice ID")
    voice_name: str = Field(default="Omega - Clear Hindi Male", description="Human-friendly voice name")
    tts_provider: str = Field(default="speaches", description="dograh, speaches, sarvam, cartesia, elevenlabs, deepgram")
    language_mode: str = Field(default="auto_match", description="auto_match, hindi, english, hinglish, fixed")
    primary_language: str = Field(default="multi", description="multi, hi, en, etc.")
    voice_style: str = Field(default="Friendly + Professional + Conversational", description="Conversational style personality")
    speaking_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speaking speed: 0.5 to 2.0")

    company_name: Optional[str] = Field(default=None, description="Company/organization name the agent represents")
    company_description: Optional[str] = Field(default=None, description="Brief description of the company and offerings to speak to customers")
    greeting_message: Optional[str] = Field(default=None, description="Pre-defined opening greeting spoken directly upon call connection")
    predefined_faqs: List[Dict[str, Any]] = Field(default_factory=list, description="Pre-defined FAQ answers to avoid LLM processing")

    # Per-Agent Dedicated Telephony Configuration
    telephony_provider: Optional[str] = Field(default="workspace_default", description="vobiz, twilio, or workspace_default")
    telephony_from_number: Optional[str] = Field(default=None, description="Dedicated outbound caller ID E.164 phone number")
    telephony_auth_id: Optional[str] = Field(default=None, description="Dedicated carrier Auth ID / Account SID")
    telephony_auth_token: Optional[str] = Field(default=None, description="Dedicated carrier Auth Token / API Secret")

    # Tenant & Configuration
    tenant_id: Optional[str] = None
    business_id: Optional[str] = None
    questionnaire_id: Optional[str] = None
    avatar: Optional[str] = None
    concurrency: int = Field(default=1, ge=1)
    provider: str = Field(default="vobiz")
    supported_languages: List[str] = Field(default_factory=lambda: ["English", "Hindi", "Hinglish"])
    stt_config: Dict[str, Any] = Field(default_factory=dict)
    tts_config: Dict[str, Any] = Field(default_factory=dict)
    llm_config: Dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    is_enabled: Optional[bool] = None
    default_language: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("purpose"):
                data["purpose"] = data.get("description") or data.get("name") or "General Voice Agent"
            if not data.get("instructions"):
                data["instructions"] = data.get("system_prompt") or "You are a professional voice AI assistant."
            if "is_enabled" in data and "enabled" not in data:
                data["enabled"] = data["is_enabled"]
            if data.get("business_id") and not data.get("tenant_id"):
                data["tenant_id"] = data["business_id"]
            if not data.get("company_name"):
                data["company_name"] = "ARB SoftTech"
            if not data.get("company_description") and data.get("purpose"):
                data["company_description"] = data.get("purpose")
        return data


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    purpose: Optional[str] = Field(None, max_length=1024)
    instructions: Optional[str] = None
    allowed_topics: Optional[List[str]] = None
    restricted_topics: Optional[List[str]] = None
    behavior_rules: Optional[List[str]] = None
    enabled: Optional[bool] = None

    company_name: Optional[str] = None
    company_description: Optional[str] = None
    greeting_message: Optional[str] = None
    predefined_faqs: Optional[List[Dict[str, Any]]] = None

    # Frontend aliases
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    is_enabled: Optional[bool] = None
    default_language: Optional[str] = None
    tenant_id: Optional[str] = None
    business_id: Optional[str] = None
    questionnaire_id: Optional[str] = None
    avatar: Optional[str] = None
    concurrency: Optional[int] = None
    provider: Optional[str] = None
    supported_languages: Optional[List[str]] = None
    stt_config: Optional[Dict[str, Any]] = None
    tts_config: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None

    # Voice Configuration Updates
    voice_gender: Optional[str] = None
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    tts_provider: Optional[str] = None
    language_mode: Optional[str] = None
    primary_language: Optional[str] = None
    voice_style: Optional[str] = None
    speaking_speed: Optional[float] = Field(None, ge=0.5, le=2.0)

    # Per-Agent Telephony Updates
    telephony_provider: Optional[str] = None
    telephony_from_number: Optional[str] = None
    telephony_auth_id: Optional[str] = None
    telephony_auth_token: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "description" in data and not data.get("purpose"):
                data["purpose"] = data["description"]
            if "system_prompt" in data and not data.get("instructions"):
                data["instructions"] = data["system_prompt"]
            if "is_enabled" in data and "enabled" not in data:
                data["enabled"] = data["is_enabled"]
            if data.get("business_id") and not data.get("tenant_id"):
                data["tenant_id"] = data["business_id"]
        return data


class AgentResponse(AgentBase):
    id: str
    dograh_workflow_id: Optional[int] = None
    dograh_trigger_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Frontend compatibility fields
    agent_id: Optional[str] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
    default_language: Optional[str] = "English"
    system_prompt: Optional[str] = None
    has_custom_telephony_token: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def sync_frontend_fields(self):
        self.agent_id = self.id
        self.is_enabled = self.enabled
        self.description = self.purpose or self.description
        self.system_prompt = self.instructions or self.system_prompt
        self.business_id = self.tenant_id
        if not self.default_language:
            self.default_language = "English" if "en" in (self.primary_language or "") else "Hindi"

        # Check and safely mask custom telephony auth token
        if self.telephony_auth_token and len(self.telephony_auth_token.strip()) > 0:
            self.has_custom_telephony_token = True
            token_str = self.telephony_auth_token.strip()
            suffix = token_str[-4:] if len(token_str) >= 4 else token_str
            self.telephony_auth_token = f"••••••••{suffix}"
        else:
            self.has_custom_telephony_token = False

        return self


class StartCallsRequest(BaseModel):
    phone_numbers: List[str]
    concurrency: Optional[int] = 1
    provider: Optional[str] = "vobiz"
    language: Optional[str] = "English"
    questionnaire_id: Optional[str] = None
