"""
Trial Router
API endpoints for trial status and information.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import User
from app.routers.auth import get_current_user
from app.services.trial_service import TrialService, TrialStatus

router = APIRouter()


class TrialInfoResponse(BaseModel):
    """Response model for trial information."""
    status: str
    subscription_tier: str
    trades_remaining: Optional[int] = None
    trades_used: Optional[int] = None
    trades_limit: Optional[int] = None
    days_remaining: Optional[int] = None
    hours_remaining: Optional[int] = None
    days_limit: Optional[int] = None
    trial_started_at: Optional[str] = None
    trial_ended_at: Optional[str] = None


@router.get("/status", response_model=TrialInfoResponse)
async def get_trial_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current trial status for authenticated user.

    Returns trial information including:
    - status: not_started, active, expired, or not_applicable (paid user)
    - trades_remaining: How many trades left in trial
    - days_remaining: How many days left in trial
    - trial_started_at: When trial began
    - trial_ended_at: When trial expired (if applicable)
    """
    trial_service = TrialService(db)
    trial_info = trial_service.get_trial_info(current_user)
    return TrialInfoResponse(**trial_info)


@router.post("/start")
async def start_trial(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually start trial for a user.

    Note: Trial is normally auto-started on first signal execution.
    This endpoint allows explicit trial start if needed.
    """
    trial_service = TrialService(db)

    # Check if trial can be started
    if current_user.subscription_tier != "free":
        raise HTTPException(
            status_code=400,
            detail="Trial not available for paid subscribers"
        )

    if current_user.trial_status == "active":
        raise HTTPException(
            status_code=400,
            detail="Trial already active"
        )

    if current_user.trial_status == "expired":
        raise HTTPException(
            status_code=400,
            detail="Trial already expired. Please upgrade to continue trading."
        )

    # Start the trial
    started = trial_service.start_trial(current_user)

    if started:
        return {
            "success": True,
            "message": "Trial started successfully",
            "trial_info": trial_service.get_trial_info(current_user)
        }

    raise HTTPException(
        status_code=400,
        detail="Could not start trial"
    )


@router.get("/check")
async def check_trial_active(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick check if user can execute signals.

    Returns:
    - can_trade: True if user can execute signals
    - reason: Why trading is blocked (if applicable)
    """
    trial_service = TrialService(db)
    status = trial_service.check_trial_status(current_user)

    if status == TrialStatus.NOT_APPLICABLE:
        return {
            "can_trade": True,
            "reason": None,
            "subscription_tier": current_user.subscription_tier
        }

    if status == TrialStatus.NOT_STARTED:
        return {
            "can_trade": True,  # Trial will auto-start on first signal
            "reason": "trial_not_started",
            "subscription_tier": current_user.subscription_tier
        }

    if status == TrialStatus.ACTIVE:
        trial_info = trial_service.get_trial_info(current_user)
        return {
            "can_trade": True,
            "reason": None,
            "subscription_tier": current_user.subscription_tier,
            "trades_remaining": trial_info.get("trades_remaining"),
            "days_remaining": trial_info.get("days_remaining")
        }

    # EXPIRED
    trial_info = trial_service.get_trial_info(current_user)
    return {
        "can_trade": False,
        "reason": "trial_expired",
        "subscription_tier": current_user.subscription_tier,
        "message": "Your free trial has ended. Please upgrade to Pro to continue trading.",
        "trades_used": trial_info.get("trades_used"),
        "trial_ended_at": trial_info.get("trial_ended_at")
    }
