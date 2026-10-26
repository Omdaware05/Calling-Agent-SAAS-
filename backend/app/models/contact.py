import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Contact(Base):
    """
    Contact / Customer model representing a target for outbound calling campaigns.
    """
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name = Column(String(128), nullable=True)
    phone_number = Column(String(32), nullable=False, index=True)
    email = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="active")  # active, do_not_call, invalid
    custom_fields = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="contacts")
    agent = relationship("Agent")
    calls = relationship("Call", back_populates="contact")
    campaign_associations = relationship("CampaignContact", back_populates="contact", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_contacts_tenant_phone", "tenant_id", "phone_number"),
    )
