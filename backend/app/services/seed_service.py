"""
Database Seeder Service
=======================
Automatically populates the database with default tenants, telephony config,
and production-ready voice agents (Hindi & English) if the database is newly initialized.
Ensures the client has immediate working agents ready to test and dial.
"""

import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.agent import Agent
from app.models.telephony import TelephonyConfig
from app.config import settings

logger = logging.getLogger(__name__)


async def seed_initial_data_if_needed():
    """
    Checks if agents and tenants exist. If not, seeds ready-to-dial agents.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Check if tenant exists
            tenant_res = await session.execute(select(Tenant).limit(1))
            tenant = tenant_res.scalar_one_or_none()

            if not tenant:
                tenant = Tenant(
                    id="tenant-arb-default",
                    name="ARB SoftTech Enterprise",
                    slug="arb-softtech",
                    industry="Telecommunications",
                    is_active=True,
                )
                session.add(tenant)
                await session.flush()
                logger.info("[Seeder] Created default tenant: ARB SoftTech Enterprise")

            # Check if telephony config exists
            tel_res = await session.execute(select(TelephonyConfig).limit(1))
            tel_config = tel_res.scalar_one_or_none()
            if not tel_config:
                vobiz_id = getattr(settings, "VOBIZ_AUTH_ID", "")
                vobiz_token = getattr(settings, "VOBIZ_AUTH_TOKEN", "")
                # No baked-in fallback number: a fresh install used to be
                # seeded with a hard-coded caller number the operator may
                # not own, marked ready-to-dial with EMPTY credentials —
                # telephony looked configured and only failed at dial time.
                from_num = getattr(settings, "VOBIZ_FROM_NUMBER", "") or ""
                creds_present = bool(vobiz_id and vobiz_token)

                import json
                tel_config = TelephonyConfig(
                    provider="vobiz",
                    name="VoBiz Primary Trunk",
                    credentials_json=json.dumps({"auth_id": vobiz_id, "auth_token": vobiz_token}),
                    default_from_number=from_num or None,
                    from_numbers=[from_num] if from_num else [],
                    is_default_outbound=True,
                    is_ready_for_outbound=creds_present,
                    status="active" if creds_present else "unconfigured",
                )
                session.add(tel_config)
                logger.info("[Seeder] Initialized default VoBiz telephony config")

            # Check if agents exist
            agent_res = await session.execute(select(Agent).limit(1))
            existing_agent = agent_res.scalar_one_or_none()

            if not existing_agent:
                agents_to_seed = [
                    Agent(
                        id="agent-admission-advisor",
                        tenant_id=tenant.id,
                        name="Admission & Career Counselor",
                        purpose="Guide students and parents on degree admissions, syllabus, and enrollment steps",
                        company_name="ARB SoftTech Academy",
                        company_description="Leading institution offering courses in AI, Data Science, and Engineering",
                        greeting_message="नमस्कार जी! मैं ARB SoftTech से बात कर रहा हूँ। क्या आप नए कोर्स और एडमिशन के बारे में जानकारी चाहते हैं?",
                        instructions=(
                            "You are an admission counselor. Speak naturally in polite conversational Hindi.\n"
                            "Answer questions about admissions, fees, and eligibility in 1-2 short sentences.\n"
                            "Ask exactly one question at a time to understand their educational interests.\n"
                            "If they decline or are busy, politely thank them and end the call."
                        ),
                        system_prompt="Conversational Hindi Admission Counselor",
                        voice_gender="male",
                        voice_id="shubh",
                        voice_name="Shubh - Conversational Hindi Male",
                        tts_provider="sarvam",
                        language_mode="auto_match",
                        primary_language="hi",
                        default_language="Hindi",
                        supported_languages=["Hindi", "English"],
                        speaking_speed=1.0,
                        concurrency=5,
                        provider="vobiz",
                        enabled=True,
                    ),
                    Agent(
                        id="agent-real-estate",
                        tenant_id=tenant.id,
                        name="Priya (Real Estate Advisor)",
                        purpose="Qualify prospective property buyers and schedule site visit appointments",
                        company_name="ARB Luxury Realty",
                        company_description="Premium residential and commercial properties with verified clear titles",
                        greeting_message="नमस्ते! मैं ARB Realty से प्रिया बोल रही हूँ। क्या आप नए 2 और 3 BHK रेसिडेंशियल प्रोजेक्ट्स देख रहे हैं?",
                        instructions=(
                            "You are a property advisor. Speak in warm, professional Hindi/Hinglish.\n"
                            "Highlight key property features (metro connectivity, amenities) in 1-2 concise sentences.\n"
                            "Check their budget and schedule a free site visit if they are interested.\n"
                            "If not interested, politely wish them a great day and wrap up immediately."
                        ),
                        system_prompt="Conversational Hindi Real Estate Specialist",
                        voice_gender="female",
                        voice_id="ritu",
                        voice_name="Ritu - Expressive Hindi Female",
                        tts_provider="sarvam",
                        language_mode="auto_match",
                        primary_language="hi",
                        default_language="Hindi",
                        supported_languages=["Hindi", "English"],
                        speaking_speed=1.0,
                        concurrency=5,
                        provider="vobiz",
                        enabled=True,
                    ),
                    Agent(
                        id="agent-technical-support",
                        tenant_id=tenant.id,
                        name="Raj (Broadband & Fiber Support)",
                        purpose="Assist customers with internet connectivity, plan upgrades, and technician booking",
                        company_name="ARB Fiber Net",
                        company_description="High-speed optical fiber internet provider",
                        greeting_message="नमस्ते! मैं ARB Fiber Net से राज बात कर रहा हूँ। क्या आपके ब्रॉडबैंड कनेक्शन में कोई समस्या आ रही है?",
                        instructions=(
                            "You are a customer support agent. Speak courteously and assist with internet issues.\n"
                            "Confirm their router light status and offer quick troubleshooting or engineer visit.\n"
                            "Keep all replies strictly within 1-2 short sentences in Hindi.\n"
                            "Close politely once resolved."
                        ),
                        system_prompt="Conversational Technical Support Assistant",
                        voice_gender="male",
                        voice_id="aditya",
                        voice_name="Aditya - Friendly Hindi Male",
                        tts_provider="sarvam",
                        language_mode="auto_match",
                        primary_language="hi",
                        default_language="Hindi",
                        supported_languages=["Hindi", "English"],
                        speaking_speed=1.0,
                        concurrency=5,
                        provider="vobiz",
                        enabled=True,
                    ),
                ]

                for ag in agents_to_seed:
                    session.add(ag)

                logger.info(f"[Seeder] Seeded {len(agents_to_seed)} pre-configured voice calling agents.")

            await session.commit()
    except Exception as e:
        logger.warning(f"[Seeder] Database seeding warning: {e}")
