"""
Circuit Breaker Health Monitoring Endpoint
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.services.broker_resilience import get_circuit_breaker_health, broker_circuit_breakers
from app.core.auth import get_current_user
from app.models.database import User

router = APIRouter()


@router.get("/circuit-breakers/health", tags=["monitoring"])
async def get_circuit_breaker_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get circuit breaker health status for all brokers

    Returns detailed information about circuit breaker states,
    failure counts, and overall system health.
    """
    return get_circuit_breaker_health()


@router.post("/circuit-breakers/reset", tags=["monitoring"])
async def reset_circuit_breakers(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Manually reset all circuit breakers

    Use this to force retry connections to brokers after
    fixing external issues.
    """
    broker_circuit_breakers.reset_all()
    return {
        "status": "success",
        "message": "All circuit breakers have been reset"
    }


@router.post("/circuit-breakers/{broker}/reset", tags=["monitoring"])
async def reset_broker_circuit_breaker(
    broker: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Manually reset circuit breaker for specific broker

    Args:
        broker: Broker name (mt4, mt5, tradelocker, tradovate, projectx)
    """
    breaker = broker_circuit_breakers.get_breaker(broker)

    if breaker is None:
        return {
            "status": "error",
            "message": f"Circuit breaker not found for broker: {broker}"
        }

    breaker.reset()
    return {
        "status": "success",
        "message": f"Circuit breaker for {broker} has been reset"
    }
