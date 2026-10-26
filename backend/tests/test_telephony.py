import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_telephony_providers(client: AsyncClient):
    resp = await client.get("/api/telephony/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    providers = data["providers"]
    assert len(providers) >= 7
    provider_names = [p["provider"] for p in providers]
    for expected in ["twilio", "plivo", "telnyx", "vonage", "vobiz", "cloudonix", "ari"]:
        assert expected in provider_names


@pytest.mark.asyncio
async def test_get_telephony_readiness_initially_false(client: AsyncClient):
    resp = await client.get("/api/telephony/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is False
    assert "steps" in data


@pytest.mark.asyncio
async def test_save_and_get_telephony_config(client: AsyncClient):
    payload = {
        "provider": "twilio",
        "name": "Production Twilio Account",
        "credentials": {
            "account_sid": "mock_twilio_account_sid_placeholder",
            "auth_token": "mock_twilio_auth_token_placeholder",
        },
        "from_numbers": ["+12025550199"],
        "default_from_number": "+12025550199",
        "is_default_outbound": True,
    }

    # Save
    resp = await client.post("/api/telephony/config", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "twilio"
    assert data["name"] == "Production Twilio Account"
    assert "+12025550199" in data["from_numbers"]
    # Verify auth_token is masked
    assert data["masked_credentials"]["auth_token"] != "secret_auth_token_value_here"
    assert "••••" in data["masked_credentials"]["auth_token"]

    # Get active config
    get_resp = await client.get("/api/telephony/config")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["provider"] == "twilio"
    assert get_data["masked_credentials"]["auth_token"] != "secret_auth_token_value_here"


@pytest.mark.asyncio
async def test_telephony_test_connection_invalid(client: AsyncClient):
    test_payload = {
        "provider": "twilio",
        "credentials": {
            "account_sid": "ACinvalidSID00000000000000000000",
            "auth_token": "invalidToken",
        },
    }
    resp = await client.post("/api/telephony/test", json=test_payload)
    assert resp.status_code == 200
    data = resp.json()
    # Upstream should fail authentication
    assert data["success"] is False
