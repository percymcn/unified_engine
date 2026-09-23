"""Local full-analysis payload when no market-data or model provider is configured."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

ANALYSIS_TYPES: Sequence[str] = (
    "technical",
    "dcf_valuation",
    "risk",
    "earnings",
    "patterns",
    "macro",
    "competitive",
)


def build_full_analysis(ticker: Optional[str], analyses: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """
    Return a composite analysis the AI Strategy page can render.

    Recommendations stay neutral with confidence 0. This does not invent a
    buy or sell when no market-data feed is configured.
    """
    symbol = (ticker or "").strip().upper() or "UNKNOWN"
    requested: List[str] = [name for name in (analyses or ANALYSIS_TYPES) if name]
    if not requested:
        requested = list(ANALYSIS_TYPES)

    now = datetime.utcnow().isoformat()
    summary = (
        f"No market-data feed is configured for {symbol}. "
        "This analysis is informational only and does not produce a directional call."
    )
    results: Dict[str, Any] = {}
    for name in requested:
        results[name] = {
            "analysis_type": name,
            "ticker": symbol,
            "timestamp": now,
            "recommendation": "neutral",
            "confidence": 0,
            "summary": summary,
            "data": {"market_data": "unavailable", "directional_call": False},
            "from_cache": False,
            "processing_time_ms": 0,
        }

    return {
        "ticker": symbol,
        "analyses": results,
        "composite": {
            "composite_recommendation": "neutral",
            "composite_confidence": 0,
            "agreement_level": "none",
            "signal_strength": 0,
            "individual_scores": {name: 0 for name in requested},
        },
        "timestamp": now,
        "message": summary,
    }
