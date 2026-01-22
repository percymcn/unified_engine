"""
Daily Counter Repository - In-Memory Implementation

Stores daily counters in memory with automatic date-based expiration.
Suitable for single-instance deployments. For multi-instance, use Redis.
"""

from datetime import date, datetime
from typing import Dict, Optional
import asyncio
import logging

from app.domain.services.daily_counter_service import DailyCounters

logger = logging.getLogger(__name__)


class InMemoryDailyCounterRepository:
    """
    In-memory repository for daily counters.

    Stores counters keyed by (account_id, date).
    Automatically cleans up old entries.
    """

    def __init__(self):
        """Initialize in-memory storage"""
        # Storage: {(account_id, date_str): DailyCounters}
        self._storage: Dict[tuple, DailyCounters] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = date.today()

    def _make_key(self, account_id: int, for_date: date) -> tuple:
        """Create storage key from account_id and date"""
        return (account_id, for_date.isoformat())

    async def get_or_create(self, account_id: int, for_date: date) -> DailyCounters:
        """
        Get or create counters for account on date.

        Args:
            account_id: Account ID
            for_date: Date for counters

        Returns:
            DailyCounters instance
        """
        async with self._lock:
            # Cleanup old entries if needed
            await self._cleanup_if_needed()

            key = self._make_key(account_id, for_date)
            if key not in self._storage:
                self._storage[key] = DailyCounters(
                    account_id=account_id,
                    date=for_date
                )
            return self._storage[key]

    async def save(self, counters: DailyCounters) -> None:
        """
        Save counters to storage.

        Args:
            counters: DailyCounters to save
        """
        async with self._lock:
            key = self._make_key(counters.account_id, counters.date)
            self._storage[key] = counters

    async def get_all_for_date(self, for_date: date) -> list[DailyCounters]:
        """
        Get all counters for a specific date.

        Args:
            for_date: Date to query

        Returns:
            List of DailyCounters for that date
        """
        async with self._lock:
            return [
                counters for (_, d), counters in self._storage.items()
                if d == for_date.isoformat()
            ]

    async def _cleanup_if_needed(self) -> None:
        """Remove entries older than yesterday"""
        today = date.today()
        if today == self._last_cleanup:
            return

        # Remove entries older than yesterday
        yesterday = date.today().isoformat()
        keys_to_remove = [
            key for key in self._storage.keys()
            if key[1] < yesterday
        ]

        for key in keys_to_remove:
            del self._storage[key]

        self._last_cleanup = today
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} old counter entries")

    async def clear(self) -> None:
        """Clear all counters (for testing)"""
        async with self._lock:
            self._storage.clear()


# Global singleton instance for simplicity
_counter_repository: Optional[InMemoryDailyCounterRepository] = None


def get_daily_counter_repository() -> InMemoryDailyCounterRepository:
    """
    Get the global daily counter repository instance.

    Returns:
        InMemoryDailyCounterRepository singleton
    """
    global _counter_repository
    if _counter_repository is None:
        _counter_repository = InMemoryDailyCounterRepository()
    return _counter_repository
