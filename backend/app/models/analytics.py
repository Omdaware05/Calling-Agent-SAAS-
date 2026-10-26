import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class UsageEvent(Base):
    """
    Tracks granular AI and telephony consumption for each call session.
    """
    __tablename__ = "usage_events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)

    duration = Column(Float, nullable=False, default=0.0)
    telephony_usage = Column(Float, nullable=False, default=0.0)  # minutes / cost
    stt_usage = Column(Float, nullable=False, default=0.0)        # audio minutes
    llm_usage = Column(Float, nullable=False, default=0.0)        # tokens
    tts_usage = Column(Float, nullable=False, default=0.0)        # characters
    metadata_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class AuditLog(Base):
    """
    Audit log capturing system mutations (agent publish, campaign start, etc.).
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String(36), nullable=True)

    action = Column(String(64), nullable=False, index=True)  # agent.created, campaign.started, etc.
    entity_type = Column(String(64), nullable=False)        # agent, campaign, call, etc.
    entity_id = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
