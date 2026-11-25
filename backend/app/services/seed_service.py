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
from app.models.questionnaire import Questionnaire
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
                        id="agent-arb-sales-executive",
                        tenant_id=tenant.id,
                        name="ARB Sales & Solutions Executive",
                        purpose="Qualify business prospects, capture customer name, explain AI calling solutions & pricing, and close calls.",
                        company_name="ARB SoftTech",
                        company_description="Leading provider of Enterprise AI Voice Calling, Telephony Automation, and Lead Qualification Platforms",
                        greeting_message="नमस्ते! मैं ARB SoftTech से बात कर रही हूँ। हम बिज़नेसेज़ के लिए AI वॉइस कॉलिंग और ऑटोमेशन सॉल्यूशंस प्रदान करते हैं। क्या आप इस बारे में 1 मिनट बात करने में रुचि रखते हैं?",
                        instructions=(
                            "You are an ARB SoftTech Sales Executive speaking with potential business clients. Follow this exact flow:\n"
                            "1. First Question: Tell 1 line about ARB SoftTech and ask if they are interested. If customer says NO, thank them politely and end the call. If customer says YES, qualify them as interested and ask for their Name.\n"
                            "2. Ask Name: Once they share their name, acknowledge it and ask which service they are interested in: 1. AI Outbound Calling Agent, 2. Customer Support Automation, or 3. Lead Qualification System.\n"
                            "3. Explain Pricing: Explain that plans start at ₹4,999 per month with unlimited smart calling and real-time lead intelligence.\n"
                            "4. Call Closing: Once the customer says OK, thank them by name and conclude the call gracefully."
                        ),
                        system_prompt="Conversational ARB SoftTech Sales Executive",
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

                # This is the supplied ARB lead-generation questionnaire.
                # Its wording is kept verbatim: the runtime will ask only
                # these items, collect the answers, then hand the lead to a
                # human ARB Sales & Solutions representative.
                sales_agent = next(a for a in agents_to_seed if a.id == "agent-arb-sales-executive")
                sales_questions = [
                    {
                        "question_id": "arb_interest",
                        "text": "Hello, I am calling from ARB SoftTech. We help businesses grow with AI-powered voice calling and lead generation solutions. Are you interested in knowing more?",
                        "expected_answer": "YES / NO question. If the customer says NO, thank them politely and end the call. If the customer says YES, qualify them as INTERESTED and ask for their name.",
                        "type": "yes_no",
                    },
                    {
                        "question_id": "arb_name",
                        "text": "May I know your name, please?",
                        "expected_answer": "Customer's name. Acknowledge it warmly and use it in the closing.",
                        "type": "text",
                    },
                    {
                        "question_id": "arb_service",
                        "text": "Which service are you interested in: 1. AI Outbound Calling Agent, 2. Customer Support Automation, or 3. Lead Qualification System?",
                        "expected_answer": "Record the service they select (1, 2 or 3).",
                        "type": "single_choice",
                    },
                    {
                        "question_id": "arb_pricing_interest",
                        "text": "Our plans start at ₹4,999 per month, with unlimited smart calling and real-time lead intelligence. Shall I note you as interested?",
                        "expected_answer": "Explain the pricing exactly as written. If the customer says OK, proceed to the closing.",
                        "type": "yes_no",
                    },
                    {
                        "question_id": "arb_closing",
                        "text": "Thank you. It was great speaking with you. Our team will call you back shortly with the next steps. Have a great day!",
                        "expected_answer": "Closing line. Thank the customer by name and end the call gracefully.",
                        "type": "closing",
                    },
                ]
                questionnaire = Questionnaire(
                    id="q-arb-sales-lead-generation",
                    tenant_id=tenant.id,
                    agent_id=sales_agent.id,
                    title="ARB SoftTech Sales Lead Generation",
                    description="Lead-generation flow imported from ARB_SoftTech_Sales_Lead_Generation_Questionnaire.xlsx",
                    questions=sales_questions,
                    status="published",
                    is_published=True,
                    version_id="v1",
                )
                from app.services.agent_service import format_questionnaire_prompt_block
                sales_agent.greeting_message = sales_questions[0]["text"]
                sales_agent.questionnaire_id = questionnaire.id
                sales_agent.instructions = format_questionnaire_prompt_block(questionnaire.title, sales_questions)
                sales_agent.system_prompt = sales_agent.instructions
                session.add(questionnaire)

                logger.info(f"[Seeder] Seeded {len(agents_to_seed)} pre-configured voice calling agents.")

            await session.commit()
    except Exception as e:
        logger.warning(f"[Seeder] Database seeding warning: {e}")
