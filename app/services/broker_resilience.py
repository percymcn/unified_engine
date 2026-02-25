"""
Broker Resilience Layer
Adds circuit breakers and resilience patterns to broker API calls
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Dict
from functools import wraps

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenException,
    create_broker_circuit_breaker
)
from app.models.pydantic_schemas import OrderResponse, TradeResponse

logger = logging.getLogger(__name__)


class BrokerCircuitBreakers:
    """
    Manages circuit breakers for all broker executors
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._initialize_breakers()

    def _initialize_breakers(self):
        """Initialize circuit breakers for each broker"""
        brokers = ["mt4", "mt5", "tradelocker", "tradovate", "projectx"]

        for broker in brokers:
            self._breakers[broker] = create_broker_circuit_breaker(broker)

        logger.info(f"Initialized circuit breakers for {len(brokers)} brokers")

    def get_breaker(self, broker: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker for specific broker"""
        return self._breakers.get(broker.lower())

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all circuit breakers"""
        return {
            broker: breaker.get_stats()
            for broker, breaker in self._breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All broker circuit breakers reset")


# Global instance
broker_circuit_breakers = BrokerCircuitBreakers()


def with_circuit_breaker(broker_name: str, fallback_response: Optional[Any] = None):
    """
    Decorator to wrap broker API calls with circuit breaker

    Args:
        broker_name: Name of the broker (mt4, mt5, tradelocker, etc.)
        fallback_response: Response to return when circuit is open

    Usage:
        @with_circuit_breaker("tradelocker")
        async def place_order(self, order: OrderRequest) -> OrderResponse:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = broker_circuit_breakers.get_breaker(broker_name)

            if breaker is None:
                logger.warning(f"No circuit breaker found for {broker_name}")
                return await func(*args, **kwargs)

            try:
                # Execute with circuit breaker protection
                result = await breaker.call_async(func, *args, **kwargs)
                return result

            except CircuitBreakerOpenException as e:
                logger.error(
                    f"{broker_name} circuit breaker OPEN: {e}",
                    extra={"broker": broker_name, "circuit_state": "open"}
                )

                # Return fallback response
                if fallback_response is not None:
                    return fallback_response

                # Return error response based on expected return type
                if hasattr(func, "__annotations__"):
                    return_type = func.__annotations__.get("return")

                    if return_type == OrderResponse or "OrderResponse" in str(return_type):
                        return OrderResponse(
                            success=False,
                            error=f"{broker_name} API temporarily unavailable (circuit breaker open)"
                        )
                    elif return_type == TradeResponse or "TradeResponse" in str(return_type):
                        return TradeResponse(
                            success=False,
                            error=f"{broker_name} API temporarily unavailable (circuit breaker open)"
                        )

                # Generic fallback
                raise

            except Exception as e:
                logger.error(
                    f"{broker_name} API call failed: {e}",
                    extra={"broker": broker_name},
                    exc_info=True
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker = broker_circuit_breakers.get_breaker(broker_name)

            if breaker is None:
                logger.warning(f"No circuit breaker found for {broker_name}")
                return func(*args, **kwargs)

            try:
                result = breaker.call(func, *args, **kwargs)
                return result

            except CircuitBreakerOpenException as e:
                logger.error(f"{broker_name} circuit breaker OPEN: {e}")

                if fallback_response is not None:
                    return fallback_response

                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


async def execute_with_timeout_and_breaker(
    broker_name: str,
    func: Callable,
    *args,
    timeout: float = 30.0,
    **kwargs
) -> Any:
    """
    Execute broker API call with timeout and circuit breaker

    Args:
        broker_name: Name of the broker
        func: Async function to execute
        timeout: Timeout in seconds
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from func

    Raises:
        asyncio.TimeoutError: If call exceeds timeout
        CircuitBreakerOpenException: If circuit is open
    """
    breaker = broker_circuit_breakers.get_breaker(broker_name)

    if breaker is None:
        logger.warning(f"No circuit breaker for {broker_name}, executing without protection")
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"{broker_name} API call timed out after {timeout}s")
            raise

    try:
        # Wrap in timeout
        async def wrapped_call():
            return await func(*args, **kwargs)

        result = await breaker.call_async(
            lambda: asyncio.wait_for(wrapped_call(), timeout=timeout)
        )
        return result

    except asyncio.TimeoutError:
        logger.error(
            f"{broker_name} API call timed out after {timeout}s",
            extra={"broker": broker_name, "timeout": timeout}
        )
        raise

    except CircuitBreakerOpenException:
        logger.error(f"{broker_name} circuit breaker is OPEN")
        raise


def get_circuit_breaker_health() -> Dict[str, Any]:
    """
    Get health status of all circuit breakers

    Returns:
        Dictionary with circuit breaker states and stats
    """
    stats = broker_circuit_breakers.get_all_stats()

    # Calculate overall health
    total_breakers = len(stats)
    open_breakers = sum(1 for s in stats.values() if s["state"] == "open")
    healthy = open_breakers == 0

    return {
        "healthy": healthy,
        "total_breakers": total_breakers,
        "open_breakers": open_breakers,
        "breakers": stats
    }
