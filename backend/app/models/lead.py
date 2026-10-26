import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Lead(Base):
    """
    Lead generated from AI voice qualification or contact disposition.
    """
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(128), nullable=True)
    phone_number = Column(String(32), nullable=False, index=True)
    email = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="new", index=True)  # new, interested, not_interested, qualified, closed
    score = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    tenant = relationship("Tenant")
    contact = relationship("Contact")
    agent = relationship("Agent")
    call = relationship("Call")


class Followup(Base):
    """
    Scheduled callback or action item following an AI call.
    """
    __tablename__ = "followups"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True, index=True)

    phone_number = Column(String(32), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending, scheduled, completed, cancelled
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    tenant = relationship("Tenant")
    contact = relationship("Contact")
    agent = relationship("Agent")
    call = relationship("Call")
