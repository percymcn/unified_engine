"""Broker connection checks that accept both bool flags and methods."""

import inspect
from datetime import datetime
from typing import Any, Dict, Mapping


def broker_is_connected(broker: Any) -> bool:
    """
    Return whether a broker adapter or executor is connected.

    Executors sometimes store a bool on ``is_connected`` and sometimes expose
    a method with the same name. A bound method must not count as connected.
    Async methods are not awaited here; ``_connected_flag`` or ``_is_connected``
    is used instead so a health check cannot block on the broker network.
    """
    if broker is None:
        return False

    flag = getattr(broker, "_connected_flag", None)
    if isinstance(flag, bool) and flag:
        return True

    attr = getattr(broker, "is_connected", None)
    try:
        if isinstance(attr, bool):
            return attr
        if callable(attr):
            result = attr()
            if inspect.isawaitable(result):
                result.close()
                inner = getattr(broker, "_is_connected", None)
                return bool(inner) if isinstance(inner, bool) else False
            return bool(result)
    except Exception:
        return False

    inner = getattr(broker, "_is_connected", None)
    if isinstance(inner, bool):
        return inner
    return False


def build_unified_health(
    brokers: Mapping[str, Any],
    version: str = "2.0.0",
) -> Dict[str, Any]:
    """
    Build a process-up health payload.

    Disconnected brokers produce status ``degraded`` and HTTP callers should
    return 200. This payload never raises because a broker is offline.
    """
    broker_status: Dict[str, Dict[str, Any]] = {}
    for name, broker in brokers.items():
        connected = broker_is_connected(broker)
        broker_status[name] = {
            "connected": connected,
            "status": "healthy" if connected else "disconnected",
        }

    if brokers and all(item["connected"] for item in broker_status.values()):
        status = "healthy"
    else:
        status = "degraded"

    now = datetime.utcnow().isoformat()
    return {
        "status": status,
        "timestamp": now,
        "version": version,
        "services": {
            "api": "up",
            "brokers": status,
        },
        "brokers": broker_status,
        "uptime": now,
    }
