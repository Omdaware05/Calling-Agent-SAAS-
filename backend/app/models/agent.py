import uuid
from datetime import UTC, datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(128), nullable=False, index=True)
    purpose = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)
    company_name = Column(String(255), nullable=True)
    company_description = Column(Text, nullable=True)
    greeting_message = Column(Text, nullable=True)
    predefined_faqs = Column(JSON, nullable=False, default=list)
    instructions = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)

    allowed_topics = Column(JSON, nullable=False, default=list)
    restricted_topics = Column(JSON, nullable=False, default=list)
    behavior_rules = Column(JSON, nullable=False, default=list)

    # Voice & Speech Configuration
    voice_gender = Column(String(16), nullable=False, default="male")
    voice_id = Column(String(64), nullable=False, default="hm_omega")
    voice_name = Column(String(128), nullable=False, default="Omega - Clear Hindi Male")
    tts_provider = Column(String(64), nullable=False, default="dograh")
    language_mode = Column(String(32), nullable=False, default="auto_match")
    primary_language = Column(String(32), nullable=False, default="multi")
    voice_style = Column(String(64), nullable=False, default="Friendly + Professional + Conversational")
    speaking_speed = Column(Float, nullable=False, default=1.0)

    # Multi-language & Telephony Engine Settings
    default_language = Column(String(64), nullable=False, default="English")
    supported_languages = Column(JSON, nullable=False, default=list)
    concurrency = Column(Integer, nullable=False, default=1)
    provider = Column(String(32), nullable=False, default="vobiz")
    avatar = Column(String(255), nullable=True)
    questionnaire_id = Column(String(36), nullable=True)

    # Per-Agent Telephony & Outbound Caller ID Configuration
    telephony_provider = Column(String(64), nullable=False, default="workspace_default")
    telephony_from_number = Column(String(32), nullable=True)
    telephony_auth_id = Column(String(128), nullable=True)
    telephony_auth_token = Column(String(255), nullable=True)

    # Engine configs
    stt_config = Column(JSON, nullable=False, default=dict)
    tts_config = Column(JSON, nullable=False, default=dict)
    llm_config = Column(JSON, nullable=False, default=dict)

    # Dograh sync mappings
    dograh_workflow_id = Column(Integer, nullable=True)
    dograh_trigger_path = Column(String(64), nullable=True, index=True)

    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="agents")
    calls = relationship("Call", back_populates="agent", cascade="all, delete-orphan")
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan")


class AgentVersion(Base):
    """
    Historical configuration snapshots for each published agent version.
    """
    __tablename__ = "agent_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    system_prompt = Column(Text, nullable=True)
    configuration = Column(JSON, nullable=False, default=dict)
    stt_configuration = Column(JSON, nullable=False, default=dict)
    llm_configuration = Column(JSON, nullable=False, default=dict)
    tts_configuration = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="published")  # draft, published, archived

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    published_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    agent = relationship("Agent", back_populates="versions")
