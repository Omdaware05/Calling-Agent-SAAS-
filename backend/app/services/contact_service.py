import csv
from datetime import UTC, datetime
import io
import logging
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.call import Call
from app.models.lead import Lead
from app.schemas.contact import ContactResponse, CreateContactRequest, CsvImportResponse
from app.services.call_service import validate_and_normalize_phone
from app.utils.datetime_utils import to_iso_utc

logger = logging.getLogger(__name__)


def map_contact_to_response(
    c: Contact,
    interaction_count: int = 0,
    last_interest_status: Optional[str] = None,
    last_call_id: Optional[str] = None,
    last_call_at: Optional[str] = None,
    resolved_name: Optional[str] = None,
    resolved_email: Optional[str] = None,
) -> ContactResponse:
    return ContactResponse(
        id=c.id,
        contact_id=c.id,
        tenant_id=c.tenant_id,
        agent_id=c.agent_id,
        name=resolved_name or c.name,
        phone_number=c.phone_number,
        email=resolved_email or c.email,
        status=c.status or "active",
        interaction_count=interaction_count,
        last_call_id=last_call_id,
        last_interest_status=last_interest_status,
        last_call_at=last_call_at,
        custom_fields=c.custom_fields or {},
        created_at=to_iso_utc(c.created_at) or to_iso_utc(datetime.now(UTC)),
        updated_at=to_iso_utc(c.updated_at),
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

        responses = []
        for c in contacts:
            # Query call turns/count
            call_count = (await session.execute(
                select(func.count(Call.id)).where(Call.phone_number == c.phone_number)
            )).scalar() or 0

            # Query latest lead
            lead_stmt = select(Lead).where(Lead.phone_number == c.phone_number).order_by(Lead.created_at.desc())
            lead_res = await session.execute(lead_stmt)
            lead = lead_res.scalars().first()

            # Query latest call
            call_stmt = select(Call).where(Call.phone_number == c.phone_number).order_by(Call.created_at.desc())
            call_res = await session.execute(call_stmt)
            last_call = call_res.scalars().first()

            resolved_name = c.name or (lead.name if lead and lead.name else None)
            resolved_email = c.email or (lead.email if lead and lead.email else None)

            interest_status = "unanalyzed"
            if lead and lead.status:
                interest_status = lead.status
            elif last_call and last_call.disposition:
                disp = last_call.disposition.lower()
                if disp in ("interested", "callback_requested", "qualified", "hot"):
                    interest_status = "interested"
                elif "not" in disp or disp in ("not_interested", "rejected", "opt_out", "disqualified"):
                    interest_status = "not_interested"
                else:
                    interest_status = disp

            responses.append(map_contact_to_response(
                c,
                interaction_count=call_count,
                last_interest_status=interest_status,
                last_call_id=lead.call_id if lead else (last_call.id if last_call else None),
                last_call_at=to_iso_utc(last_call.created_at) if last_call and last_call.created_at else None,
                resolved_name=resolved_name,
                resolved_email=resolved_email,
            ))
        return responses

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
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()

        if c:
            if data.name:
                c.name = data.name.strip()
            if data.email:
                c.email = data.email.strip()
            if data.custom_fields:
                c.custom_fields = {**(c.custom_fields or {}), **data.custom_fields}
            c.updated_at = datetime.now(UTC)
        else:
            c = Contact(
                tenant_id=t_id,
                agent_id=data.agent_id,
                name=data.name.strip() if data.name else None,
                phone_number=norm_phone,
                email=data.email.strip() if data.email else None,
                custom_fields=data.custom_fields or {},
                status="active",
            )
            session.add(c)

        await session.commit()
        await session.refresh(c)
        return map_contact_to_response(c)

    @staticmethod
    async def import_csv(
        session: AsyncSession,
        csv_content: str,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> CsvImportResponse:
        reader = csv.DictReader(io.StringIO(csv_content))
        total = 0
        imported = 0
        duplicates = 0
        errors = []

        # Find columns (case-insensitive)
        fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
        phone_col = next((f for f in (reader.fieldnames or []) if f.lower() in ("phone", "phone_number", "mobile", "contact")), None)
        name_col = next((f for f in (reader.fieldnames or []) if f.lower() in ("name", "full_name", "first_name", "contact_name")), None)
        email_col = next((f for f in (reader.fieldnames or []) if f.lower() in ("email", "email_address")), None)

        if not phone_col:
            return CsvImportResponse(total=0, imported=0, errors=["Missing phone number column in CSV header"])

        for row_idx, row in enumerate(reader, start=2):
            total += 1
            raw_phone = (row.get(phone_col) or "").strip()
            if not raw_phone:
                errors.append(f"Row {row_idx}: Empty phone number")
                continue

            try:
                norm_phone = validate_and_normalize_phone(raw_phone)
            except Exception:
                norm_phone = raw_phone

            # Extract any remaining fields as custom_fields
            custom_fields = {k: v for k, v in row.items() if k not in (phone_col, name_col, email_col) and v}

            # Deduplication check
            stmt = select(Contact).where(Contact.phone_number == norm_phone)
            if tenant_id:
                stmt = stmt.where(Contact.tenant_id == tenant_id)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            if existing:
                duplicates += 1
                continue

            contact = Contact(
                tenant_id=tenant_id,
                agent_id=agent_id,
                name=(row.get(name_col) or "").strip() or None,
                phone_number=norm_phone,
                email=(row.get(email_col) or "").strip() or None,
                custom_fields=custom_fields,
                status="active",
            )
            session.add(contact)
            imported += 1

        await session.commit()
        return CsvImportResponse(total=total, imported=imported, duplicates=duplicates, errors=errors)


contact_service = ContactService()

