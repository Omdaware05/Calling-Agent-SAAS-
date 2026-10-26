from typing import Optional
from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security = HTTPBearer(auto_error=False)


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
