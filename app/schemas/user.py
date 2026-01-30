"""
User Profile Schemas

Pydantic schemas for user profile management including profile updates and password changes.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class ProfileResponse(BaseModel):
    """User profile response schema."""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    subscription_tier: str = "free"
    primary_webhook_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    """User profile update schema - all fields optional for partial updates."""
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = Field(None, max_length=500)


class PasswordChange(BaseModel):
    """Password change request schema with validation."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate confirm_password matches new_password."""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v

    @field_validator('new_password')
    @classmethod
    def not_same_as_current(cls, v: str, info) -> str:
        """Validate new password is different from current."""
        if 'current_password' in info.data and v == info.data['current_password']:
            raise ValueError('New password must be different from current password')
        return v


class PasswordChangeResponse(BaseModel):
    """Password change response schema."""
    success: bool
    message: str
