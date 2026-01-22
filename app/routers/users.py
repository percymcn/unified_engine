"""
User preferences API endpoints.

Provides endpoints for managing user timezone and notification preferences.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pytz

from app.db.database import get_db
from app.models.models import User
from app.models.schemas import PreferencesResponse, PreferencesUpdate, NotificationPreferences
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("/me/preferences", response_model=PreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's preferences (timezone and notifications).
    """
    # Build notification preferences from stored JSON or defaults
    notification_prefs = current_user.notification_preferences or {
        "trade_alerts": True,
        "error_notifications": True,
        "daily_summary": False,
        "email_notifications": True
    }

    return PreferencesResponse(
        timezone=current_user.timezone or "UTC",
        notification_preferences=NotificationPreferences(**notification_prefs)
    )


@router.put("/me/preferences", response_model=PreferencesResponse)
async def update_preferences(
    preferences: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user preferences (timezone and/or notifications).

    Supports partial updates - only fields provided will be updated.
    Validates timezone against pytz.all_timezones list.
    """
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

    db.commit()
    db.refresh(current_user)

    # Return updated preferences
    notification_prefs = current_user.notification_preferences or {
        "trade_alerts": True,
        "error_notifications": True,
        "daily_summary": False,
        "email_notifications": True
    }

    return PreferencesResponse(
        timezone=current_user.timezone or "UTC",
        notification_preferences=NotificationPreferences(**notification_prefs)
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
