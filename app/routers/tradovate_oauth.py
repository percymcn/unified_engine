"""
Tradovate OAuth Router
Handles OAuth flow for connecting Tradovate accounts
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import secrets
import httpx
from urllib.parse import urlencode

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.core.config import settings

router = APIRouter(prefix="/api/v1/auth/tradovate", tags=["tradovate-oauth"])

# In-memory state store (use Redis in production for multi-instance deployments)
_oauth_states: dict[str, dict] = {}


@router.get("/authorize")
async def initiate_oauth(
    environment: str = Query("demo", pattern="^(demo|live)$"),
    current_user: User = Depends(get_current_user),
):
    """
    Generate Tradovate OAuth authorization URL.

    The client will redirect the user to this URL to authorize the application.
    After authorization, Tradovate redirects back to the callback URL with a code.

    Args:
        environment: "demo" or "live" - determines which Tradovate environment to use
        current_user: The authenticated user initiating the OAuth flow

    Returns:
        authorization_url: The URL to redirect the user to
        state: The state parameter for CSRF validation
    """
    if not settings.TRADOVATE_CLIENT_ID:
        raise HTTPException(
            status_code=400,
            detail="Tradovate OAuth not configured. Please set TRADOVATE_CLIENT_ID."
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": current_user.id,
        "environment": environment,
    }

    params = {
        "client_id": settings.TRADOVATE_CLIENT_ID,
        "redirect_uri": settings.TRADOVATE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "state": state,
    }

    auth_url = f"https://trader.tradovate.com/oauth?{urlencode(params)}"
    return {"authorization_url": auth_url, "state": state}


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Tradovate"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    db: Session = Depends(get_db),
):
    """
    Handle OAuth callback and exchange authorization code for tokens.

    This endpoint is called by the Next.js BFF after Tradovate redirects
    back with the authorization code.

    Args:
        code: The authorization code from Tradovate
        state: The state parameter to validate against CSRF
        db: Database session

    Returns:
        access_token: The Tradovate access token
        refresh_token: The Tradovate refresh token (if provided)
        expires_in: Token expiration time in seconds
        environment: The Tradovate environment (demo/live)
        user_id: The user ID associated with this token
    """
    # Validate state to prevent CSRF attacks
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state. Please restart the authorization flow."
        )

    environment = state_data["environment"]
    user_id = state_data["user_id"]

    # Select API base URL based on environment
    api_base = (
        "https://live.tradovateapi.com/v1"
        if environment == "live"
        else "https://demo.tradovateapi.com/v1"
    )

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{api_base}/auth/oauthtoken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.TRADOVATE_CLIENT_ID,
                    "client_secret": settings.TRADOVATE_CLIENT_SECRET,
                    "redirect_uri": settings.TRADOVATE_OAUTH_REDIRECT_URI,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30.0,
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Tradovate token exchange timed out"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to connect to Tradovate: {str(e)}"
            )

        if response.status_code != 200:
            # Parse error details if available
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text
            raise HTTPException(
                status_code=400,
                detail=f"Token exchange failed: {error_detail}"
            )

        tokens = response.json()

    # Return tokens to caller (frontend will store them securely)
    return {
        "access_token": tokens.get("accessToken"),
        "refresh_token": tokens.get("refreshToken"),
        "expires_in": tokens.get("expiresIn", 3600),
        "environment": environment,
        "user_id": user_id,
    }
