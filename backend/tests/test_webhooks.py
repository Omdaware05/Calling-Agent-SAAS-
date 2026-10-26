import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_processing(client: AsyncClient, monkeypatch):
    # Mock Dograh calls
    async def fake_sync(*args, **kwargs):
        return 123, "test-trigger"

    async def fake_initiate(*args, **kwargs):
        return {"status": "success", "workflow_run_id": 789, "workflow_run_name": "WR-API-789"}

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

    # 1. Create agent & initiate call
    agent_resp = await client.post(
        "/api/agents",
        json={
            "name": "Webhook Test Agent",
            "purpose": "Webhook Testing",
            "instructions": "Testing webhooks",
            "allowed_topics": ["Test"],
            "restricted_topics": [],
            "behavior_rules": [],
            "enabled": True,
        },
    )
    agent_id = agent_resp.json()["id"]

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

    call_resp = await client.post(
        "/api/calls/initiate",
        json={"phone_number": "+14155552671", "agent_id": agent_id},
    )
    assert call_resp.status_code == 200
    call_id = call_resp.json()["call_id"]

    # 2. Send webhook from Dograh
    webhook_payload = {
        "call_id": call_id,
        "workflow_run_id": 789,
        "status": "completed",
        "disposition": "interested",
        "duration": 78.5,
        "transcript_url": "https://minio.dograh.local/voice-audio/transcripts/789.json",
        "recording_url": "https://minio.dograh.local/voice-audio/recordings/789.wav",
    }
    wh_resp = await client.post("/api/webhooks/dograh", json=webhook_payload)
    assert wh_resp.status_code == 200
    assert wh_resp.json()["processed"] is True

    # 3. Verify call status updated
    status_resp = await client.get(f"/api/calls/{call_id}/status")
    assert status_resp.status_code == 200
    call_data = status_resp.json()
    assert call_data["status"] == "completed"
    assert call_data["duration"] == 78.5
    assert call_data["disposition"] == "interested"
    assert call_data["transcript_url"] in (
        f"/api/v1/calls/{call_id}/transcript",
        "https://minio.dograh.local/voice-audio/transcripts/789.json",
    )
    assert call_data["recording_url"] in (
        f"/api/v1/calls/{call_id}/recording",
        "https://minio.dograh.local/voice-audio/recordings/789.wav",
    )
