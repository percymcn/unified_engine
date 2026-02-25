"""
Circuit Breaker Pattern Implementation for External API Calls
Prevents cascading failures and provides graceful degradation
"""

import time
import logging
from typing import Callable, Any, Optional, Dict
from enum import Enum
from dataclasses import dataclass, field
from threading import Lock
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout: float = 60.0  # Seconds before trying half-open
    expected_exception: type = Exception
    name: str = "default"


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker for external API calls

    Usage:
        breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            name="tradelocker_api"
        )

        @breaker.call
        def risky_api_call():
            return external_api.request()
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = Lock()

        logger.info(
            f"Circuit breaker '{self.config.name}' initialized: "
            f"threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self.stats.state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (operational)"""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)"""
        return self.state == CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open"""
        if self.stats.last_failure_time is None:
            return False
        return (time.time() - self.stats.last_failure_time) >= self.config.timeout

    def _record_success(self):
        """Record successful call"""
        with self._lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = time.time()

            if self.stats.state == CircuitState.HALF_OPEN:
                if self.stats.success_count >= self.config.success_threshold:
                    logger.info(f"Circuit breaker '{self.config.name}' CLOSED (recovered)")
                    self.stats.state = CircuitState.CLOSED
                    self.stats.failure_count = 0
                    self.stats.success_count = 0

    def _record_failure(self):
        """Record failed call"""
        with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = time.time()
            self.stats.success_count = 0  # Reset success count

            if self.stats.state == CircuitState.CLOSED:
                if self.stats.failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit breaker '{self.config.name}' OPENED "
                        f"after {self.stats.failure_count} failures"
                    )
                    self.stats.state = CircuitState.OPEN
            elif self.stats.state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit breaker '{self.config.name}' reopened "
                    f"(test failed)"
                )
                self.stats.state = CircuitState.OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Raises:
            CircuitBreakerOpenException: If circuit is open
        """
        with self._lock:
            self.stats.total_calls += 1

            # Check if we should try half-open
            if self.stats.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(
                        f"Circuit breaker '{self.config.name}' trying HALF_OPEN"
                    )
                    self.stats.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.config.name}' is OPEN. "
                        f"Service unavailable."
                    )

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.config.expected_exception as e:
            self._record_failure()
            raise

    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.call_async(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        with self._lock:
            self.stats.total_calls += 1

            if self.stats.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(
                        f"Circuit breaker '{self.config.name}' trying HALF_OPEN"
                    )
                    self.stats.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.config.name}' is OPEN"
                    )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.config.expected_exception as e:
            self._record_failure()
            raise

    def reset(self):
        """Manually reset circuit breaker"""
        with self._lock:
            logger.info(f"Circuit breaker '{self.config.name}' manually reset")
            self.stats.state = CircuitState.CLOSED
            self.stats.failure_count = 0
            self.stats.success_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.config.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_calls": self.stats.total_calls,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "last_failure": self.stats.last_failure_time,
            "last_success": self.stats.last_success_time,
        }


class CircuitBreakerRegistry:
    """
    Global registry for circuit breakers
    Allows centralized monitoring and management
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: Dict[str, CircuitBreaker] = {}
        return cls._instance

    def register(self, name: str, breaker: CircuitBreaker):
        """Register a circuit breaker"""
        self._breakers[name] = breaker
        logger.info(f"Registered circuit breaker: {name}")

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


def create_broker_circuit_breaker(broker_name: str) -> CircuitBreaker:
    """
    Create circuit breaker for broker API

    Args:
        broker_name: Name of broker (mt4, mt5, tradelocker, etc.)

    Returns:
        Configured CircuitBreaker instance
    """
    config = CircuitBreakerConfig(
        failure_threshold=5,  # Open after 5 failures
        success_threshold=2,  # Close after 2 successes
        timeout=60.0,  # Try again after 60 seconds
        expected_exception=Exception,
        name=f"{broker_name}_api"
    )

    breaker = CircuitBreaker(config)
    circuit_breaker_registry.register(config.name, breaker)

    return breaker
