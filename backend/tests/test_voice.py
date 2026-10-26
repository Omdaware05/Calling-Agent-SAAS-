import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_voice_providers(client: AsyncClient):
    resp = await client.get("/api/voice/providers")
    assert resp.status_code == 200
    providers = resp.json()
    assert len(providers) >= 3
    provider_keys = [p["provider"] for p in providers]
    assert "dograh" in provider_keys
    assert "sarvam" in provider_keys


@pytest.mark.asyncio
async def test_get_voices_catalog(client: AsyncClient, monkeypatch):
    # Mock voice catalog response
    from app.services.voice_service import voice_service

    async def fake_get_voices(provider="dograh", gender=None, language=None, search=None):
        from app.schemas.voice import VoiceItem, VoiceListResponse
        mock_voices = [
            VoiceItem(
                voice_id="dg_voice_4c52528b7a1804810035",
                name="Aarti - Conversationalist",
                gender="female",
                language="hi",
                accent="in",
                description="Indian accented female for relatable dialogue",
                preview_url="https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
            ),
            VoiceItem(
                voice_id="dg_voice_ee5efd12f17797d0ff39",
                name="Aarav - Old Time Storyteller",
                gender="male",
                language="en",
                accent="in",
                description="Warm adult male voice with a slight Indian accent",
                preview_url="https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
            ),
        ]
        if gender:
            mock_voices = [v for v in mock_voices if v.gender == gender.lower()]
        return VoiceListResponse(provider=provider, total=len(mock_voices), voices=mock_voices)

    monkeypatch.setattr(voice_service, "get_voices", fake_get_voices)

    # 1. Fetch all
    resp = await client.get("/api/voice/providers/dograh/voices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["voices"][0]["name"] == "Aarti - Conversationalist"

    # 2. Filter female
    female_resp = await client.get("/api/voice/providers/dograh/voices?gender=female")
    assert female_resp.status_code == 200
    female_data = female_resp.json()
    assert female_data["total"] == 1
    assert female_data["voices"][0]["gender"] == "female"


@pytest.mark.asyncio
async def test_preview_voice_untrusted_url_blocked(client: AsyncClient):
    # SSRF protection test: untrusted domain must be rejected
    resp = await client.get("/api/voice/preview?preview_url=https://attacker.com/malicious.mp3")
    assert resp.status_code == 400
    assert "untrusted" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_and_update_agent_voice(client: AsyncClient, monkeypatch):
    from app.services.dograh_service import dograh_service

    captured_kwargs = {}

    async def fake_sync(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return 101, "trigger-voice-test"

    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)

    payload = {
        "name": "Bilingual Counselor",
        "purpose": "Counsel students in Hindi and English",
        "instructions": "Be helpful, friendly and conversational.",
        "allowed_topics": ["Courses"],
        "restricted_topics": [],
        "behavior_rules": [],
        "enabled": True,
        "voice_gender": "female",
        "voice_id": "dg_voice_4c52528b7a1804810035",
        "voice_name": "Aarti - Conversationalist",
        "tts_provider": "dograh",
        "language_mode": "auto_match",
        "primary_language": "multi",
        "voice_style": "Friendly + Professional + Conversational",
        "speaking_speed": 1.1,
    }

    # Create agent with voice
    resp = await client.post("/api/agents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["voice_id"] == "dg_voice_4c52528b7a1804810035"
    assert data["speaking_speed"] == 1.1
    assert data["language_mode"] == "auto_match"
    assert captured_kwargs.get("voice_id") == "dg_voice_4c52528b7a1804810035"
    assert captured_kwargs.get("speaking_speed") == 1.1

    agent_id = data["id"]

    # Update agent voice
    update_payload = {
        "speaking_speed": 0.9,
        "voice_style": "Calm + Warm",
    }
    update_resp = await client.put(f"/api/agents/{agent_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["speaking_speed"] == 0.9
    assert updated["voice_style"] == "Calm + Warm"
    assert captured_kwargs.get("speaking_speed") == 0.9
    assert captured_kwargs.get("voice_style") == "Calm + Warm"


@pytest.mark.asyncio
async def test_invalid_speaking_speed_rejected(client: AsyncClient):
    payload = {
        "name": "Invalid Speed Agent",
        "purpose": "Test",
        "instructions": "Test",
        "speaking_speed": 3.5,  # Out of bounds (> 2.0)
    }
    resp = await client.post("/api/agents", json=payload)
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_existing_agent_loads_with_defaults(client: AsyncClient, monkeypatch):
    from app.services.dograh_service import dograh_service

    async def fake_sync(*args, **kwargs):
        return 102, "trigger-default-test"

    monkeypatch.setattr(dograh_service, "sync_workflow_to_dograh", fake_sync)

    payload = {
        "name": "Default Voice Agent",
        "purpose": "Testing default voice assignment",
        "instructions": "Testing",
    }
    resp = await client.post("/api/agents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["voice_gender"] == "male"
    assert data["voice_id"] == "hm_omega"
    assert data["speaking_speed"] == 1.0
    assert data["language_mode"] == "auto_match"
