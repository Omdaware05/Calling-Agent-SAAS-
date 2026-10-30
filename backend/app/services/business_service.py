from datetime import UTC, datetime
import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.call import Call
from app.models.lead import Lead
from app.models.agent import Agent
from app.schemas.business import BusinessResponse, CreateBusinessRequest, UpdateBusinessRequest
from app.utils.datetime_utils import to_iso_utc

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r"[^\w\s-]", "", text).replace(" ", "-")


def map_tenant_to_response(t: Tenant, total_calls: int = 0, total_leads: int = 0, qualified_leads: int = 0) -> BusinessResponse:
    conversion_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0
    return BusinessResponse(
        id=t.id,
        business_id=t.id,
        org_id=t.org_id or "org_default",
        name=t.name,
        slug=t.slug,
        industry=t.industry or "General",
        primary_contact=t.primary_contact,
        email=t.email,
        phone=t.phone,
        timezone=t.timezone or "UTC",
        country=t.country or "US",
        preferred_languages=t.preferred_languages or ["en"],
        assigned_agent_ids=t.assigned_agent_ids or [],
        settings=t.settings or {},
        is_active=t.is_active if t.is_active is not None else True,
        status=t.status or "active",
        total_calls=total_calls,
        total_leads=total_leads,
        qualified_leads=qualified_leads,
        conversion_rate=conversion_rate,
        created_at=to_iso_utc(t.created_at) or to_iso_utc(datetime.now(UTC)),
        updated_at=to_iso_utc(t.updated_at),
    )


class BusinessService:
    @staticmethod
    async def list_businesses(
        session: AsyncSession,
        org_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[BusinessResponse]:
        stmt = select(Tenant).order_by(Tenant.created_at.desc())
        if org_id:
            stmt = stmt.where(Tenant.org_id == org_id)
        if is_active is not None:
            stmt = stmt.where(Tenant.is_active == is_active)
        stmt = stmt.offset(skip).limit(limit)

        result = await session.execute(stmt)
        tenants = result.scalars().all()

        responses = []
        for t in tenants:
            # Query call count and lead count for this business
            call_count = (await session.execute(
                select(func.count(Call.id)).where(Call.tenant_id == t.id)
            )).scalar() or 0

            lead_count = (await session.execute(
                select(func.count(Lead.id)).where(Lead.tenant_id == t.id)
            )).scalar() or 0

            qual_count = (await session.execute(
                select(func.count(Lead.id)).where(Lead.tenant_id == t.id, Lead.status.in_(["qualified", "interested"]))
            )).scalar() or 0

            resp = map_tenant_to_response(t, call_count, lead_count, qual_count)
            agent_ids = (await session.execute(
                select(Agent.id).where(Agent.tenant_id == t.id)
            )).scalars().all()
            resp.assigned_agent_ids = list(dict.fromkeys((t.assigned_agent_ids or []) + list(agent_ids)))
            responses.append(resp)
        return responses

    @staticmethod
    async def get_business(session: AsyncSession, business_id: str) -> Optional[BusinessResponse]:
        stmt = select(Tenant).where(Tenant.id == business_id)
        result = await session.execute(stmt)
        t = result.scalar_one_or_none()
        if not t:
            return None

        call_count = (await session.execute(
            select(func.count(Call.id)).where(Call.tenant_id == t.id)
        )).scalar() or 0
        lead_count = (await session.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == t.id)
        )).scalar() or 0
        qual_count = (await session.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == t.id, Lead.status.in_(["qualified", "interested"]))
        )).scalar() or 0

        resp = map_tenant_to_response(t, call_count, lead_count, qual_count)
        agent_ids = (await session.execute(
            select(Agent.id).where(Agent.tenant_id == t.id)
        )).scalars().all()
        resp.assigned_agent_ids = list(dict.fromkeys((t.assigned_agent_ids or []) + list(agent_ids)))
        return resp

    @staticmethod
    async def create_business(session: AsyncSession, data: CreateBusinessRequest) -> BusinessResponse:
        t = Tenant(
            name=data.name.strip(),
            slug=slugify(data.name),
            industry=data.industry or "General",
            primary_contact=data.primary_contact,
            email=data.email,
            phone=data.phone,
            timezone=data.timezone or "UTC",
            country=data.country or "US",
            preferred_languages=data.preferred_languages or ["en"],
            assigned_agent_ids=[],
            settings=data.settings or {},
            status="active",
            is_active=True,
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        return map_tenant_to_response(t)

    @staticmethod
    async def update_business(session: AsyncSession, business_id: str, data: UpdateBusinessRequest) -> Optional[BusinessResponse]:
        stmt = select(Tenant).where(Tenant.id == business_id)
        result = await session.execute(stmt)
        t = result.scalar_one_or_none()
        if not t:
            return None

        if data.name is not None:
            t.name = data.name.strip()
            t.slug = slugify(data.name)
        if data.industry is not None:
            t.industry = data.industry
        if data.primary_contact is not None:
            t.primary_contact = data.primary_contact
        if data.email is not None:
            t.email = data.email
        if data.phone is not None:
            t.phone = data.phone
        if data.timezone is not None:
            t.timezone = data.timezone
        if data.country is not None:
            t.country = data.country
        if data.preferred_languages is not None:
            t.preferred_languages = data.preferred_languages
        if data.is_active is not None:
            t.is_active = data.is_active
            t.status = "active" if data.is_active else "inactive"
        if data.settings is not None:
            t.settings = data.settings
        if data.assigned_agent_ids is not None:
            t.assigned_agent_ids = data.assigned_agent_ids

        t.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(t)
        return map_tenant_to_response(t)

    @staticmethod
    async def delete_business(session: AsyncSession, business_id: str, hard_delete: bool = False) -> bool:
        stmt = select(Tenant).where(Tenant.id == business_id)
        result = await session.execute(stmt)
        t = result.scalar_one_or_none()
        if not t:
            return False

        if hard_delete:
            await session.delete(t)
        else:
            t.is_active = False
            t.status = "inactive"
            t.updated_at = datetime.now(UTC)
        await session.commit()
        return True

    @staticmethod
    async def assign_agent(session: AsyncSession, business_id: str, agent_id: str) -> bool:
        stmt = select(Tenant).where(Tenant.id == business_id)
        result = await session.execute(stmt)
        t = result.scalar_one_or_none()
        if not t:
            return False

        current = list(t.assigned_agent_ids or [])
        if agent_id not in current:
            current.append(agent_id)
            t.assigned_agent_ids = current
            t.updated_at = datetime.now(UTC)
            await session.commit()
        return True

    @staticmethod
    async def unassign_agent(session: AsyncSession, business_id: str, agent_id: str) -> bool:
        stmt = select(Tenant).where(Tenant.id == business_id)
        result = await session.execute(stmt)
        t = result.scalar_one_or_none()
        if not t:
            return False

        current = list(t.assigned_agent_ids or [])
        if agent_id in current:
            current.remove(agent_id)
            t.assigned_agent_ids = current
            t.updated_at = datetime.now(UTC)
            await session.commit()
        return True

    @staticmethod
    async def get_dashboard(session: AsyncSession, business_id: str) -> Dict[str, Any]:
        t = await BusinessService.get_business(session, business_id)
        if not t:
            return {"error": "Business not found"}

        return {
            "business": t.model_dump(),
            "metrics": {
                "total_calls": t.total_calls,
                "total_leads": t.total_leads,
                "qualified_leads": t.qualified_leads,
                "conversion_rate": t.conversion_rate,
            },
        }


business_service = BusinessService()
