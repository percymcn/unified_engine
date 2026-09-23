"""Premarket scan math from caller-supplied symbols.

No market-data provider is configured in this repository. When the request
does not include symbols, the scan returns an empty result instead of
inventing prices or failing the request.
"""

from typing import Any, Dict, List, Mapping, Optional, Sequence

_NO_PROVIDER = "No symbols supplied and no market data provider is configured."
_DEFAULT_MAX_FLOAT = 20_000_000.0


def _symbols(body: Optional[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    if not isinstance(body, Mapping):
        return []
    raw = body.get("symbols") or body.get("tickers") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _empty(action: str) -> Dict[str, Any]:
    return {
        "results": [],
        "status": "ok",
        "action": action,
        "message": _NO_PROVIDER,
    }


def gap_percent(previous_close: float, open_price: float) -> Optional[float]:
    if previous_close == 0:
        return None
    return ((open_price - previous_close) / previous_close) * 100.0


def run_gap_analyze(body: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = _symbols(body)
    if not rows:
        return _empty("gap-analyze")

    results = []
    for row in rows:
        previous = row.get("previous_close")
        opened = row.get("open_price", row.get("open"))
        if previous is None or opened is None:
            continue
        try:
            previous_close = float(previous)
            open_price = float(opened)
        except (TypeError, ValueError):
            continue
        percent = gap_percent(previous_close, open_price)
        if percent is None:
            continue
        results.append(
            {
                "symbol": row.get("symbol"),
                "previous_close": previous_close,
                "open_price": open_price,
                "gap_percent": percent,
            }
        )
    return {"results": results, "status": "ok", "action": "gap-analyze", "message": None}


def run_low_float_scan(body: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = _symbols(body)
    if not rows:
        return _empty("low-float")

    max_float = _DEFAULT_MAX_FLOAT
    if isinstance(body, Mapping) and body.get("max_float") is not None:
        try:
            max_float = float(body["max_float"])
        except (TypeError, ValueError):
            max_float = _DEFAULT_MAX_FLOAT

    results = []
    for row in rows:
        shares = row.get("float_shares", row.get("float"))
        if shares is None:
            continue
        try:
            float_shares = float(shares)
        except (TypeError, ValueError):
            continue
        if float_shares <= max_float:
            results.append({"symbol": row.get("symbol"), "float_shares": float_shares})
    return {"results": results, "status": "ok", "action": "low-float", "message": None}


def run_premarket_generate(body: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Combine gap and low-float flags for symbols the caller already supplied."""
    rows = _symbols(body)
    if not rows:
        return _empty("premarket-generate")

    gaps = {item["symbol"]: item for item in run_gap_analyze(body)["results"]}
    floats = {item["symbol"]: item for item in run_low_float_scan(body)["results"]}
    symbols: List[Any] = []
    for row in rows:
        symbol = row.get("symbol")
        if symbol is None or symbol in symbols:
            continue
        symbols.append(symbol)

    results = []
    for symbol in symbols:
        gap = gaps.get(symbol)
        low_float = floats.get(symbol)
        if gap is None and low_float is None:
            continue
        results.append(
            {
                "symbol": symbol,
                "gap_percent": None if gap is None else gap["gap_percent"],
                "float_shares": None if low_float is None else low_float["float_shares"],
                "low_float": low_float is not None,
            }
        )
    return {"results": results, "status": "ok", "action": "premarket-generate", "message": None}


def run_market_scan(action: str, body: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    normalized = (action or "").strip().lower().strip("/")
    if normalized in {"premarket/generate", "premarket-generate", "generate"}:
        return run_premarket_generate(body)
    if normalized in {"gap-analyze", "gap_analyze", "gap"}:
        return run_gap_analyze(body)
    if normalized in {"low-float", "low_float", "low-float-scan"}:
        return run_low_float_scan(body)
    return {
        "results": [],
        "status": "ok",
        "action": normalized,
        "message": f"Unknown scan action '{normalized}'. {_NO_PROVIDER}",
    }
