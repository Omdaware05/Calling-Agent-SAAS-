from datetime import UTC, datetime
import logging
import re
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentVersion
from app.models.tenant import Tenant
from app.models.questionnaire import Questionnaire
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.dograh_service import dograh_service

logger = logging.getLogger(__name__)


def format_questionnaire_prompt_block(title: str, questions: list) -> str:
    if not questions:
        return ""
    lines = [f"\n\n### MANDATORY QUESTIONNAIRE SCRIPT ({title.upper()}):"]
    lines.append("You must conduct the following conversational questionnaire with the caller during this call:")
    for idx, q in enumerate(questions, 1):
        q_text = q.get("text") or q.get("question") or q.get("title") or ""
        expected = q.get("expected_answer")
        if expected:
            lines.append(f"{idx}. Question: \"{q_text}\"\n   - Expected Answer / Reference: \"{expected}\"")
        else:
            q_type = q.get("type", "general")
            q_opts = q.get("options")
            opt_str = f" [Options: {', '.join(q_opts)}]" if q_opts else ""
            lines.append(f"{idx}. Question: \"{q_text}\" (Type: {q_type}){opt_str}")
    lines.append("")
    lines.append("Rules for conducting the questionnaire:")
    lines.append("- Ask exactly one question at a time naturally in the caller's language.")
    lines.append("- The Expected Answer / Reference is STRICTLY internal context for you to interpret customer responses. NEVER speak phrases like 'Expected answer is...' to the customer.")
    lines.append("- Understand caller responses semantically and flexibly — do NOT expect an exact textual match (for example, if expected answer is 'गहू / हरभरा / चणा / मका' and the caller says 'मी यंदा गहू करणार आहे', recognize Wheat and proceed accordingly).")
    lines.append("- Listen attentively, warmly acknowledge the caller's response, and proceed naturally through the conversational script.")
    lines.append("- If the caller asks clarifying questions or needs product information, answer politely and then return to the script flow.")
    return "\n".join(lines)


class AgentService:
    @staticmethod
    async def list_agents(session: AsyncSession, tenant_id: Optional[str] = None) -> List[Agent]:
        stmt = select(Agent).order_by(Agent.created_at.desc())
        if tenant_id:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_agent(session: AsyncSession, agent_id: str) -> Optional[Agent]:
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_agent(session: AsyncSession, data: AgentCreate) -> Agent:
        instructions = data.instructions or data.system_prompt or "You are a professional voice AI assistant."
        system_prompt = data.system_prompt or instructions

        # If a questionnaire is chosen, connect it to instructions & system prompt
        if data.questionnaire_id:
            q_res = await session.execute(select(Questionnaire).where(Questionnaire.id == data.questionnaire_id))
            q_obj = q_res.scalar_one_or_none()
            if q_obj and q_obj.questions:
                q_block = format_questionnaire_prompt_block(q_obj.title, q_obj.questions)
                # Dedupe on the script-block header — this used to skip
                # attaching entirely whenever the questionnaire's TITLE
                # happened to appear anywhere in the instructions prose.
                if q_block and "### MANDATORY QUESTIONNAIRE SCRIPT" not in instructions:
                    instructions = f"{instructions.strip()}\n\n{q_block}"
                    system_prompt = instructions

        agent = Agent(
            tenant_id=data.tenant_id,
            name=data.name,
            purpose=data.purpose,
            description=data.description or data.purpose,
            company_name=data.company_name or "ARB SoftTech",
            company_description=data.company_description or data.purpose,
            greeting_message=data.greeting_message,
            predefined_faqs=data.predefined_faqs or [],
            instructions=instructions,
            system_prompt=system_prompt,
            allowed_topics=data.allowed_topics,
            restricted_topics=data.restricted_topics,
            behavior_rules=data.behavior_rules,
            enabled=data.enabled,
            voice_gender=data.voice_gender,
            voice_id=data.voice_id,
            voice_name=data.voice_name,
            tts_provider=data.tts_provider,
            language_mode=data.language_mode,
            primary_language=data.primary_language,
            voice_style=data.voice_style,
            speaking_speed=data.speaking_speed,
            default_language=data.default_language or "English",
            supported_languages=data.supported_languages or ["English", "Hindi", "Hinglish"],
            concurrency=data.concurrency or 1,
            provider=data.provider or "vobiz",
            avatar=data.avatar,
            questionnaire_id=data.questionnaire_id,
            telephony_provider=data.telephony_provider or "workspace_default",
            telephony_from_number=data.telephony_from_number,
            telephony_auth_id=data.telephony_auth_id,
            telephony_auth_token=data.telephony_auth_token,
            stt_config=data.stt_config or {},
            tts_config=data.tts_config or {},
            llm_config=data.llm_config or {},
        )

        # Sync to Dograh to create the workflow and trigger
        try:
            workflow_id, trigger_path = await dograh_service.sync_workflow_to_dograh(
                name=agent.name,
                purpose=agent.purpose,
                instructions=agent.instructions,
                allowed_topics=agent.allowed_topics,
                restricted_topics=agent.restricted_topics,
                behavior_rules=agent.behavior_rules,
                voice_id=agent.voice_id,
                speaking_speed=agent.speaking_speed,
                language_mode=agent.language_mode,
                primary_language=agent.primary_language,
                voice_style=agent.voice_style,
                tts_provider=agent.tts_provider,
                company_name=agent.company_name,
                company_description=agent.company_description,
                greeting_message=agent.greeting_message,
            )
            agent.dograh_workflow_id = workflow_id
            agent.dograh_trigger_path = trigger_path
        except Exception as e:
            logger.warning(f"Error syncing new agent workflow to Dograh: {e}")

        session.add(agent)
        await session.flush()

        # Connect questionnaire back to this agent if assigned
        if data.questionnaire_id and q_obj:
            q_obj.agent_id = agent.id

        # Create version 1 record
        initial_version = AgentVersion(
            agent_id=agent.id,
            version=1,
            system_prompt=agent.system_prompt,
            configuration={
                "name": agent.name,
                "purpose": agent.purpose,
                "voice_id": agent.voice_id,
                "tts_provider": agent.tts_provider,
                "speaking_speed": agent.speaking_speed,
            },
            stt_configuration=agent.stt_config or {},
            llm_configuration=agent.llm_config or {},
            tts_configuration=agent.tts_config or {},
            status="published",
        )
        session.add(initial_version)

        # If tenant specified, ensure assigned_agent_ids is updated
        if agent.tenant_id:
            tenant_res = await session.execute(select(Tenant).where(Tenant.id == agent.tenant_id))
            tenant = tenant_res.scalar_one_or_none()
            if tenant:
                assigned = list(tenant.assigned_agent_ids or [])
                if agent.id not in assigned:
                    assigned.append(agent.id)
                    tenant.assigned_agent_ids = assigned

        await session.commit()
        await session.refresh(agent)
        return agent

    @staticmethod
    async def update_agent(session: AsyncSession, agent_id: str, data: AgentUpdate) -> Optional[Agent]:
        agent = await AgentService.get_agent(session, agent_id)
        if not agent:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        # Handle aliases
        if "description" in update_dict and not update_dict.get("purpose"):
            agent.purpose = update_dict["description"]
        if "system_prompt" in update_dict and not update_dict.get("instructions"):
            agent.instructions = update_dict["system_prompt"]
        if "is_enabled" in update_dict and "enabled" not in update_dict:
            agent.enabled = update_dict["is_enabled"]

        for key, value in update_dict.items():
            if hasattr(agent, key) and value is not None:
                # If user leaves token blank or submits masked token, preserve existing token
                if key == "telephony_auth_token" and (not str(value).strip() or "••••" in str(value)):
                    continue
                setattr(agent, key, value)

        # Rebuild the questionnaire script block ONLY when this request
        # actually changes the questionnaire link. This used to run on
        # EVERY edit of a questionnaire-linked agent (even a name-only
        # change), rewriting the prompt each time and clobbering a
        # system_prompt edited in the same request — and it silently
        # STOLE the questionnaire from whichever agent owned it before
        # by overwriting q_obj.agent_id.
        if agent.questionnaire_id and "questionnaire_id" in update_dict:
            q_res = await session.execute(select(Questionnaire).where(Questionnaire.id == agent.questionnaire_id))
            q_obj = q_res.scalar_one_or_none()
            if q_obj and q_obj.questions:
                if q_obj.agent_id in (None, agent.id):
                    q_obj.agent_id = agent.id
                else:
                    logger.warning(
                        f"Questionnaire {q_obj.id} is owned by agent {q_obj.agent_id}; "
                        f"linking it to agent {agent.id} without stealing ownership."
                    )
                q_block = format_questionnaire_prompt_block(q_obj.title, q_obj.questions)
                cleaned_instr = re.sub(r"\n\n### MANDATORY QUESTIONNAIRE SCRIPT[\s\S]*?(?=\n\n[A-Z#]|$)", "", agent.instructions or "").strip()
                agent.instructions = f"{cleaned_instr}\n\n{q_block}" if cleaned_instr else q_block
                agent.system_prompt = agent.instructions
        elif "questionnaire_id" in update_dict and update_dict["questionnaire_id"] is None:
            # Clean up questionnaire block if explicitly detached
            agent.instructions = re.sub(r"\n\n### MANDATORY QUESTIONNAIRE SCRIPT[\s\S]*?(?=\n\n[A-Z#]|$)", "", agent.instructions or "").strip()
            agent.system_prompt = agent.instructions

        agent.updated_at = datetime.now(UTC)

        # Re-sync workflow with Dograh including voice parameters
        try:
            workflow_id, trigger_path = await dograh_service.sync_workflow_to_dograh(
                name=agent.name,
                purpose=agent.purpose,
                instructions=agent.instructions,
                allowed_topics=agent.allowed_topics,
                restricted_topics=agent.restricted_topics,
                behavior_rules=agent.behavior_rules,
                existing_workflow_id=agent.dograh_workflow_id,
                existing_trigger_path=agent.dograh_trigger_path,
                voice_id=agent.voice_id,
                speaking_speed=agent.speaking_speed,
                language_mode=agent.language_mode,
                primary_language=agent.primary_language,
                voice_style=agent.voice_style,
                tts_provider=agent.tts_provider,
                company_name=agent.company_name,
                company_description=agent.company_description,
                greeting_message=agent.greeting_message,
            )
            if workflow_id:
                agent.dograh_workflow_id = workflow_id
            if trigger_path:
                agent.dograh_trigger_path = trigger_path
        except Exception as e:
            logger.warning(f"Error re-syncing agent workflow to Dograh: {e}")

        # Update or add agent version
        try:
            ver_res = await session.execute(
                select(AgentVersion).where(AgentVersion.agent_id == agent.id).order_by(AgentVersion.version.desc()).limit(1)
            )
            latest_ver = ver_res.scalar_one_or_none()
            next_version_num = (latest_ver.version + 1) if latest_ver else 1

            new_ver = AgentVersion(
                agent_id=agent.id,
                version=next_version_num,
                system_prompt=agent.system_prompt,
                configuration={
                    "name": agent.name,
                    "purpose": agent.purpose,
                    "voice_id": agent.voice_id,
                    "tts_provider": agent.tts_provider,
                    "speaking_speed": agent.speaking_speed,
                },
                stt_configuration=agent.stt_config or {},
                llm_configuration=agent.llm_config or {},
                tts_configuration=agent.tts_config or {},
                status="published",
            )
            session.add(new_ver)
        except Exception as e:
            logger.debug(f"Version snapshot warning: {e}")

        await session.commit()
        await session.refresh(agent)
        return agent

    @staticmethod
    async def delete_agent(session: AsyncSession, agent_id: str) -> bool:
        agent = await AgentService.get_agent(session, agent_id)
        if not agent:
            return False

        # Attempt to delete workflow from Dograh
        if agent.dograh_workflow_id:
            try:
                await dograh_service.delete_workflow(agent.dograh_workflow_id)
            except Exception as e:
                logger.warning(f"Error deleting Dograh workflow {agent.dograh_workflow_id}: {e}")

        # Remove from any tenant assigned list
        if agent.tenant_id:
            tenant_res = await session.execute(select(Tenant).where(Tenant.id == agent.tenant_id))
            tenant = tenant_res.scalar_one_or_none()
            if tenant and tenant.assigned_agent_ids:
                assigned = [aid for aid in tenant.assigned_agent_ids if aid != agent.id]
                tenant.assigned_agent_ids = assigned

        await session.delete(agent)
        await session.commit()
        return True


agent_service = AgentService()
