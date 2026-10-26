import uuid
from datetime import UTC, datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Questionnaire(Base):
    """
    Questionnaire model for agent dynamic questionnaires and surveys.
    """
    __tablename__ = "questionnaires"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    version_id = Column(String(64), nullable=False, default="v1")

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    questions = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="draft")  # draft, published, archived
    is_published = Column(Boolean, nullable=False, default=False)
    version_history = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    tenant = relationship("Tenant")
    agent = relationship("Agent")
