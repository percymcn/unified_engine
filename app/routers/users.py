"""
User profile and preferences API endpoints.

Provides endpoints for managing user profile, password changes,
timezone and notification preferences.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pytz

from app.db.database import get_db
from app.models.models import User
from app.models.database_models import WebhookConfig
from app.models.schemas import PreferencesResponse, PreferencesUpdate, NotificationPreferences, DeduplicationSettings
from app.schemas.user import ProfileResponse, ProfileUpdate, PasswordChange, PasswordChangeResponse
from app.routers.auth import get_current_user, verify_password, get_password_hash, get_user_by_email

router = APIRouter()


# =============================================================================
# Profile Endpoints
# =============================================================================

@router.get("/me/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's profile information.
    """
    webhook_config = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id,
        WebhookConfig.is_active == True
    ).order_by(WebhookConfig.updated_at.desc()).first()

    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=getattr(current_user, 'avatar_url', None),
        primary_webhook_key=webhook_config.webhook_key if webhook_config else None,
        created_at=current_user.created_at,
    )


@router.put("/me/profile", response_model=ProfileResponse)
async def update_profile(
    profile: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.

    Supports partial updates - only fields provided will be updated.
    Email changes require uniqueness validation.
    """
    # Check email uniqueness if being updated
    if profile.email is not None and profile.email != current_user.email:
        existing_user = get_user_by_email(db, profile.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = profile.email

    # Update other fields if provided
    if profile.full_name is not None:
        current_user.full_name = profile.full_name

    if profile.avatar_url is not None:
        current_user.avatar_url = profile.avatar_url

    db.commit()
    db.refresh(current_user)

    webhook_config = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id,
        WebhookConfig.is_active == True
    ).order_by(WebhookConfig.updated_at.desc()).first()

    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=getattr(current_user, 'avatar_url', None),
        primary_webhook_key=webhook_config.webhook_key if webhook_config else None,
        created_at=current_user.created_at,
    )


@router.post("/me/password", response_model=PasswordChangeResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.

    Requires current password verification before allowing password change.
    New password must be different from current password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Verify new password is different from current
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Verify passwords match
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return PasswordChangeResponse(
        success=True,
        message="Password changed successfully"
    )


# =============================================================================
# Preferences Endpoints
# =============================================================================


@router.get("/me/preferences", response_model=PreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's preferences (timezone, notifications, and deduplication).
    """
    # Build notification preferences from stored JSON or defaults
    notification_prefs = current_user.notification_preferences or {
        "trade_alerts": True,
        "error_notifications": True,
        "daily_summary": False,
        "email_notifications": True
    }

    # Build deduplication settings
    dedup_settings = DeduplicationSettings(
        enable_deduplication=getattr(current_user, 'enable_deduplication', True) if hasattr(current_user, 'enable_deduplication') else True,
        deduplication_scope=getattr(current_user, 'deduplication_scope', 'per_account') or 'per_account'
    )

    return PreferencesResponse(
        timezone=current_user.timezone or "UTC",
        notification_preferences=NotificationPreferences(**notification_prefs),
        deduplication=dedup_settings
    )


@router.put("/me/preferences", response_model=PreferencesResponse)
async def update_preferences(
    preferences: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user preferences (timezone, notifications, and/or deduplication).

    Supports partial updates - only fields provided will be updated.
    Validates timezone against pytz.all_timezones list.
    Validates deduplication_scope against allowed values.
    """
    # Update theme if provided (Patch 1.2.1)
    if preferences.theme is not None:
        valid_themes = ['system', 'dark', 'light']
        if preferences.theme not in valid_themes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid theme: '{preferences.theme}'. Must be one of: {valid_themes}"
            )
        current_user.theme = preferences.theme

    # Validate timezone if provided
    if preferences.timezone is not None:
        if preferences.timezone not in pytz.all_timezones:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timezone: '{preferences.timezone}'. Must be a valid IANA timezone."
            )
        current_user.timezone = preferences.timezone

    # Update notification preferences if provided
    if preferences.notification_preferences is not None:
        # Merge with existing preferences
        existing_prefs = current_user.notification_preferences or {
            "trade_alerts": True,
            "error_notifications": True,
            "daily_summary": False,
            "email_notifications": True
        }
        # Update with new values
        existing_prefs.update(preferences.notification_preferences.model_dump())
        current_user.notification_preferences = existing_prefs

    # Update deduplication settings if provided
    if preferences.deduplication is not None:
        # Validate deduplication scope
        valid_scopes = ['per_account', 'global']
        if preferences.deduplication.deduplication_scope not in valid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid deduplication_scope: '{preferences.deduplication.deduplication_scope}'. Must be one of: {valid_scopes}"
            )
        current_user.enable_deduplication = preferences.deduplication.enable_deduplication
        current_user.deduplication_scope = preferences.deduplication.deduplication_scope

    db.commit()
    db.refresh(current_user)

    # Return updated preferences
    notification_prefs = current_user.notification_preferences or {
        "trade_alerts": True,
        "error_notifications": True,
        "daily_summary": False,
        "email_notifications": True
    }

    dedup_settings = DeduplicationSettings(
        enable_deduplication=getattr(current_user, 'enable_deduplication', True) if hasattr(current_user, 'enable_deduplication') else True,
        deduplication_scope=getattr(current_user, 'deduplication_scope', 'per_account') or 'per_account'
    )

    return PreferencesResponse(
        timezone=current_user.timezone or "UTC",
        theme=getattr(current_user, 'theme', 'system') or 'system',  # Patch 1.2.1
        notification_preferences=NotificationPreferences(**notification_prefs),
        deduplication=dedup_settings
    )


@router.get("/timezones")
async def get_timezones():
    """
    Get list of common timezones for dropdown selection.

    Returns a curated list of common timezones grouped by region.
    """
    common_timezones = [
        # Americas
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Phoenix",
        "America/Toronto",
        "America/Vancouver",
        "America/Mexico_City",
        "America/Sao_Paulo",
        "America/Buenos_Aires",
        # Europe
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Amsterdam",
        "Europe/Madrid",
        "Europe/Rome",
        "Europe/Zurich",
        "Europe/Stockholm",
        "Europe/Moscow",
        # Asia
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Asia/Hong_Kong",
        "Asia/Singapore",
        "Asia/Seoul",
        "Asia/Dubai",
        "Asia/Kolkata",
        "Asia/Bangkok",
        # Pacific
        "Pacific/Sydney",
        "Pacific/Auckland",
        "Pacific/Honolulu",
        # UTC
        "UTC",
    ]

    return {"timezones": common_timezones}
