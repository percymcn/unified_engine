"""
OAuth Authentication Router
Handles OAuth login flows for Google, GitHub, Microsoft
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db.database import get_db
from app.models.enhanced_models import OAuthProvider
from app.services.oauth_service import oauth_service
from app.routers.auth import create_access_token, get_current_user
from app.models.models import User
from app.core.config import settings
from app.core.oauth_state import generate_oauth_state, validate_oauth_state_permissive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])

@router.get("/providers")
async def get_oauth_providers():
    """Get available OAuth providers with CSRF-protected auth URLs"""
    providers = []

    # Generate a unique state token for CSRF protection
    state = await generate_oauth_state()

    if hasattr(settings, "GOOGLE_CLIENT_ID") and settings.GOOGLE_CLIENT_ID:
        providers.append({
            "provider": "google",
            "name": "Google",
            "auth_url": oauth_service.get_oauth_authorization_url(OAuthProvider.GOOGLE, state=state)
        })

    if hasattr(settings, "GITHUB_CLIENT_ID") and settings.GITHUB_CLIENT_ID:
        providers.append({
            "provider": "github",
            "name": "GitHub",
            "auth_url": oauth_service.get_oauth_authorization_url(OAuthProvider.GITHUB, state=state)
        })

    if hasattr(settings, "MICROSOFT_CLIENT_ID") and settings.MICROSOFT_CLIENT_ID:
        providers.append({
            "provider": "microsoft",
            "name": "Microsoft",
            "auth_url": oauth_service.get_oauth_authorization_url(OAuthProvider.MICROSOFT, state=state)
        })

    return {"providers": providers, "state": state}

@router.get("/callback/google")
async def google_oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: Optional[str] = Query(None, description="OAuth state parameter"),
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    Exchanges authorization code for access token and creates/updates user session.
    """
    import httpx

    # Validate state parameter to prevent CSRF attacks
    # Using permissive mode for backwards compatibility with existing flows
    state_valid = await validate_oauth_state_permissive(state)
    if not state_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter - possible CSRF attack"
        )

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )
    
    redirect_uri = settings.GOOGLE_REDIRECT_URI or "https://mytradeflow.app/api/auth/google/callback"
    
    # Exchange authorization code for access token
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data["access_token"]
    except httpx.HTTPStatusError as e:
        response_text = e.response.text if e.response is not None else "no response"
        status_code = e.response.status_code if e.response is not None else "unknown"
        # Mask sensitive info in logs
        client_id_masked = f"{settings.GOOGLE_CLIENT_ID[:8]}..." if settings.GOOGLE_CLIENT_ID else "NOT_SET"
        logger.error(
            "Google OAuth token exchange failed: status=%s response=%s client_id=%s code_len=%s redirect_uri=%s",
            status_code,
            response_text[:500],  # Truncate long responses
            client_id_masked,
            len(code) if code else 0,
            redirect_uri,
        )
        # Return more helpful error message
        error_detail = "Google OAuth token exchange failed"
        if "redirect_uri_mismatch" in response_text.lower():
            error_detail = "OAuth redirect URI mismatch - check Google Console configuration"
        elif "invalid_grant" in response_text.lower():
            error_detail = "OAuth code expired or already used - please try again"
        elif "invalid_client" in response_text.lower():
            error_detail = "OAuth client configuration error"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail
        )
    except Exception as e:
        client_id_masked = f"{settings.GOOGLE_CLIENT_ID[:8]}..." if settings.GOOGLE_CLIENT_ID else "NOT_SET"
        logger.error(
            "Google OAuth token exchange failed: error=%s type=%s client_id=%s code_len=%s redirect_uri=%s",
            str(e),
            type(e).__name__,
            client_id_masked,
            len(code) if code else 0,
            redirect_uri,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth token exchange failed - please try again"
        )
    
    # Authenticate user with Google
    try:
        user = await oauth_service.authenticate_oauth(OAuthProvider.GOOGLE, access_token, db)
    except Exception as e:
        logger.error(f"Google OAuth authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate with Google"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create access token
    from datetime import timedelta
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    subscription_value = (
        user.subscription_tier.value
        if hasattr(user.subscription_tier, "value")
        else (user.subscription_tier or "free")
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "role": getattr(user, "role", None) or "free_user",
            "subscription_tier": subscription_value
        }
    }

@router.post("/login/{provider}")
async def oauth_login(
    provider: str,
    access_token: str = Query(..., description="OAuth access token"),
    db: Session = Depends(get_db)
):
    """Login with OAuth provider"""
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )
    
    # Authenticate user
    user = await oauth_service.authenticate_oauth(oauth_provider, access_token, db)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create access token
    from datetime import timedelta
    from app.core.config import settings
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    subscription_value = (
        user.subscription_tier.value
        if hasattr(user.subscription_tier, "value")
        else (user.subscription_tier or "free")
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "role": getattr(user, "role", None) or "free_user",
            "subscription_tier": subscription_value
        }
    }

@router.get("/accounts")
async def get_oauth_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's connected OAuth accounts"""
    from app.models.enhanced_models import OAuthAccount
    
    accounts = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == current_user.id
    ).all()
    
    return {
        "accounts": [
            {
                "id": acc.id,
                "provider": acc.provider.value,
                "provider_email": acc.provider_email,
                "created_at": acc.created_at.isoformat()
            }
            for acc in accounts
        ]
    }

@router.delete("/accounts/{account_id}")
async def disconnect_oauth_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect an OAuth account"""
    from app.models.enhanced_models import OAuthAccount
    
    account = db.query(OAuthAccount).filter(
        OAuthAccount.id == account_id,
        OAuthAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth account not found"
        )
    
    # Don't allow disconnecting if it's the only auth method
    if not current_user.hashed_password and len(current_user.oauth_accounts) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect last authentication method"
        )
    
    db.delete(account)
    db.commit()
    
    return {"message": "OAuth account disconnected"}
