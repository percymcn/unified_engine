"""
Shadow-only compatibility cache for recent positions.

Enabled by COMPAT_POSITIONS_CACHE=1 to help short-lived consistency in shadow runs.
"""
from __future__ import annotations

import os
import time
from typing import Dict, List, Any


_ENABLED = os.getenv("COMPAT_POSITIONS_CACHE", "").lower() in ("1", "true", "yes")
_TTL_SECONDS = int(os.getenv("COMPAT_POSITIONS_TTL_SECONDS", "30"))
_POSITIONS: Dict[int, Dict[str, Dict[str, Any]]] = {}


def is_enabled() -> bool:
    return _ENABLED


def record_open(account_id: int, position: Dict[str, Any]) -> None:
    if not _ENABLED or not account_id:
        return
    pos_id = str(position.get("id") or "")
    if not pos_id:
        return
    payload = dict(position)
    payload["_ts"] = time.time()
    _POSITIONS.setdefault(account_id, {})[pos_id] = payload


def record_close(account_id: int, position_id: str | None = None, symbol: str | None = None) -> None:
    if not _ENABLED or not account_id:
        return
    account_cache = _POSITIONS.get(account_id)
    if not account_cache:
        return
    if position_id and position_id in account_cache:
        account_cache.pop(position_id, None)
        return
    if symbol:
        for pid, pos in list(account_cache.items()):
            if str(pos.get("symbol", "")).upper() == symbol.upper():
                account_cache.pop(pid, None)


def get_positions(account_id: int) -> List[Dict[str, Any]]:
    if not _ENABLED or not account_id:
        return []
    account_cache = _POSITIONS.get(account_id, {})
    now = time.time()
    positions: List[Dict[str, Any]] = []
    for pid, pos in list(account_cache.items()):
        ts = pos.get("_ts", 0)
        if now - ts > _TTL_SECONDS:
            account_cache.pop(pid, None)
            continue
        cleaned = dict(pos)
        cleaned.pop("_ts", None)
        positions.append(cleaned)
    if not account_cache:
        _POSITIONS.pop(account_id, None)
    return positions
