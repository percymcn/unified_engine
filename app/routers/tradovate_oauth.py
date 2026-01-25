"""
Tradovate OAuth Router
Handles OAuth flow for connecting Tradovate accounts

Uses Redis for state storage to support multi-process / multi-worker deployments.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import secrets
import httpx
import logging
from urllib.parse import urlencode

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.core.config import settings
from app.cache.redis_client import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/tradovate", tags=["tradovate-oauth"])

# Redis key prefix and TTL for OAuth state
OAUTH_STATE_KEY_PREFIX = "tradovate:oauth_state:"
OAUTH_STATE_TTL_SECONDS = 600  # 10 minutes


async def _store_oauth_state(state: str, data: dict) -> bool:
    """Store OAuth state in Redis with TTL."""
    key = f"{OAUTH_STATE_KEY_PREFIX}{state}"
    result = await redis_client.set(key, data, expire=OAUTH_STATE_TTL_SECONDS)
    if not result:
        logger.warning(f"Failed to store OAuth state in Redis (state={state[:8]}...)")
    return result


async def _get_and_delete_oauth_state(state: str) -> dict | None:
    """
    Retrieve and delete OAuth state from Redis (one-time use).
    Returns None if state doesn't exist or is expired.
    """
    key = f"{OAUTH_STATE_KEY_PREFIX}{state}"
    data = await redis_client.get(key)
    if data:
        # Delete after retrieval (one-time use for CSRF protection)
        await redis_client.delete(key)
    return data


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
    state_data = {
        "user_id": current_user.id,
        "environment": environment,
    }

    # Store state in Redis with TTL
    stored = await _store_oauth_state(state, state_data)
    if not stored:
        raise HTTPException(
            status_code=503,
            detail="Unable to initialize OAuth flow. Please try again."
        )

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
    # Validate state to prevent CSRF attacks (one-time use via Redis)
    state_data = await _get_and_delete_oauth_state(state)
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
