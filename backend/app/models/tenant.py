import uuid
from datetime import UTC, datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Tenant(Base):
    """
    Tenant/Business model representing an organization or client business in Voxora.
    Mapped directly to frontend BusinessProvider and /api/businesses endpoints.
    """
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    org_id = Column(String(64), nullable=True, default="org_default")
    name = Column(String(128), nullable=False, index=True)
    slug = Column(String(128), nullable=True, index=True)
    industry = Column(String(64), nullable=False, default="General")
    primary_contact = Column(String(128), nullable=True)
    email = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    timezone = Column(String(64), nullable=False, default="UTC")
    country = Column(String(64), nullable=False, default="US")
    preferred_languages = Column(JSON, nullable=False, default=lambda: ["en"])
    assigned_agent_ids = Column(JSON, nullable=False, default=list)
    settings = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="active")  # active, inactive, onboarding
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="tenant")
    contacts = relationship("Contact", back_populates="tenant")
    campaigns = relationship("Campaign", back_populates="tenant")


class User(Base):
    """
    User belonging to a tenant organization.
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(128), nullable=False, unique=True, index=True)
    name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="member")  # admin, member, viewer
    status = Column(String(32), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="users")
