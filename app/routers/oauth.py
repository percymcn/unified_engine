"""
OAuth Authentication Router
Handles OAuth login flows for Google, GitHub, Microsoft
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.models.enhanced_models import OAuthProvider
from app.services.oauth_service import oauth_service
from app.routers.auth import create_access_token, get_current_user
from app.models.models import User
from app.core.config import settings

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])

@router.get("/providers")
async def get_oauth_providers():
    """Get available OAuth providers"""
    providers = []
    
    if hasattr(settings, "GOOGLE_CLIENT_ID") and settings.GOOGLE_CLIENT_ID:
        providers.append({
            "provider": "google",
            "name": "Google",
            "auth_url": oauth_service.get_oauth_authorization_url(OAuthProvider.GOOGLE)
        })
    
    if hasattr(settings, "GITHUB_CLIENT_ID") and settings.GITHUB_CLIENT_ID:
        providers.append({
            "provider": "github",
            "name": "GitHub",
            "auth_url": oauth_service.get_oauth_authorization_url(OAuthProvider.GITHUB)
        })
    
    if hasattr(settings, "MICROSOFT_CLIENT_ID") and settings.MICROSOFT_CLIENT_ID:
        providers.append({
            "provider": "microsoft",
            "name": "Microsoft",
            "auth_url": oauth_service.get_oauth_authorization_url(OAuthProvider.MICROSOFT)
        })
    
    return {"providers": providers}

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
            "role": user.role,
            "subscription_tier": user.subscription_tier.value if user.subscription_tier else "free"
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
