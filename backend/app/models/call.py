import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    dograh_run_id = Column(Integer, nullable=True, index=True)
    dograh_run_name = Column(String(64), nullable=True)
    telephony_call_id = Column(String(64), nullable=True, index=True)

    phone_number = Column(String(32), nullable=False, index=True)
    direction = Column(String(16), nullable=False, default="outbound")  # outbound, inbound

    # Normalized status: initiating, ringing, in_progress, completed, busy, no_answer, failed
    status = Column(String(32), nullable=False, default="initiating", index=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    disposition = Column(String(64), nullable=True)
    termination_reason = Column(String(64), nullable=True)

    transcript_url = Column(String(512), nullable=True)
    recording_url = Column(String(512), nullable=True)

    context_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    agent = relationship("Agent", back_populates="calls")
    contact = relationship("Contact", back_populates="calls")
    campaign = relationship("Campaign", back_populates="calls")
    events = relationship("CallEvent", back_populates="call", cascade="all, delete-orphan")
    transcript = relationship("Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan")
    recording = relationship("Recording", back_populates="call", uselist=False, cascade="all, delete-orphan")


class CallEvent(Base):
    """
    Audit and lifecycle timeline events for an individual call.
    """
    __tablename__ = "call_events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # call.created, call.initiated, call.ringing, call.answered, call.completed, call.failed
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    event_metadata = Column(JSON, nullable=False, default=dict)

    call = relationship("Call", back_populates="events")


class Transcript(Base):
    """
    Structured transcript parent record.
    """
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    call = relationship("Call", back_populates="transcript")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan", order_by="TranscriptSegment.sequence")


class TranscriptSegment(Base):
    """
    Individual spoken turn in the voice conversation.
    """
    __tablename__ = "transcript_segments"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    transcript_id = Column(String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker = Column(String(16), nullable=False)  # agent, customer, system
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    sequence = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)

    transcript = relationship("Transcript", back_populates="segments")


class Recording(Base):
    """
    Metadata for audio recordings stored in MinIO / S3.
    """
    __tablename__ = "recordings"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    storage_key = Column(String(512), nullable=False)
    bucket = Column(String(128), nullable=False)
    content_type = Column(String(64), nullable=False, default="audio/wav")
    file_size = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="ready")  # processing, ready, failed

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    call = relationship("Call", back_populates="recording")
