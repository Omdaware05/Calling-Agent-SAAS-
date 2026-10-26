import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_persistence_workflow(client: AsyncClient, monkeypatch):
    # Mock Dograh workflow sync
    async def fake_sync(*args, **kwargs):
        return 777, "mock-trigger-777"

    from app.services.dograh_service import dograh_service
    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)

    # 1. Test Health Endpoint
    health_resp = await client.get("/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()
    assert h_data["service"] == "calling-agent-backend"
    assert "database" in h_data
    assert "storage" in h_data

    # 2. Test Business Creation (POST /api/businesses)
    biz_payload = {
        "name": "Apex Healthcare Solutions",
        "industry": "Healthcare",
        "email": "contact@apexhealth.com",
        "phone": "+14155552671",
        "timezone": "America/New_York",
        "country": "US",
        "preferred_languages": ["en", "es"],
    }
    biz_resp = await client.post("/api/businesses", json=biz_payload)
    assert biz_resp.status_code == 201
    biz_data = biz_resp.json()
    assert biz_data["name"] == "Apex Healthcare Solutions"
    assert "business_id" in biz_data
    biz_id = biz_data["business_id"]

    # 3. Test Business Listing (GET /api/businesses)
    list_biz_resp = await client.get("/api/businesses")
    assert list_biz_resp.status_code == 200
    assert any(b["business_id"] == biz_id for b in list_biz_resp.json())

    # 4. Test Agent Creation with Business Association (POST /api/agents)
    agent_payload = {
        "name": "Healthcare Assistant",
        "purpose": "Appointment scheduling",
        "instructions": "Help patients book appointments.",
        "tenant_id": biz_id,
        "business_id": biz_id,
        "enabled": True,
    }
    agent_resp = await client.post("/api/agents", json=agent_payload)
    assert agent_resp.status_code == 201
    agent_data = agent_resp.json()
    agent_id = agent_data["id"]
    assert agent_data["name"] == "Healthcare Assistant"
    assert agent_data["tenant_id"] == biz_id

    # 5. Test Assign Agent to Business (POST /api/businesses/{id}/agents/{agentId}/assign)
    assign_resp = await client.post(f"/api/businesses/{biz_id}/agents/{agent_id}/assign")
    assert assign_resp.status_code == 200

    # Verify Business now contains assigned agent
    get_biz_resp = await client.get(f"/api/businesses/{biz_id}")
    assert get_biz_resp.status_code == 200
    assert agent_id in get_biz_resp.json()["assigned_agent_ids"]

    # 6. Test Contact Creation (POST /api/contacts)
    contact_payload = {
        "name": "John Doe",
        "phone_number": "+14155552671",
        "email": "john.doe@example.com",
        "agent_id": agent_id,
        "tenant_id": biz_id,
        "custom_fields": {"preferred_time": "morning"},
    }
    contact_resp = await client.post("/api/contacts", json=contact_payload)
    assert contact_resp.status_code == 201
    contact_data = contact_resp.json()
    assert contact_data["phone_number"] == "+14155552671"
    contact_id = contact_data["id"]

    # Verify Contact Listing
    contacts_list = await client.get("/api/contacts")
    assert contacts_list.status_code == 200
    assert any(c["id"] == contact_id for c in contacts_list.json())

    # 7. Test Campaign Creation (POST /api/campaigns)
    campaign_payload = {
        "name": "Spring Flu Outreach",
        "description": "Patient wellness check",
        "agent_id": agent_id,
        "tenant_id": biz_id,
        "phone_numbers": ["+14155552671"],
        "concurrency": 2,
    }
    camp_resp = await client.post("/api/campaigns", json=campaign_payload)
    assert camp_resp.status_code == 201
    camp_data = camp_resp.json()
    assert camp_data["name"] == "Spring Flu Outreach"
    assert camp_data["status"] == "CREATED"
    camp_id = camp_data["id"]

    # Start and Stop Campaign
    start_resp = await client.post(f"/api/campaigns/{camp_id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["campaign"]["status"] == "RUNNING"

    stop_resp = await client.post(f"/api/campaigns/{camp_id}/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["campaign"]["status"] == "STOPPED"

    # 8. Test Questionnaire CRUD (POST & GET /api/questionnaires)
    q_payload = {
        "title": "Patient Wellness Intake",
        "agent_id": agent_id,
        "tenant_id": biz_id,
        "questions": [{"id": "q1", "text": "Are you experiencing any symptoms?", "type": "yes_no"}],
    }
    q_resp = await client.post("/api/questionnaires", json=q_payload)
    assert q_resp.status_code == 201
    q_data = q_resp.json()
    assert q_data["title"] == "Patient Wellness Intake"
    q_id = q_data["id"]

    q_list = await client.get("/api/questionnaires")
    assert q_list.status_code == 200
    assert any(q["id"] == q_id for q in q_list.json())

    # 9. Test Reports for Business (GET /api/reports/business/{id})
    rep_resp = await client.get(f"/api/reports/business/{biz_id}")
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert rep_data["business_id"] == biz_id
    assert "summary" in rep_data
