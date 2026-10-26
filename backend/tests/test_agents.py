import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_agent(client: AsyncClient, monkeypatch):
    # Mock Dograh sync so tests don't require running Dograh server
    async def fake_sync(*args, **kwargs):
        return 999, "mock-trigger-path"

    from app.services.dograh_service import dograh_service
    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)

    payload = {
        "name": "Course Sales Agent",
        "purpose": "Sell our company's courses",
        "instructions": "Explain courses, pricing, benefits, eligibility and course details.",
        "allowed_topics": ["Courses", "pricing", "admission", "curriculum"],
        "restricted_topics": ["Politics", "religion", "unrelated topics"],
        "behavior_rules": [
            "If customer is interested -> continue sales conversation.",
            "If customer is not interested -> politely end conversation.",
        ],
        "enabled": True,
    }

    # 1. Create Agent
    resp = await client.post("/api/agents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Course Sales Agent"
    assert data["dograh_workflow_id"] == 999
    assert data["dograh_trigger_path"] == "mock-trigger-path"
    agent_id = data["id"]

    # 2. Get Agent by ID
    get_resp = await client.get(f"/api/agents/{agent_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == agent_id

    # 3. List Agents
    list_resp = await client.get("/api/agents")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 4. Update Agent
    update_resp = await client.put(f"/api/agents/{agent_id}", json={"name": "Updated Sales Agent"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Sales Agent"

    # 5. Delete Agent
    del_resp = await client.delete(f"/api/agents/{agent_id}")
    assert del_resp.status_code == 200

    # 6. Verify deleted
    not_found_resp = await client.get(f"/api/agents/{agent_id}")
    assert not_found_resp.status_code == 404
