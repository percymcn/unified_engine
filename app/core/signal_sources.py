"""Map inbound webhook source labels onto the persisted SignalSource enum."""

from typing import Any, Mapping, Optional

from app.domain.enums import SignalSource

_TRAILHACKER_KEYS = {
    "trailhacker",
    "trail_hacker",
    "trailhacker_webhook",
    "th",
}


def resolve_signal_source(raw: Optional[str]) -> SignalSource:
    """
    Resolve a webhook source label to a SignalSource value that exists in the database enum.

    TrailHacker aliases map to TRAILHACKER. The label "custom" is stored as API,
    which is a valid enum member. Unknown labels fall back to TRADINGVIEW.
    """
    if raw is None:
        return SignalSource.TRADINGVIEW

    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        return SignalSource.TRADINGVIEW

    if key in _TRAILHACKER_KEYS or "trailhacker" in key:
        return SignalSource.TRAILHACKER
    if key in {"custom", "api"}:
        return SignalSource.API
    if key == "manual":
        return SignalSource.MANUAL
    if key in {"tradingview", "tv"}:
        return SignalSource.TRADINGVIEW

    try:
        return SignalSource(key)
    except ValueError:
        return SignalSource.TRADINGVIEW


def is_empty_trailhacker_payload(payload: Optional[Mapping[str, Any]]) -> bool:
    """True when a TrailHacker body has no symbol and no action to execute."""
    if not payload:
        return True

    symbol = str(payload.get("symbol") or payload.get("ticker") or "").strip()
    action = str(payload.get("signal") or payload.get("action") or "").strip()
    if not symbol or symbol.upper() == "UNKNOWN":
        return True
    if not action:
        return True
    return False
