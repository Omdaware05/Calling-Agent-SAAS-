import json
import logging
import re
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.telephony import TelephonyConfig
from app.schemas.telephony import (
    ProviderFieldOption,
    ProviderFieldSchema,
    ProviderMetadataSchema,
    ReadinessCheckStep,
    TelephonyConfigRequest,
    TelephonyConfigResponse,
    TelephonyReadinessResponse,
    TelephonyTestRequest,
    TelephonyTestResponse,
)
from app.services.dograh_service import DograhServiceException, dograh_service

logger = logging.getLogger(__name__)

# Fallback metadata if Dograh metadata endpoint is temporarily unavailable
DEFAULT_PROVIDER_METADATA: List[Dict[str, Any]] = [
    {
        "provider": "twilio",
        "display_name": "Twilio",
        "connectivity": "api",
        "docs_url": "https://www.twilio.com/docs",
        "fields": [
            {
                "name": "account_sid",
                "label": "Account SID",
                "type": "text",
                "required": True,
                "sensitive": False,
                "description": "Found on your Twilio Console dashboard (starts with AC)",
                "placeholder": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            },
            {
                "name": "auth_token",
                "label": "Auth Token",
                "type": "password",
                "required": True,
                "sensitive": True,
                "description": "Your Twilio primary authentication token",
                "placeholder": "••••••••••••••••••••••••••••••••",
            },
            {
                "name": "from_numbers",
                "label": "Caller ID Phone Numbers",
                "type": "string-array",
                "required": True,
                "sensitive": False,
                "description": "E.164 phone numbers purchased or verified in Twilio (e.g. +12025550199)",
                "placeholder": "+1234567890",
            },
            {
                "name": "amd_enabled",
                "label": "Enable Answering Machine Detection (AMD)",
                "type": "bool",
                "required": False,
                "sensitive": False,
                "description": "Detect whether a human or voicemail answered the call",
            },
        ],
    },
    {
        "provider": "plivo",
        "display_name": "Plivo",
        "connectivity": "api",
        "docs_url": "https://www.plivo.com/docs",
        "fields": [
            {
                "name": "auth_id",
                "label": "Auth ID",
                "type": "text",
                "required": True,
                "sensitive": False,
                "description": "Plivo Auth ID from your console",
                "placeholder": "MAMXXXXXXXXXXXXXXXXX",
            },
            {
                "name": "auth_token",
                "label": "Auth Token",
                "type": "password",
                "required": True,
                "sensitive": True,
                "description": "Plivo Auth Token",
                "placeholder": "••••••••••••••••••••••••••••••••",
            },
            {
                "name": "application_id",
                "label": "Application ID (Optional)",
                "type": "text",
                "required": False,
                "sensitive": False,
                "description": "Leave blank to let Dograh auto-create a sub-application",
                "placeholder": "Auto-created if omitted",
            },
            {
                "name": "from_numbers",
                "label": "Caller ID Phone Numbers",
                "type": "string-array",
                "required": True,
                "sensitive": False,
                "description": "Plivo outbound phone numbers in E.164 format",
                "placeholder": "+1234567890",
            },
        ],
    },
    {
        "provider": "telnyx",
        "display_name": "Telnyx",
        "connectivity": "api",
        "docs_url": "https://developers.telnyx.com",
        "fields": [
            {
                "name": "api_key",
                "label": "API Key",
                "type": "password",
                "required": True,
                "sensitive": True,
                "description": "Telnyx V2 API Key from Mission Control Portal",
                "placeholder": "KEY••••••••••••••••••••••••••••",
            },
            {
                "name": "connection_id",
                "label": "Connection ID (Optional)",
                "type": "text",
                "required": False,
                "sensitive": False,
                "description": "Call Control Application ID (auto-created if left blank)",
                "placeholder": "Auto-created if omitted",
            },
            {
                "name": "webhook_public_key",
                "label": "Webhook Public Key (Optional)",
                "type": "text",
                "required": False,
                "sensitive": False,
                "description": "For inbound webhook signature verification",
            },
            {
                "name": "from_numbers",
                "label": "Caller ID Phone Numbers",
                "type": "string-array",
                "required": True,
                "sensitive": False,
                "description": "Telnyx assigned phone numbers in E.164 format",
                "placeholder": "+1234567890",
            },
        ],
    },
    {
        "provider": "vonage",
        "display_name": "Vonage",
        "connectivity": "api",
        "docs_url": "https://developer.vonage.com",
        "fields": [
            {
                "name": "application_id",
                "label": "Application ID",
                "type": "text",
                "required": True,
                "sensitive": False,
                "description": "Vonage Voice API Application UUID",
                "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            },
            {
                "name": "private_key",
                "label": "Private Key",
                "type": "textarea",
                "required": True,
                "sensitive": True,
                "description": "PEM-formatted private key downloaded from Vonage dashboard",
                "placeholder": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
            },
            {
                "name": "api_key",
                "label": "API Key",
                "type": "text",
                "required": True,
                "sensitive": False,
                "description": "Vonage Account API Key",
            },
            {
                "name": "api_secret",
                "label": "API Secret",
                "type": "password",
                "required": True,
                "sensitive": True,
                "description": "Vonage Account API Secret",
            },
            {
                "name": "from_numbers",
                "label": "Caller ID Phone Numbers",
                "type": "string-array",
                "required": True,
                "sensitive": False,
                "description": "Vonage virtual phone numbers in E.164 format",
                "placeholder": "+1234567890",
            },
        ],
    },
    {
        "provider": "vobiz",
        "display_name": "Vobiz",
        "connectivity": "api",
        "docs_url": "https://vobiz.ai",
        "fields": [
            {
                "name": "auth_id",
                "label": "Auth ID",
                "type": "text",
                "required": True,
                "sensitive": False,
                "placeholder": "Vobiz Auth ID",
            },
            {
                "name": "auth_token",
                "label": "Auth Token",
                "type": "password",
                "required": True,
                "sensitive": True,
                "placeholder": "••••••••••••••••",
            },
            {
                "name": "from_numbers",
                "label": "Caller ID Phone Numbers",
                "type": "string-array",
                "required": True,
                "sensitive": False,
                "description": "Vobiz assigned phone numbers in E.164 format",
                "placeholder": "+1234567890",
            },
        ],
    },
    {
        "provider": "cloudonix",
        "display_name": "Cloudonix",
        "connectivity": "sip",
        "docs_url": "https://docs.cloudonix.io",
        "fields": [
            {
                "name": "bearer_token",
                "label": "Bearer Token",
                "type": "password",
                "required": True,
                "sensitive": True,
                "description": "Cloudonix API Bearer Token",
                "placeholder": "••••••••••••••••",
            },
            {
                "name": "domain_id",
                "label": "Domain / Realm",
                "type": "text",
                "required": True,
                "sensitive": False,
                "description": "Your Cloudonix voice domain",
                "placeholder": "domain.cloudonix.net",
            },
            {
                "name": "from_numbers",
                "label": "Caller ID / Trunks",
                "type": "string-array",
                "required": True,
                "sensitive": False,
                "description": "E.164 phone numbers or SIP caller addresses",
                "placeholder": "+1234567890",
            },
        ],
    },
    {
        "provider": "ari",
        "display_name": "Asterisk ARI",
        "connectivity": "sip",
        "docs_url": "https://wiki.asterisk.org/wiki/display/AST/Asterisk+REST+Interface",
        "fields": [
            {
                "name": "ari_endpoint",
                "label": "ARI Endpoint URL",
                "type": "text",
                "required": True,
                "sensitive": False,
                "description": "HTTP(S) base URL of your Asterisk ARI instance",
                "placeholder": "http://asterisk.local:8088/ari",
            },
            {
                "name": "app_name",
                "label": "ARI Username / App Name",
                "type": "text",
                "required": True,
                "sensitive": False,
                "placeholder": "asterisk_user",
            },
            {
                "name": "app_password",
                "label": "ARI Password / Secret",
                "type": "password",
                "required": True,
                "sensitive": True,
                "placeholder": "••••••••••••••••",
            },
            {
                "name": "from_numbers",
                "label": "Caller IDs / Extensions",
                "type": "string-array",
                "required": True,
                "sensitive": False,
                "description": "Caller extensions or E.164 DIDs",
                "placeholder": "1001",
            },
        ],
    },
]


def mask_secret(value: Any) -> str:
    """Masks sensitive credentials while preserving first/last hints for confirmation."""
    if not value or not isinstance(value, str):
        return "••••••••"
    val = value.strip()
    if len(val) <= 6:
        return "••••" + val[-2:] if len(val) >= 2 else "••••"
    if val.startswith("AC") or val.startswith("SK") or val.startswith("KEY"):
        prefix = val[:4]
        suffix = val[-4:]
        return f"{prefix}••••••••{suffix}"
    return f"{val[:2]}••••••••{val[-4:]}"


def mask_credentials_dict(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a copy of credentials with sensitive strings securely masked."""
    sensitive_keys = {
        "auth_token",
        "api_key",
        "api_secret",
        "private_key",
        "bearer_token",
        "app_password",
        "password",
        "secret",
        "token",
    }
    masked = {}
    for k, v in credentials.items():
        if k.lower() in sensitive_keys or any(s in k.lower() for s in ("token", "secret", "password", "key")):
            masked[k] = mask_secret(v)
        else:
            masked[k] = v
    return masked


class TelephonyService:
    def __init__(self):
        self.base_url = settings.DOGRAH_BASE_URL.rstrip("/")
        self.api_key = settings.DOGRAH_API_KEY

    def _get_dograh_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def get_providers_metadata(self) -> List[ProviderMetadataSchema]:
        """Fetch provider metadata from Dograh with a fallback cache."""
        url = f"{self.base_url}/api/v1/organizations/telephony-providers/metadata"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._get_dograh_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    providers = data.get("providers", [])
                    return [ProviderMetadataSchema(**p) for p in providers]
        except Exception as e:
            logger.warning(f"Could not load metadata from Dograh: {e}; using fallback.")

        # Fallback to local schema
        return [ProviderMetadataSchema(**p) for p in DEFAULT_PROVIDER_METADATA]

    async def get_active_config(self, session: AsyncSession) -> Optional[TelephonyConfigResponse]:
        """Returns the currently active telephony configuration from DB."""
        stmt = (
            select(TelephonyConfig)
            .order_by(TelephonyConfig.is_default_outbound.desc(), desc(TelephonyConfig.updated_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            # Also check if Dograh has any ready configs that can be synced
            await self._sync_from_dograh_if_needed(session)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

        if not record:
            return None

        # Parse stored credentials and mask
        try:
            creds = json.loads(record.credentials_json) if record.credentials_json else {}
        except Exception:
            creds = {}

        return TelephonyConfigResponse(
            id=record.id,
            provider=record.provider,
            name=record.name,
            dograh_config_id=record.dograh_config_id,
            masked_credentials=mask_credentials_dict(creds),
            from_numbers=record.from_numbers or [],
            default_from_number=record.default_from_number,
            is_default_outbound=record.is_default_outbound,
            is_ready_for_outbound=record.is_ready_for_outbound,
            outbound_blocked_reason=record.outbound_blocked_reason,
            status=record.status,
            last_tested_at=record.last_tested_at,
            last_test_error=record.last_test_error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def _sync_from_dograh_if_needed(self, session: AsyncSession):
        """Syncs ready configurations from Dograh into local DB."""
        url = f"{self.base_url}/api/v1/organizations/telephony-configs"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._get_dograh_headers())
                if resp.status_code == 200:
                    configs = resp.json().get("configurations", [])
                    for cfg in configs:
                        if cfg.get("is_ready_for_outbound") or cfg.get("is_default_outbound"):
                            # Check if exists
                            stmt = select(TelephonyConfig).where(TelephonyConfig.dograh_config_id == cfg["id"])
                            res = await session.execute(stmt)
                            existing = res.scalar_one_or_none()
                            if not existing:
                                new_rec = TelephonyConfig(
                                    provider=cfg["provider"],
                                    name=cfg["name"],
                                    dograh_config_id=cfg["id"],
                                    credentials_json="{}",
                                    from_numbers=[],
                                    is_default_outbound=cfg.get("is_default_outbound", False),
                                    is_ready_for_outbound=cfg.get("is_ready_for_outbound", False),
                                    outbound_blocked_reason=cfg.get("outbound_blocked_reason"),
                                    status="ready" if cfg.get("is_ready_for_outbound") else "incomplete",
                                )
                                session.add(new_rec)
                                await session.commit()
        except Exception as e:
            logger.debug(f"Sync from Dograh skipped: {e}")

    async def save_config(
        self, session: AsyncSession, request: TelephonyConfigRequest
    ) -> TelephonyConfigResponse:
        """
        Saves telephony configuration:
        1. Encrypts/stores credentials locally.
        2. Provisions configuration in Dograh.
        3. Registers caller IDs / phone numbers with Dograh.
        4. Sets as default outbound in Dograh.
        5. Updates local record with Dograh config ID and readiness.
        """
        provider = request.provider.lower().strip()
        name = request.name.strip() or f"{provider.capitalize()} Config"
        credentials = dict(request.credentials or {})
        from_numbers = [n.strip() for n in request.from_numbers if n and n.strip()]
        default_from = request.default_from_number or (from_numbers[0] if from_numbers else None)

        # 1. Look for existing config with same provider or active
        stmt = select(TelephonyConfig).where(TelephonyConfig.provider == provider).limit(1)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            record = TelephonyConfig(
                provider=provider,
                name=name,
                credentials_json=json.dumps(credentials),
                from_numbers=from_numbers,
                default_from_number=default_from,
                is_default_outbound=request.is_default_outbound,
                status="incomplete",
            )
            session.add(record)
        else:
            record.name = name
            # Merge credentials so masked unchanged values are not overwritten by placeholder asterisks
            try:
                old_creds = json.loads(record.credentials_json) if record.credentials_json else {}
            except Exception:
                old_creds = {}
            for k, v in credentials.items():
                if isinstance(v, str) and "••" in v:
                    # Keep old credential if masked
                    credentials[k] = old_creds.get(k, "")
            record.credentials_json = json.dumps(credentials)
            record.from_numbers = from_numbers
            record.default_from_number = default_from
            record.is_default_outbound = request.is_default_outbound

        await session.commit()
        await session.refresh(record)

        # 2. Provision in Dograh if reachable
        dograh_id = record.dograh_config_id
        is_ready = False
        blocked_reason = None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Prepare Dograh payload
                dograh_payload = {
                    "name": name,
                    "is_default_outbound": request.is_default_outbound,
                    "config": {
                        "provider": provider,
                        **credentials,
                        "from_numbers": from_numbers,
                    },
                }

                if dograh_id:
                    # Update existing config in Dograh
                    put_url = f"{self.base_url}/api/v1/organizations/telephony-configs/{dograh_id}"
                    resp = await client.put(put_url, json=dograh_payload, headers=self._get_dograh_headers())
                    if resp.status_code not in (200, 201):
                        # Try POST instead if PUT fails
                        dograh_id = None

                if not dograh_id:
                    # Create new config in Dograh
                    post_url = f"{self.base_url}/api/v1/organizations/telephony-configs"
                    resp = await client.post(post_url, json=dograh_payload, headers=self._get_dograh_headers())
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        dograh_id = data.get("id")
                        record.dograh_config_id = dograh_id
                    else:
                        logger.warning(f"Dograh config creation returned {resp.status_code}: {resp.text}")
                        error_detail = ""
                        try:
                            error_detail = resp.json().get("detail", resp.text)
                        except Exception:
                            error_detail = resp.text
                        blocked_reason = f"Voice engine sync failed ({resp.status_code}): {error_detail}"

                # 3. Add phone numbers to Dograh configuration
                if dograh_id and from_numbers:
                    for num in from_numbers:
                        num_url = f"{self.base_url}/api/v1/organizations/telephony-configs/{dograh_id}/phone-numbers"
                        num_payload = {
                            "address": num,
                            "is_active": True,
                            "is_default_caller_id": (num == default_from),
                        }
                        await client.post(num_url, json=num_payload, headers=self._get_dograh_headers())

                # 4. Set as default outbound in Dograh
                if dograh_id and request.is_default_outbound:
                    def_url = f"{self.base_url}/api/v1/organizations/telephony-configs/{dograh_id}/set-default-outbound"
                    await client.post(def_url, headers=self._get_dograh_headers())

                # 5. Fetch updated status from Dograh
                if dograh_id:
                    get_url = f"{self.base_url}/api/v1/organizations/telephony-configs/{dograh_id}"
                    status_resp = await client.get(get_url, headers=self._get_dograh_headers())
                    if status_resp.status_code == 200:
                        detail = status_resp.json()
                        is_ready = detail.get("is_ready_for_outbound", True)
                        blocked_reason = detail.get("outbound_blocked_reason")
                    else:
                        is_ready = bool(from_numbers)
                else:
                    is_ready = False
                    if not blocked_reason:
                        blocked_reason = "Configuration could not be synchronized with the voice engine."

        except Exception as e:
            logger.error(f"Error provisioning telephony configuration in Dograh: {e}")
            is_ready = False
            blocked_reason = f"Dograh sync error: {str(e)}"

        record.is_ready_for_outbound = is_ready
        record.outbound_blocked_reason = blocked_reason
        record.status = "ready" if is_ready else "incomplete"
        await session.commit()
        await session.refresh(record)

        return TelephonyConfigResponse(
            id=record.id,
            provider=record.provider,
            name=record.name,
            dograh_config_id=record.dograh_config_id,
            masked_credentials=mask_credentials_dict(credentials),
            from_numbers=record.from_numbers or [],
            default_from_number=record.default_from_number,
            is_default_outbound=record.is_default_outbound,
            is_ready_for_outbound=record.is_ready_for_outbound,
            outbound_blocked_reason=record.outbound_blocked_reason,
            status=record.status,
            last_tested_at=record.last_tested_at,
            last_test_error=record.last_test_error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def test_config(self, session: AsyncSession, request: TelephonyTestRequest) -> TelephonyTestResponse:
        """
        Validates provider credentials against the upstream provider API.
        """
        provider = request.provider.lower().strip()
        creds = dict(request.credentials or {})

        # If credentials contain masked values, retrieve stored credentials
        if any(isinstance(v, str) and "••" in v for v in creds.values()):
            stmt = select(TelephonyConfig).where(TelephonyConfig.provider == provider).limit(1)
            res = await session.execute(stmt)
            rec = res.scalar_one_or_none()
            if rec and rec.credentials_json:
                stored = json.loads(rec.credentials_json)
                for k, v in creds.items():
                    if isinstance(v, str) and "••" in v:
                        creds[k] = stored.get(k, "")

        success = False
        message = ""
        details = {}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                if provider == "twilio":
                    account_sid = creds.get("account_sid", "").strip()
                    auth_token = creds.get("auth_token", "").strip()
                    if not account_sid or not auth_token:
                        return TelephonyTestResponse(
                            success=False,
                            message="Both Account SID and Auth Token are required for Twilio.",
                        )
                    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
                    r = await client.get(url, auth=(account_sid, auth_token))
                    if r.status_code == 200:
                        account_data = r.json()
                        success = True
                        friendly_name = account_data.get("friendly_name", "Twilio Account")
                        status = account_data.get("status", "active")
                        message = f"Connected successfully to Twilio: {friendly_name} (Status: {status})"
                        details = {"account_sid": account_sid, "status": status}
                    elif r.status_code == 401:
                        success = False
                        message = "Twilio authentication failed. Check your Account SID and Auth Token."
                    else:
                        success = False
                        message = f"Twilio returned status {r.status_code}: {r.text[:200]}"

                elif provider == "plivo":
                    auth_id = creds.get("auth_id", "").strip()
                    auth_token = creds.get("auth_token", "").strip()
                    if not auth_id or not auth_token:
                        return TelephonyTestResponse(
                            success=False,
                            message="Both Auth ID and Auth Token are required for Plivo.",
                        )
                    url = f"https://api.plivo.com/v1/Account/{auth_id}/"
                    r = await client.get(url, auth=(auth_id, auth_token))
                    if r.status_code == 200:
                        data = r.json()
                        success = True
                        message = f"Connected successfully to Plivo: {data.get('name', 'Account')}"
                        details = {"auth_id": auth_id, "state": data.get("state")}
                    else:
                        success = False
                        message = f"Plivo authentication failed: HTTP {r.status_code}"

                elif provider == "telnyx":
                    api_key = creds.get("api_key", "").strip()
                    if not api_key:
                        return TelephonyTestResponse(
                            success=False,
                            message="API Key is required for Telnyx.",
                        )
                    url = "https://api.telnyx.com/v2/phone_numbers"
                    r = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                    if r.status_code in (200, 201):
                        success = True
                        message = "Connected successfully to Telnyx API."
                        details = {"verified": True}
                    else:
                        success = False
                        message = f"Telnyx API key validation failed: HTTP {r.status_code}"

                elif provider == "vonage":
                    api_key = creds.get("api_key", "").strip()
                    api_secret = creds.get("api_secret", "").strip()
                    if not api_key or not api_secret:
                        return TelephonyTestResponse(
                            success=False,
                            message="API Key and API Secret are required for Vonage.",
                        )
                    url = f"https://rest.nexmo.com/account/get-balance?api_key={api_key}&api_secret={api_secret}"
                    r = await client.get(url)
                    if r.status_code == 200:
                        success = True
                        data = r.json()
                        message = f"Connected successfully to Vonage (Balance: {data.get('value', '0')} EUR)."
                        details = {"balance": data.get("value")}
                    else:
                        success = False
                        message = f"Vonage authentication failed: HTTP {r.status_code}"

                elif provider == "ari":
                    ari_endpoint = creds.get("ari_endpoint", "").strip().rstrip("/")
                    app_name = creds.get("app_name", "").strip()
                    app_password = creds.get("app_password", "").strip()
                    if not ari_endpoint or not app_name:
                        return TelephonyTestResponse(
                            success=False,
                            message="ARI Endpoint URL and Username are required.",
                        )
                    url = f"{ari_endpoint}/asterisk/info"
                    r = await client.get(url, auth=(app_name, app_password))
                    if r.status_code == 200:
                        success = True
                        info = r.json().get("system", {})
                        message = f"Connected to Asterisk ARI ({info.get('version', 'PBX')})."
                        details = {"system": info}
                    else:
                        success = False
                        message = f"Asterisk ARI connection failed: HTTP {r.status_code}"

                elif provider == "vobiz":
                    auth_id = creds.get("auth_id", "").strip()
                    auth_token = creds.get("auth_token", "").strip()
                    if not auth_id or not auth_token:
                        return TelephonyTestResponse(
                            success=False,
                            message="Both Auth ID and Auth Token are required for VoBiz.",
                        )
                    # Real upstream verification (VoBiz mirrors the Plivo
                    # API) — this provider used to fall into the generic
                    # branch below and "pass" with any garbage credentials.
                    url = f"https://api.vobiz.ai/api/v1/account/{auth_id}"
                    r = await client.get(
                        url,
                        headers={"X-Auth-ID": auth_id, "X-Auth-Token": auth_token},
                        auth=(auth_id, auth_token),
                    )
                    if r.status_code == 200:
                        success = True
                        message = "Connected successfully to VoBiz (account verified upstream)."
                        details = {"verified": True}
                    else:
                        success = False
                        message = f"VoBiz authentication failed: HTTP {r.status_code}"

                else:
                    # No upstream verification exists for this provider in
                    # the codebase — report that honestly instead of the
                    # old behaviour: success=True ("validated locally")
                    # whenever any field was non-empty.
                    success = False
                    if any(bool(v) for v in creds.values()):
                        message = f"{provider.capitalize()} credentials are saved, but this provider cannot be verified automatically — place a test call to confirm they work."
                    else:
                        message = f"Please enter credentials for {provider}."
                    details = {"validated_locally": False}

        except Exception as err:
            logger.error(f"Error testing telephony provider {provider}: {err}")
            success = False
            message = f"Connection test failed: {str(err)}"

        # Record test outcome in DB if record exists
        stmt = select(TelephonyConfig).where(TelephonyConfig.provider == provider).limit(1)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            record.last_tested_at = datetime.now(UTC)
            record.last_test_error = None if success else message
            await session.commit()

        return TelephonyTestResponse(success=success, message=message, details=details)

    async def delete_config(self, session: AsyncSession) -> bool:
        """Deletes active telephony configuration from DB and Dograh."""
        stmt = select(TelephonyConfig).order_by(desc(TelephonyConfig.updated_at)).limit(1)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            return False

        if record.dograh_config_id:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    url = f"{self.base_url}/api/v1/organizations/telephony-configs/{record.dograh_config_id}"
                    await client.delete(url, headers=self._get_dograh_headers())
            except Exception as e:
                logger.warning(f"Failed to delete config in Dograh: {e}")

        await session.delete(record)
        await session.commit()
        return True

    async def get_outbound_readiness(self, session: AsyncSession) -> TelephonyReadinessResponse:
        """Evaluates overall outbound readiness with clear step-by-step diagnostics."""
        steps: List[ReadinessCheckStep] = []

        # 1. Config exists
        stmt = (
            select(TelephonyConfig)
            .where(TelephonyConfig.is_default_outbound == True)
            .order_by(desc(TelephonyConfig.updated_at))
            .limit(1)
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            # Fallback to any config
            stmt2 = select(TelephonyConfig).order_by(desc(TelephonyConfig.updated_at)).limit(1)
            res2 = await session.execute(stmt2)
            record = res2.scalar_one_or_none()

        if not record:
            steps.append(
                ReadinessCheckStep(
                    step="telephony_provider_configured",
                    passed=False,
                    message="No telephony provider configured. Please set up Twilio, Plivo, Telnyx, or another provider.",
                )
            )
            return TelephonyReadinessResponse(
                is_ready=False,
                blocked_reason="No telephony provider configured",
                steps=steps,
            )

        steps.append(
            ReadinessCheckStep(
                step="telephony_provider_configured",
                passed=True,
                message=f"Provider '{record.provider.capitalize()}' is configured.",
            )
        )

        # 2. Phone numbers configured
        from_nums = record.from_numbers or []
        has_numbers = len(from_nums) > 0
        steps.append(
            ReadinessCheckStep(
                step="caller_id_configured",
                passed=has_numbers,
                message=(
                    f"Caller ID configured: {record.default_from_number or from_nums[0]}"
                    if has_numbers
                    else "No Caller ID phone number configured for outbound calls."
                ),
            )
        )

        # 3. Upstream Dograh sync
        dograh_ready = record.dograh_config_id is not None
        steps.append(
            ReadinessCheckStep(
                step="dograh_synchronized",
                passed=dograh_ready,
                message="Synced with voice engine" if dograh_ready else "Configuration pending sync with voice engine",
            )
        )

        is_overall_ready = has_numbers and record.status in ("ready", "active")
        blocked = None
        if not has_numbers:
            blocked = "Please add at least one Caller ID / from-phone-number in Telephony Settings."
        elif record.outbound_blocked_reason:
            blocked = record.outbound_blocked_reason

        return TelephonyReadinessResponse(
            is_ready=is_overall_ready,
            provider=record.provider,
            default_caller_id=record.default_from_number or (from_nums[0] if from_nums else None),
            blocked_reason=blocked,
            steps=steps,
        )

    async def hangup_live_telephony_call(
        self,
        call_uuid: Optional[str] = None,
        auth_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> bool:
        """
        Directly terminates an active phone call on the telecom carrier side (VoBiz / Plivo).
        Immediately disconnects the phone call on the callee's device.
        """
        if not call_uuid:
            return False

        a_id = auth_id or settings.VOBIZ_AUTH_ID
        a_token = auth_token or settings.VOBIZ_AUTH_TOKEN
        if not a_id or not a_token:
            return False

        endpoint = f"https://api.vobiz.ai/api/v1/Account/{a_id}/Call/{call_uuid}/"
        headers = {
            "X-Auth-ID": a_id,
            "X-Auth-Token": a_token,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.delete(endpoint, headers=headers)
                if resp.status_code in (200, 204):
                    logger.info(f"VoBiz live call {call_uuid} terminated via carrier DELETE.")
                    return True
                # Fallback: POST status completed
                resp_post = await client.post(endpoint, json={"status": "completed"}, headers=headers)
                if resp_post.status_code in (200, 204):
                    logger.info(f"VoBiz live call {call_uuid} terminated via carrier POST.")
                    return True
                logger.warning(f"VoBiz hangup API returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Error terminating live VoBiz call {call_uuid}: {e}")
        return False


telephony_service = TelephonyService()
