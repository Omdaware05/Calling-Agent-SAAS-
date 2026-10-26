import uuid
from datetime import UTC, datetime, timedelta
from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Invoice(Base):
    """
    Invoice model representing billing items and payments for client businesses.
    """
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    invoice_number = Column(String(64), unique=True, nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)

    status = Column(String(32), nullable=False, default="pending")  # pending, paid, overdue, cancelled
    subtotal = Column(Float, nullable=False, default=0.0)
    tax = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)
    currency = Column(String(8), nullable=False, default="USD")

    issue_date = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    due_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC) + timedelta(days=30),
        nullable=False,
    )
    notes = Column(String(512), nullable=True)
    line_items = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[business_id])

    def to_dict(self):
        return {
            "invoice_id": self.id,
            "invoice_number": self.invoice_number,
            "business_id": self.business_id,
            "status": self.status,
            "subtotal": round(self.subtotal, 2),
            "tax": round(self.tax, 2),
            "total": round(self.total, 2),
            "currency": self.currency,
            "issue_date": self.issue_date.isoformat() if self.issue_date else "",
            "due_date": self.due_date.isoformat() if self.due_date else "",
            "notes": self.notes or "",
            "line_items": self.line_items or [],
        }
