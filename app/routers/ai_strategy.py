"""AI Strategy analysis endpoint that always returns a renderable composite."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.models import User
from app.routers.auth import get_current_user
from app.services.ai_analysis import build_full_analysis

router = APIRouter(prefix="/api/v1/ai-strategy", tags=["ai-strategy"])


class FullAnalysisRequest(BaseModel):
    ticker: Optional[str] = None
    analyses: Optional[List[str]] = None


@router.post("/full-analysis")
async def full_analysis(
    body: FullAnalysisRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Run a full analysis for the AI Strategy page.

    Without a market-data feed the result is an explicit neutral composite
    so the page has output. It does not emit a trade signal.
    """
    return build_full_analysis(body.ticker, body.analyses)
