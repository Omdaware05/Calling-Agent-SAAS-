import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Campaign(Base):
    """
    Campaign model for automated outbound voice calling workflows.
    """
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    questionnaire_id = Column(String(36), nullable=True)

    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="CREATED", index=True)  # CREATED, RUNNING, PAUSED, STOPPED, COMPLETED, FAILED
    concurrency = Column(Integer, nullable=False, default=1)
    provider = Column(String(32), nullable=False, default="vobiz")
    phone_numbers = Column(JSON, nullable=False, default=list)

    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="campaigns")
    agent = relationship("Agent")
    contacts = relationship("CampaignContact", back_populates="campaign", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="campaign")


class CampaignContact(Base):
    """
    Supporting join table tracking contact progress within a campaign.
    """
    __tablename__ = "campaign_contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    phone_number = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending, calling, completed, failed, retry
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="contacts")
    contact = relationship("Contact", back_populates="campaign_associations")
