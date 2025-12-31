"""
API Key Management Router
Handles API key generation, validation, and revocation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
import hashlib
from passlib.context import CryptContext

from app.db.database import get_db
from app.models.models import ApiKey, User
from app.models.schemas import APIResponse
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api-keys", tags=["api-keys"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ue_{secrets.token_urlsafe(32)}"

@router.get("/", response_model=List[dict])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all API keys for current user"""
    api_keys = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.id
    ).all()
    
    return [
        {
            "id": key.id,
            "name": key.name,
            "is_active": key.is_active,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "created_at": key.created_at.isoformat(),
            "permissions": key.permissions
        }
        for key in api_keys
    ]

@router.post("/", response_model=dict)
async def create_api_key(
    name: str,
    expires_days: Optional[int] = None,
    permissions: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key"""
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Calculate expiration
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    # Create database record
    db_api_key = ApiKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=name,
        permissions=permissions or ["read", "write"],
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    # Return the key only once (it won't be shown again)
    return {
        "id": db_api_key.id,
        "name": db_api_key.name,
        "api_key": api_key,  # Only returned on creation
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": db_api_key.created_at.isoformat()
    }

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}

@router.get("/{key_id}")
async def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get API key details (without the actual key)"""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "created_at": api_key.created_at.isoformat(),
        "permissions": api_key.permissions
    }

async def verify_api_key_from_db(api_key: str, db: Session) -> Optional[User]:
    """Verify API key against database"""
    if not api_key:
        return None
    
    key_hash = hash_api_key(api_key)
    
    db_api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True
    ).first()
    
    if not db_api_key:
        return None
    
    # Check expiration
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        return None
    
    # Update last used
    db_api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    # Return user
    return db.query(User).filter(User.id == db_api_key.user_id).first()
