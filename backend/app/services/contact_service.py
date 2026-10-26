import csv
from datetime import UTC, datetime
import io
import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.schemas.contact import ContactResponse, CreateContactRequest, CsvImportResponse
from app.services.call_service import validate_and_normalize_phone

logger = logging.getLogger(__name__)


def map_contact_to_response(c: Contact) -> ContactResponse:
    return ContactResponse(
        id=c.id,
        contact_id=c.id,
        tenant_id=c.tenant_id,
        agent_id=c.agent_id,
        name=c.name,
        phone_number=c.phone_number,
        email=c.email,
        status=c.status or "active",
        custom_fields=c.custom_fields or {},
        created_at=c.created_at.isoformat() if c.created_at else datetime.now(UTC).isoformat(),
        updated_at=c.updated_at.isoformat() if c.updated_at else None,
    )


class ContactService:
    @staticmethod
    async def list_contacts(
        session: AsyncSession,
        agent_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[ContactResponse]:
        stmt = select(Contact).order_by(Contact.created_at.desc())
        if agent_id:
            stmt = stmt.where(Contact.agent_id == agent_id)
        if tenant_id:
            stmt = stmt.where(Contact.tenant_id == tenant_id)
        stmt = stmt.offset(skip).limit(limit)

        result = await session.execute(stmt)
        contacts = result.scalars().all()
        return [map_contact_to_response(c) for c in contacts]

    @staticmethod
    async def create_or_update_contact(session: AsyncSession, data: CreateContactRequest) -> ContactResponse:
        t_id = data.tenant_id or data.business_id
        try:
            norm_phone = validate_and_normalize_phone(data.phone_number)
        except Exception:
            norm_phone = data.phone_number.strip()

        # Check existing contact by phone (and tenant if provided)
        stmt = select(Contact).where(Contact.phone_number == norm_phone)
        if t_id:
            stmt = stmt.where(Contact.tenant_id == t_id)
        res = await session.execute(stmt)
        contact = res.scalar_one_or_none()

        if contact:
            if data.name:
                contact.name = data.name.strip()
            if data.email:
                contact.email = data.email.strip()
            if data.agent_id:
                contact.agent_id = data.agent_id
            if data.custom_fields:
                merged = dict(contact.custom_fields or {})
                merged.update(data.custom_fields)
                contact.custom_fields = merged
            contact.updated_at = datetime.now(UTC)
        else:
            contact = Contact(
                tenant_id=t_id,
                agent_id=data.agent_id,
                name=data.name.strip() if data.name else None,
                phone_number=norm_phone,
                email=data.email.strip() if data.email else None,
                status="active",
                custom_fields=data.custom_fields or {},
            )
            session.add(contact)

        await session.commit()
        await session.refresh(contact)
        return map_contact_to_response(contact)

    @staticmethod
    async def import_csv(
        session: AsyncSession,
        csv_content: str,
        agent_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> CsvImportResponse:
        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)
        total = 0
        imported = 0
        duplicates = 0
        errors: List[str] = []

        for row in reader:
            total += 1
            # Look for phone column
            raw_phone = None
            for key in ("phone", "phone_number", "Phone", "Phone Number", "mobile", "Mobile", "contact", "Contact"):
                if key in row and row[key]:
                    raw_phone = str(row[key]).strip()
                    break

            if not raw_phone:
                # Fallback to first column
                vals = list(row.values())
                if vals and vals[0]:
                    raw_phone = str(vals[0]).strip()

            if not raw_phone:
                errors.append(f"Row {total}: No phone number found")
                continue

            try:
                norm_phone = validate_and_normalize_phone(raw_phone)
            except Exception:
                norm_phone = raw_phone

            name = row.get("name") or row.get("Name") or row.get("full_name") or row.get("Full Name")
            email = row.get("email") or row.get("Email")

            # Check if contact already exists
            stmt = select(Contact).where(Contact.phone_number == norm_phone)
            if tenant_id:
                stmt = stmt.where(Contact.tenant_id == tenant_id)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            if existing:
                duplicates += 1
                if name:
                    existing.name = name.strip()
                if email:
                    existing.email = email.strip()
                if agent_id:
                    existing.agent_id = agent_id
                existing.updated_at = datetime.now(UTC)
            else:
                contact = Contact(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    name=name.strip() if name else None,
                    phone_number=norm_phone,
                    email=email.strip() if email else None,
                    status="active",
                    custom_fields={k: v for k, v in row.items() if k not in ("phone", "phone_number", "name", "email")},
                )
                session.add(contact)
                imported += 1

        await session.commit()
        return CsvImportResponse(total=total, imported=imported, duplicates=duplicates, errors=errors)


contact_service = ContactService()
