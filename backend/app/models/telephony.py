import uuid
from datetime import UTC, datetime
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TelephonyConfig(Base):
    __tablename__ = "telephony_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    provider = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    dograh_config_id = Column(Integer, nullable=True, index=True)
    credentials_json = Column(Text, nullable=False, default="{}")
    from_numbers = Column(JSON, nullable=False, default=list)
    default_from_number = Column(String(64), nullable=True)
    is_default_outbound = Column(Boolean, nullable=False, default=True)
    is_ready_for_outbound = Column(Boolean, nullable=False, default=False)
    outbound_blocked_reason = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="incomplete")
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
