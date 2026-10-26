import pytest
from httpx import AsyncClient
from app.services.questionnaire_runtime_service import FastQuestionnaireOrchestrator


@pytest.mark.asyncio
async def test_agent_creation_with_default_and_custom_company_greeting(client: AsyncClient, monkeypatch):
    synced_workflows = []

    async def fake_sync(*args, **kwargs):
        synced_workflows.append(kwargs)
        return 999, "mock-trigger"

    from app.services.dograh_service import dograh_service
    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)

    # 1. Create agent with custom company name & greeting
    payload_custom = {
        "name": "Rohan",
        "purpose": "Sell organic fertilizers and seeds",
        "company_name": "Sahyadri Agro Solutions",
        "company_description": "We supply certified bio-fertilizers and hybrid seeds with doorstep delivery across Maharashtra.",
        "greeting_message": "नमस्कार! मी सह्याद्री अ‍ॅग्रो सोल्युशन्स कडून रोहन बोलत आहे. आम्ही सेंद्रिय खतांवर विशेष सवलत देत आहोत.",
        "instructions": "Help farmers understand our organic fertilizers and seed options.",
        "default_language": "Marathi",
        "enabled": True,
    }

    resp = await client.post("/api/agents", json=payload_custom)
    assert resp.status_code == 201
    data = resp.json()

    assert data["company_name"] == "Sahyadri Agro Solutions"
    assert "सह्याद्री अ‍ॅग्रो" in data["greeting_message"]
    assert "bio-fertilizers" in data["company_description"]

    # Verify Dograh sync was passed the pre-defined company & greeting
    assert len(synced_workflows) > 0
    last_sync = synced_workflows[-1]
    assert last_sync["company_name"] == "Sahyadri Agro Solutions"
    assert "सह्याद्री अ‍ॅग्रो" in last_sync["greeting_message"]

    # 2. Create agent without specifying greeting -> greeting_message is None (no default greeting forced)
    payload_default = {
        "name": "Pooja",
        "purpose": "Offer data analytics training with 100% placement",
        "instructions": "Explain curriculum and batches.",
        "enabled": True,
    }

    resp_def = await client.post("/api/agents", json=payload_default)
    assert resp_def.status_code == 201
    data_def = resp_def.json()

    # Default company name is set, but greeting_message remains None
    assert data_def["company_name"] == "Voxora Technologies"
    assert data_def.get("greeting_message") is None


@pytest.mark.asyncio
async def test_fast_orchestrator_turn_0_greeting_and_identity_faqs():
    system_prompt = (
        "AGENT IDENTITY & PERSONA:\n"
        "- Agent Name: 'Aarti', AI Voice Assistant\n"
        "- Company / Organization: 'EduTech Pro Global'\n"
        "- Company Specialty: We provide industry-recognized AI and Python certified courses.\n"
        "- Primary Role: Student admissions and curriculum guidance\n\n"
        "SYSTEM INSTRUCTIONS:\n"
        "Greet the caller naturally based on your role, persona, and instructions.\n\n"
        "### MANDATORY QUESTIONNAIRE SCRIPT (Student Survey):\n"
        "1. Question: \"क्या आप कॉलेज के छात्र हैं या वर्किंग प्रोफेशनल?\"\n"
        "   - Expected Answer / Reference: \"दोनों के लिए वीकेंड और रेगुलर बैचेस हैं।\"\n"
        "2. Question: \"क्या आपको पायथन की बेसिक नॉलेज है?\"\n"
        "   - Expected Answer / Reference: \"शुरुआती छात्रों के लिए बेसिक से ट्रेनिंग है।\"\n"
    )

    # Turn 0: Caller answers the phone and says "Hello, who is this?" or "Haan boliye"
    messages_turn0 = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello, kaun bol raha hai?"}
    ]
    reply0 = FastQuestionnaireOrchestrator.resolve_next_turn(messages_turn0)
    # Turn 0 must return None so the role prompt & instructions go to LLM to create dynamic greeting!
    assert reply0 is None

    # Turn 0 (Standard pickup): Caller says "Hello / Haan boliye"
    messages_pickup = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Haan boliye"}
    ]
    reply_pickup = FastQuestionnaireOrchestrator.resolve_next_turn(messages_pickup)
    assert reply_pickup is None

    # LLM dynamically creates opening greeting & introduces Question 1 based on role prompt & system instructions
    llm_generated_opening = "नमस्ते जी! मैं EduTech Pro Global से Aarti बात कर रही हूँ। क्या आप कॉलेज के छात्र हैं या वर्किंग प्रोफेशनल?"

    # Inquiry about company name: "Aap kis company se baat kar rahe ho?"
    messages_comp_inquiry = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": llm_generated_opening},
        {"role": "user", "content": "Ye konsi company hai?"}
    ]
    reply_comp = FastQuestionnaireOrchestrator.resolve_next_turn(messages_comp_inquiry)
    assert reply_comp is not None
    # Direct company answer based on role prompt metadata without slow LLM re-generation!
    assert "EduTech Pro Global" in reply_comp

    # Inquiry about call reason: "Aapne phone kyu kiya?"
    messages_reason = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": llm_generated_opening},
        {"role": "user", "content": "Aapne call kis liye kiya hai?"}
    ]
    reply_reason = FastQuestionnaireOrchestrator.resolve_next_turn(messages_reason)
    assert reply_reason is not None
    assert "जानकारी" in reply_reason or "AI" in reply_reason

    # WhatsApp request: "Details WhatsApp par bhej do"
    messages_wa = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": llm_generated_opening},
        {"role": "user", "content": "Mujhe WhatsApp par details bhej do"}
    ]
    reply_wa = FastQuestionnaireOrchestrator.resolve_next_turn(messages_wa)
    assert reply_wa is not None
    assert "WhatsApp" in reply_wa

    # Busy / Reschedule: "Abhi main driving kar raha hu, baad me call karo"
    messages_busy = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": llm_generated_opening},
        {"role": "user", "content": "Abhi main busy hu, bad me phone karo"}
    ]
    reply_busy = FastQuestionnaireOrchestrator.resolve_next_turn(messages_busy)
    assert reply_busy is not None
    assert "बाद में कॉल करेंगे" in reply_busy
