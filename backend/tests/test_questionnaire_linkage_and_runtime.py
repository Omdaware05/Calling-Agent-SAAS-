import pytest
from httpx import AsyncClient
from app.services.questionnaire_runtime_service import FastQuestionnaireOrchestrator


@pytest.mark.asyncio
async def test_questionnaire_assigned_during_agent_creation(client: AsyncClient, monkeypatch):
    synced_instructions = []

    async def fake_sync(*args, **kwargs):
        synced_instructions.append(kwargs.get("instructions", ""))
        return 888, "mock-trigger"

    from app.services.dograh_service import dograh_service
    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)

    # 1. Create a questionnaire first
    q_payload = {
        "title": "Course Eligibility Survey",
        "category": "survey",
        "description": "Survey for applicant qualification",
        "sections": [
            {
                "id": "sec-1",
                "title": "Qualification",
                "questions": [
                    {
                        "id": "q1",
                        "title": "Are you a graduate?",
                        "type": "single_choice",
                        "options": ["Yes", "No"],
                        "expected_answer": "Yes, graduation is preferred.",
                    },
                    {
                        "id": "q2",
                        "title": "Which course are you interested in?",
                        "type": "text",
                        "expected_answer": "We offer AI and Web development tracks.",
                    }
                ]
            }
        ]
    }
    q_resp = await client.post("/api/questionnaires", json=q_payload)
    assert q_resp.status_code == 201
    q_data = q_resp.json()
    q_id = q_data["id"]
    assert q_data["agent_id"] is None

    # 2. Create agent assigning this questionnaire
    agent_payload = {
        "name": "Admissions Officer",
        "purpose": "Screen students",
        "instructions": "Be polite and professional.",
        "questionnaire_id": q_id,
        "enabled": True,
    }
    agent_resp = await client.post("/api/agents", json=agent_payload)
    assert agent_resp.status_code == 201
    agent_data = agent_resp.json()
    agent_id = agent_data["id"]

    # Verify agent has questionnaire_id and enriched instructions
    assert agent_data["questionnaire_id"] == q_id
    assert "MANDATORY QUESTIONNAIRE SCRIPT" in agent_data["instructions"]
    assert "Are you a graduate?" in agent_data["instructions"]
    assert "Which course are you interested in?" in agent_data["instructions"]

    # Verify Dograh was synced with the enriched instructions!
    assert len(synced_instructions) > 0
    assert "MANDATORY QUESTIONNAIRE SCRIPT" in synced_instructions[-1]

    # Verify questionnaire is now linked back to agent
    q_get_resp = await client.get(f"/api/questionnaires/{q_id}")
    assert q_get_resp.status_code == 200
    assert q_get_resp.json()["agent_id"] == agent_id


@pytest.mark.asyncio
async def test_questionnaire_assigned_during_questionnaire_creation_and_update(client: AsyncClient, monkeypatch):
    synced_instructions = []

    async def fake_sync(*args, **kwargs):
        synced_instructions.append(kwargs.get("instructions", ""))
        return 777, "mock-trigger"

    from app.services.dograh_service import dograh_service
    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)

    # 1. Create agent without questionnaire
    agent_resp = await client.post("/api/agents", json={
        "name": "Support Bot",
        "purpose": "Customer Support",
        "instructions": "Help the customer resolve issues.",
        "enabled": True,
    })
    assert agent_resp.status_code == 201
    agent_id = agent_resp.json()["id"]

    # 2. Create questionnaire assigning this agent
    q_resp = await client.post("/api/questionnaires", json={
        "title": "Feedback Form",
        "category": "feedback",
        "agent_id": agent_id,
        "sections": [
            {
                "id": "s1",
                "title": "Satisfaction",
                "questions": [
                    {
                        "id": "q1",
                        "title": "How would you rate our service from 1 to 5?",
                        "type": "single_choice",
                        "options": ["1", "2", "3", "4", "5"],
                    }
                ]
            }
        ]
    })
    assert q_resp.status_code == 201
    q_id = q_resp.json()["id"]
    assert q_resp.json()["agent_id"] == agent_id

    # Verify agent is updated with questionnaire_id and enriched instructions
    agent_get = await client.get(f"/api/agents/{agent_id}")
    assert agent_get.status_code == 200
    agent_info = agent_get.json()
    assert agent_info["questionnaire_id"] == q_id
    assert "MANDATORY QUESTIONNAIRE SCRIPT (FEEDBACK FORM)" in agent_info["instructions"]
    assert "How would you rate our service from 1 to 5?" in agent_info["instructions"]


@pytest.mark.asyncio
async def test_fast_questionnaire_orchestrator_deterministic_turns():
    system_prompt = (
        "You are an admissions assistant.\n\n"
        "### MANDATORY QUESTIONNAIRE SCRIPT (Quick Survey):\n"
        "1. Question: \"Are you interested in our Python data science course?\"\n"
        "   - Expected Answer / Reference: \"Yes, our batch begins next Monday.\"\n"
        "2. Question: \"Do you have prior coding experience?\"\n"
        "   - Expected Answer / Reference: \"Beginners are completely welcome.\"\n"
    )

    # Turn 0: Call connected, customer asks "who is this?" -> answered
    # INSTANTLY and deterministically with identity + Q1. (Changed
    # 2026-10-29: the old behaviour — pass Turn 0 to the slow LLM — was the
    # root of the client complaints "welcome speech initiates late" and
    # "agent repeats questions", because the LLM paraphrased Q1 and the
    # paraphrase could not be recognised as asked.)
    messages_turn0 = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello, who is this?"}
    ]
    reply0 = FastQuestionnaireOrchestrator.resolve_next_turn(messages_turn0)
    assert reply0 is not None
    assert "Are you interested in our Python data science course?" in reply0

    # Turn 1: LLM has greeted and asked Q1; Customer answered yes to Q1
    llm_turn0_reply = "Hello! I am an admissions assistant. Are you interested in our Python data science course?"
    messages_turn1 = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": llm_turn0_reply},
        {"role": "user", "content": "Ha interested hu, bataiye details."}
    ]
    reply1 = FastQuestionnaireOrchestrator.resolve_next_turn(messages_turn1)
    assert reply1 is not None
    # Must advance to Question 2
    assert "Do you have prior coding experience?" in reply1

    # Turn 2: Customer answered Q2
    messages_turn2 = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": llm_turn0_reply},
        {"role": "user", "content": "Ha interested hu, bataiye details."},
        {"role": "assistant", "content": reply1},
        {"role": "user", "content": "Haan, basic computer knowledge hai bas."}
    ]
    reply2 = FastQuestionnaireOrchestrator.resolve_next_turn(messages_turn2)
    assert reply2 is not None
    # All questions finished -> Closing thank you!
    assert ("धन्यवाद" in reply2 or "thank you" in reply2.lower())

    # Turn with refusal / not interested: customer says "nahi chahiye mujhe interest nahi hai"
    messages_refusal = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": llm_turn0_reply},
        {"role": "user", "content": "Nahi chahiye mujhe interest nahi hai."}
    ]
    reply_refusal = FastQuestionnaireOrchestrator.resolve_next_turn(messages_refusal)
    assert reply_refusal is not None
    # Must immediately exit politely
    assert ("धन्यवाद" in reply_refusal or "thank you" in reply_refusal.lower() or "दिन शुभ" in reply_refusal)


@pytest.mark.asyncio
async def test_fast_questionnaire_orchestrator_never_repeats_paraphrased_question():
    """Regression (client complaint 2026-10-29): the agent re-asked Q1 when
    it had been spoken in paraphrased words, because asked-question
    detection only matched the verbatim 35-char prefix. Detection is now
    normalised + token-overlap based and advancement is first-unasked."""
    system_prompt = (
        "You are an admissions assistant.\n\n"
        "### MANDATORY QUESTIONNAIRE SCRIPT (Quick Survey):\n"
        "1. Question: \"Are you interested in our Python data science course?\"\n"
        "   - Expected Answer / Reference: \"Yes, our batch begins next Monday.\"\n"
        "2. Question: \"Do you have prior coding experience?\"\n"
        "   - Expected Answer / Reference: \"Beginners are completely welcome.\"\n"
    )
    # Q1 was spoken PARAPHRASED (as an LLM would), customer answered it.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": "Hello! Would you like to know about our Python data science course, are you interested?"},
        {"role": "user", "content": "Yes, tell me more."},
    ]
    reply = FastQuestionnaireOrchestrator.resolve_next_turn(messages)
    assert reply is not None
    # Must advance to Q2 — never repeat Q1 in any form.
    assert "Do you have prior coding experience?" in reply
    assert "interested in our Python" not in reply

