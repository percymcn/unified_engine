"""Honest payloads for the operations summary endpoints."""

from datetime import datetime
from typing import Any, Dict, Iterable, Optional


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_errors_payload(rows: Iterable[Any]) -> Dict[str, Any]:
    """Recent webhook errors. Empty when nothing has failed."""
    errors = []
    for row in rows:
        message = getattr(row, "error_message", None)
        if not message:
            continue
        errors.append(
            {
                "timestamp": _iso(getattr(row, "created_at", None)),
                "level": "error",
                "message": message,
                "component": getattr(row, "source", None) or "webhooks",
            }
        )
    return {
        "errors": errors,
        "total_count": len(errors),
        "critical_count": 0,
        "source": "webhook_logs",
    }


def empty_errors_payload() -> Dict[str, Any]:
    payload = build_errors_payload([])
    payload["source"] = "unavailable"
    return payload


def build_api_keys_payload(rows: Iterable[Any]) -> Dict[str, Any]:
    """API key status without secret material."""
    keys = []
    for row in rows:
        active = bool(getattr(row, "is_active", False))
        keys.append(
            {
                "id": getattr(row, "id", None),
                "name": getattr(row, "name", None),
                "is_active": active,
                "status": "active" if active else "inactive",
                "last_used_at": _iso(getattr(row, "last_used_at", None)),
                "expires_at": _iso(getattr(row, "expires_at", None)),
            }
        )
    return {"api_keys": keys, "total": len(keys), "source": "api_keys"}


def empty_api_keys_payload() -> Dict[str, Any]:
    payload = build_api_keys_payload([])
    payload["source"] = "unavailable"
    return payload


def build_daily_summary(trades: Iterable[Any], day: Optional[str] = None) -> Dict[str, Any]:
    """Daily P&L from stored trades. Zeros when the day has no trades."""
    profits = []
    for trade in trades:
        profit = getattr(trade, "profit", None)
        if profit is None:
            continue
        try:
            profits.append(float(profit))
        except (TypeError, ValueError):
            continue

    wins = [profit for profit in profits if profit > 0]
    losses = [profit for profit in profits if profit < 0]
    total = len(profits)
    return {
        "date": day or datetime.utcnow().strftime("%Y-%m-%d"),
        "summary": {
            "total_trades": total,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": (len(wins) / total) if total else 0,
            "total_pnl": sum(profits),
            "best_trade": max(profits) if profits else 0,
            "worst_trade": min(profits) if profits else 0,
        },
        "brokers": {},
        "source": "trades",
    }


def empty_daily_summary(day: Optional[str] = None) -> Dict[str, Any]:
    payload = build_daily_summary([], day)
    payload["source"] = "unavailable"
    return payload
