import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_call_lifecycle(client: AsyncClient, monkeypatch):
    # Mock Dograh calls
    async def fake_sync(*args, **kwargs):
        return 123, "test-trigger-path"

    async def fake_initiate(*args, **kwargs):
        return {
            "status": "success",
            "workflow_run_id": 456,
            "workflow_run_name": "WR-API-456",
        }

    from app.services.dograh_service import dograh_service
    from app.services.telephony_service import telephony_service
    from app.models.telephony import TelephonyConfig
    from app.schemas.telephony import TelephonyConfigResponse

    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)
    monkeypatch.setattr(dograh_service, "initiate_call", fake_initiate)

    async def fake_save_telephony(session, req):
        cfg = TelephonyConfig(
            provider=req.provider,
            name=req.name,
            dograh_config_id=999,
            credentials_json="{}",
            from_numbers=req.from_numbers,
            default_from_number=req.default_from_number,
            is_default_outbound=req.is_default_outbound,
            is_ready_for_outbound=True,
            status="ready",
        )
        session.add(cfg)
        await session.commit()
        await session.refresh(cfg)
        return TelephonyConfigResponse(
            id=cfg.id,
            provider=cfg.provider,
            name=cfg.name,
            dograh_config_id=999,
            from_numbers=cfg.from_numbers or [],
            default_from_number=cfg.default_from_number,
            is_default_outbound=cfg.is_default_outbound,
            is_ready_for_outbound=True,
            status="ready",
            created_at=cfg.created_at,
            updated_at=cfg.updated_at,
        )

    monkeypatch.setattr(telephony_service, "save_config", fake_save_telephony)

    # 1. Create agent
    agent_resp = await client.post(
        "/api/agents",
        json={
            "name": "Test Sales Agent",
            "purpose": "Course Sales",
            "instructions": "Help caller choose a course",
            "allowed_topics": ["Courses"],
            "restricted_topics": ["Politics"],
            "behavior_rules": ["Be courteous"],
            "enabled": True,
        },
    )
    assert agent_resp.status_code == 201
    agent_id = agent_resp.json()["id"]

    # 2. Initiate call with invalid phone
    bad_phone_resp = await client.post(
        "/api/calls/initiate",
        json={"phone_number": "invalid-phone", "agent_id": agent_id},
    )
    assert bad_phone_resp.status_code == 400
    assert bad_phone_resp.json()["error"] == "INVALID_PHONE_NUMBER"

    # 3. Initiate call with invalid agent
    bad_agent_resp = await client.post(
        "/api/calls/initiate",
        json={"phone_number": "+14155552671", "agent_id": "non-existent-agent"},
    )
    assert bad_agent_resp.status_code == 404
    assert bad_agent_resp.json()["error"] == "AGENT_NOT_FOUND"

    # Set up telephony provider for preflight validation
    await client.post(
        "/api/telephony/config",
        json={
            "provider": "twilio",
            "name": "Test Twilio",
            "credentials": {"account_sid": "AC1234567890", "auth_token": "token123"},
            "from_numbers": ["+12025550199"],
            "default_from_number": "+12025550199",
            "is_default_outbound": True,
        },
    )

    # 4. Initiate successful call
    call_resp = await client.post(
        "/api/calls/initiate",
        json={"phone_number": "+14155552671", "agent_id": agent_id},
    )
    assert call_resp.status_code == 200
    call_data = call_resp.json()
    assert call_data["success"] is True
    call_id = call_data["call_id"]
    assert call_data["status"] == "initiating"

    # 5. Get call status
    status_resp = await client.get(f"/api/calls/{call_id}/status")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["call_id"] == call_id
    assert st_data["phone_number"] == "+14155552671"
    assert st_data["agent_id"] == agent_id
    assert st_data["agent_name"] == "Test Sales Agent"

    # 6. List call history
    hist_resp = await client.get("/api/calls/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["success"] is True
    assert hist_data["total"] >= 1
    assert any(c["call_id"] == call_id for c in hist_data["calls"])
