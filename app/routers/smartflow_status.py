"""SmartFlow status that stays in paper mode.

Live trading stays off. These routes exist so the dashboard can authenticate
and read status without the Mini-only trader stack or broker credentials.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from app.models.models import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/smartflow", tags=["smartflow"])

_PAPER_STATUS = {
    "authenticated": True,
    "running": False,
    "paused": True,
    "paper_mode": True,
    "kill_switch": True,
    "live_trading_enabled": False,
    "message": "Live trading is not enabled. SmartFlow trader is paused in paper mode.",
}


@router.get("/trader/status")
async def trader_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Authenticated paper-mode trader status."""
    return {
        **_PAPER_STATUS,
        "user_id": current_user.id,
        "strategies": [],
    }


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def smartflow_paused(
    path: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Any other SmartFlow action stays paused and does not place an order."""
    return {
        **_PAPER_STATUS,
        "user_id": current_user.id,
        "path": path,
        "method": request.method,
    }
