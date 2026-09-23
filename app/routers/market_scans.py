"""Premarket scan endpoints.

Live scanner pages that call a different path than these routes are still
blocked until that Mini-only UI is in this repository. These routes stop
the known generate / gap / low-float actions from 404 or 500 when the UI
posts symbols, and they return an empty result when no provider is configured.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.models import User
from app.routers.auth import get_current_user
from app.services.market_scans import run_market_scan

router = APIRouter(prefix="/api/v1/market-scans", tags=["market-scans"])


class MarketScanRequest(BaseModel):
    symbols: Optional[list] = None
    tickers: Optional[list] = None
    max_float: Optional[float] = None

    class Config:
        extra = "allow"


def _run(action: str, body: Optional[MarketScanRequest]) -> Dict[str, Any]:
    if body is None:
        payload: Dict[str, Any] = {}
    elif hasattr(body, "model_dump"):
        payload = body.model_dump()
    else:
        payload = body.dict()
    return run_market_scan(action, payload)


@router.post("/premarket/generate")
async def premarket_generate(
    body: Optional[MarketScanRequest] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate a premarket list from symbols included in the request."""
    return _run("premarket/generate", body)


@router.post("/gap-analyze")
async def gap_analyze(
    body: Optional[MarketScanRequest] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compute gap percent for symbols that include previous close and open."""
    return _run("gap-analyze", body)


@router.post("/low-float")
async def low_float_scan(
    body: Optional[MarketScanRequest] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Filter supplied symbols by float shares."""
    return _run("low-float", body)
