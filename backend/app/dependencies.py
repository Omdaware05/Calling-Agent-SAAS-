from typing import Optional
from fastapi import Header, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security = HTTPBearer(auto_error=False)


def resolve_tenant_id(
    tenant_id: Optional[str] = Query(None),
    business_id: Optional[str] = Query(None),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_business_id: Optional[str] = Header(None, alias="X-Business-ID"),
) -> Optional[str]:
    """
    Extracts and normalizes the active tenant / business ID from
    query parameters or HTTP request headers.
    Returns None if global / all businesses is requested.
    """
    raw = tenant_id or business_id or x_tenant_id or x_business_id
    if not raw:
        return None
    cleaned = str(raw).strip()
    if cleaned.lower() in ("all", "all_clients", "null", "undefined", ""):
        return None
    return cleaned


async def verify_app_client(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_app_key: Optional[str] = Header(None, alias="X-App-Key"),
) -> bool:
    """
    Validates mobile client authentication against APP_API_KEY.
    If APP_API_KEY is empty (local dev default), all requests are allowed.
    """
    if not settings.APP_API_KEY:
        return True

    token = None
    if auth:
        token = auth.credentials
    elif x_app_key:
        token = x_app_key

    if not token or token != settings.APP_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "UNAUTHORIZED", "message": "Invalid application authentication token"},
        )
    return True


async def verify_webhook_secret(
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
) -> bool:
    """
    Validates Dograh webhook calls if DOGRAH_WEBHOOK_SECRET is configured.
    """
    if not settings.DOGRAH_WEBHOOK_SECRET:
        return True

    if not x_webhook_secret or x_webhook_secret != settings.DOGRAH_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "UNAUTHORIZED_WEBHOOK", "message": "Invalid webhook secret"},
        )
    return True
