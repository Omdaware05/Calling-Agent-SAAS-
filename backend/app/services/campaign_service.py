from datetime import UTC, datetime
import logging
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignContact
from app.models.call import Call
from app.schemas.campaign import CampaignResponse, CreateCampaignRequest
from app.utils.datetime_utils import to_iso_utc

logger = logging.getLogger(__name__)


def map_campaign_to_response(
    c: Campaign, total_contacts: int = 0, completed_calls: int = 0, pending_calls: int = 0
) -> CampaignResponse:
    phones = c.phone_numbers if isinstance(c.phone_numbers, list) else []
    calc_total = total_contacts if total_contacts > 0 else len(phones)
    calc_pending = pending_calls if total_contacts > 0 else calc_total - completed_calls
    return CampaignResponse(
        id=c.id,
        campaign_id=c.id,
        tenant_id=c.tenant_id,
        agent_id=c.agent_id,
        questionnaire_id=c.questionnaire_id,
        name=c.name,
        description=c.description,
        status=c.status or "CREATED",
        concurrency=c.concurrency or 1,
        provider=c.provider or "vobiz",
        phone_numbers=phones,
        total_contacts=calc_total,
        completed_calls=completed_calls,
        pending_calls=max(0, calc_pending),
        created_at=to_iso_utc(c.created_at) or to_iso_utc(datetime.now(UTC)),
        updated_at=to_iso_utc(c.updated_at),
    )


class CampaignService:
    @staticmethod
    async def list_campaigns(
        session: AsyncSession,
        agent_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[CampaignResponse]:
        stmt = select(Campaign).order_by(Campaign.created_at.desc())
        if agent_id:
            stmt = stmt.where(Campaign.agent_id == agent_id)
        if tenant_id:
            stmt = stmt.where(Campaign.tenant_id == tenant_id)

        result = await session.execute(stmt)
        campaigns = result.scalars().all()

        responses = []
        for c in campaigns:
            total_cc = (await session.execute(
                select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == c.id)
            )).scalar() or 0

            completed_calls = (await session.execute(
                select(func.count(Call.id)).where(Call.campaign_id == c.id, Call.status == "completed")
            )).scalar() or 0

            pending_cc = (await session.execute(
                select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == c.id, CampaignContact.status == "pending")
            )).scalar() or 0

            responses.append(map_campaign_to_response(c, total_cc, completed_calls, pending_cc))

        return responses

    @staticmethod
    async def get_campaign(session: AsyncSession, campaign_id: str) -> Optional[CampaignResponse]:
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            return None

        total_cc = (await session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == c.id)
        )).scalar() or 0

        completed_calls = (await session.execute(
            select(func.count(Call.id)).where(Call.campaign_id == c.id, Call.status == "completed")
        )).scalar() or 0

        pending_cc = (await session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == c.id, CampaignContact.status == "pending")
        )).scalar() or 0

        return map_campaign_to_response(c, total_cc, completed_calls, pending_cc)

    @staticmethod
    async def create_campaign(session: AsyncSession, data: CreateCampaignRequest) -> CampaignResponse:
        t_id = data.tenant_id or data.business_id
        campaign = Campaign(
            name=data.name.strip(),
            description=data.description,
            agent_id=data.agent_id,
            tenant_id=t_id,
            questionnaire_id=data.questionnaire_id,
            phone_numbers=data.phone_numbers,
            concurrency=data.concurrency or 1,
            provider=data.provider or "vobiz",
            status="CREATED",
        )
        session.add(campaign)
        await session.flush()

        # Populate campaign_contacts
        for phone in data.phone_numbers:
            p_clean = str(phone).strip()
            if p_clean:
                cc = CampaignContact(
                    campaign_id=campaign.id,
                    phone_number=p_clean,
                    status="pending",
                )
                session.add(cc)

        await session.commit()
        await session.refresh(campaign)
        return map_campaign_to_response(campaign, len(data.phone_numbers), 0, len(data.phone_numbers))

    @staticmethod
    async def start_campaign(session: AsyncSession, campaign_id: str) -> Optional[CampaignResponse]:
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            return None

        c.status = "RUNNING"
        c.started_at = datetime.now(UTC)
        c.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(c)
        return await CampaignService.get_campaign(session, campaign_id)

    @staticmethod
    async def stop_campaign(session: AsyncSession, campaign_id: str) -> Optional[CampaignResponse]:
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            return None

        c.status = "STOPPED"
        c.completed_at = datetime.now(UTC)
        c.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(c)
        return await CampaignService.get_campaign(session, campaign_id)


campaign_service = CampaignService()
