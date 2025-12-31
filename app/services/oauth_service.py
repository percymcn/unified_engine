"""
OAuth Integration Service
Supports Google, GitHub, Microsoft OAuth
"""
import httpx
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import User
from app.models.enhanced_models import OAuthAccount, OAuthProvider
from app.routers.auth import get_password_hash

logger = logging.getLogger(__name__)

class OAuthService:
    """OAuth service for handling social logins"""
    
    @staticmethod
    async def get_google_user_info(access_token: str) -> Dict[str, Any]:
        """Get user info from Google"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get Google user info: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to verify Google token"
                )
    
    @staticmethod
    async def get_github_user_info(access_token: str) -> Dict[str, Any]:
        """Get user info from GitHub"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                user_data = response.json()
                
                # Get email if not public
                email = user_data.get("email")
                if not email:
                    email_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        email = next((e["email"] for e in emails if e.get("primary")), None)
                        if not email and emails:
                            email = emails[0]["email"]
                
                return {
                    "id": str(user_data["id"]),
                    "email": email,
                    "name": user_data.get("name") or user_data.get("login"),
                    "avatar_url": user_data.get("avatar_url"),
                    "login": user_data.get("login"),
                }
            except Exception as e:
                logger.error(f"Failed to get GitHub user info: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to verify GitHub token"
                )
    
    @staticmethod
    async def get_microsoft_user_info(access_token: str) -> Dict[str, Any]:
        """Get user info from Microsoft"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get Microsoft user info: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to verify Microsoft token"
                )
    
    @staticmethod
    async def authenticate_oauth(
        provider: OAuthProvider,
        access_token: str,
        db: Session
    ) -> User:
        """Authenticate user via OAuth provider"""
        # Get user info from provider
        if provider == OAuthProvider.GOOGLE:
            user_info = await OAuthService.get_google_user_info(access_token)
            provider_user_id = user_info["id"]
            email = user_info["email"]
            name = user_info.get("name", "")
            avatar_url = user_info.get("picture")
        elif provider == OAuthProvider.GITHUB:
            user_info = await OAuthService.get_github_user_info(access_token)
            provider_user_id = user_info["id"]
            email = user_info["email"]
            name = user_info.get("name", user_info.get("login", ""))
            avatar_url = user_info.get("avatar_url")
        elif provider == OAuthProvider.MICROSOFT:
            user_info = await OAuthService.get_microsoft_user_info(access_token)
            provider_user_id = user_info["id"]
            email = user_info.get("mail") or user_info.get("userPrincipalName")
            name = user_info.get("displayName", "")
            avatar_url = None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}"
            )
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by OAuth provider"
            )
        
        # Check if OAuth account exists
        oauth_account = db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        ).first()
        
        if oauth_account:
            # Update OAuth account
            oauth_account.access_token = access_token  # Should be encrypted in production
            oauth_account.provider_email = email
            oauth_account.provider_data = user_info
            db.commit()
            return oauth_account.user
        
        # Check if user exists by email
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Link OAuth account to existing user
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=email,
                access_token=access_token,  # Should be encrypted
                provider_data=user_info
            )
            db.add(oauth_account)
            db.commit()
            return user
        
        # Create new user
        username = email.split("@")[0]
        # Ensure username is unique
        base_username = username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            email=email,
            username=username,
            full_name=name,
            avatar_url=avatar_url,
            is_verified=True,  # OAuth providers verify emails
            oauth_provider=provider.value,
            oauth_id=provider_user_id,
            role="free_user"
        )
        db.add(user)
        db.flush()
        
        # Create OAuth account
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            access_token=access_token,  # Should be encrypted
            provider_data=user_info
        )
        db.add(oauth_account)
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def get_oauth_authorization_url(provider: OAuthProvider) -> str:
        """Get OAuth authorization URL for provider"""
        if provider == OAuthProvider.GOOGLE:
            client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
            redirect_uri = f"{settings.CORS_ORIGINS[0]}/auth/google/callback"
            return (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope=openid email profile"
            )
        elif provider == OAuthProvider.GITHUB:
            client_id = getattr(settings, "GITHUB_CLIENT_ID", "")
            redirect_uri = f"{settings.CORS_ORIGINS[0]}/auth/github/callback"
            return (
                f"https://github.com/login/oauth/authorize?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"scope=user:email"
            )
        elif provider == OAuthProvider.MICROSOFT:
            client_id = getattr(settings, "MICROSOFT_CLIENT_ID", "")
            redirect_uri = f"{settings.CORS_ORIGINS[0]}/auth/microsoft/callback"
            return (
                f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope=openid email profile"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}"
            )

oauth_service = OAuthService()
