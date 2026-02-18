"""
Daily Counter Service - Domain Service

Tracks daily signal and trade counts per account for risk enforcement.
Date-based counters reset automatically at midnight UTC.
"""

from datetime import date, datetime
from typing import Dict, Optional, Protocol
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyCounters:
    """Daily counters for an account"""
    account_id: int
    date: date
    signals_received: int = 0
    trades_executed: int = 0
    trades_rejected: int = 0
    trades_by_symbol: Dict[str, int] = field(default_factory=dict)
    last_trade_at: Optional[datetime] = None

    def increment_signals(self) -> None:
        """Increment daily signal count"""
        self.signals_received += 1

    def increment_trades(self, symbol: str) -> None:
        """Increment daily trade count and per-symbol count"""
        self.trades_executed += 1
        self.trades_by_symbol[symbol] = self.trades_by_symbol.get(symbol, 0) + 1
        self.last_trade_at = datetime.utcnow()

    def get_symbol_count(self, symbol: str) -> int:
        """Get trade count for a specific symbol"""
        return self.trades_by_symbol.get(symbol, 0)


class DailyCounterRepository(Protocol):
    """Repository interface for daily counters (in-memory or persistent)"""

    async def get_or_create(self, account_id: int, for_date: date) -> DailyCounters:
        """Get or create counters for account on date"""
        ...

    async def save(self, counters: DailyCounters) -> None:
        """Save counters"""
        ...

    async def get_all_for_date(self, for_date: date) -> list[DailyCounters]:
        """Get all counters for a date"""
        ...


class DailyCounterService:
    """
    Tracks daily signal and trade counts per account.

    Counters reset automatically each day (UTC).
    Used by RiskEnforcementService to check daily limits.
    """

    def __init__(self, repository: DailyCounterRepository):
        """
        Initialize service with repository.

        Args:
            repository: Repository for counter persistence
        """
        self._repo = repository

    async def get_counters(self, account_id: int, for_date: date = None) -> DailyCounters:
        """
        Get or create daily counters for account.

        Args:
            account_id: Target account ID
            for_date: Date for counters (defaults to today UTC)

        Returns:
            DailyCounters for the account and date
        """
        if for_date is None:
            for_date = date.today()
        return await self._repo.get_or_create(account_id, for_date)

    async def increment_signals(self, account_id: int) -> DailyCounters:
        """
        Increment daily signal count for account.

        Args:
            account_id: Target account ID

        Returns:
            Updated DailyCounters
        """
        counters = await self.get_counters(account_id)
        counters.increment_signals()
        await self._repo.save(counters)
        logger.debug(f"Account {account_id} signals: {counters.signals_received}")
        return counters

    async def increment_trades(self, account_id: int, symbol: str) -> DailyCounters:
        """
        Increment daily trade count and per-symbol count.

        Args:
            account_id: Target account ID
            symbol: Trading symbol

        Returns:
            Updated DailyCounters
        """
        counters = await self.get_counters(account_id)
        counters.increment_trades(symbol)
        await self._repo.save(counters)
        logger.debug(
            f"Account {account_id} trades: {counters.trades_executed}, "
            f"{symbol}: {counters.trades_by_symbol.get(symbol, 0)}"
        )
        return counters

    async def get_signal_count(self, account_id: int) -> int:
        """
        Get today's signal count for account.

        Args:
            account_id: Target account ID

        Returns:
            Number of signals received today
        """
        counters = await self.get_counters(account_id)
        return counters.signals_received

    async def get_trade_count(self, account_id: int) -> int:
        """
        Get today's trade count for account.

        Args:
            account_id: Target account ID

        Returns:
            Number of trades executed today
        """
        counters = await self.get_counters(account_id)
        return counters.trades_executed

    async def get_symbol_trade_count(self, account_id: int, symbol: str) -> int:
        """
        Get today's trade count for specific symbol.

        Args:
            account_id: Target account ID
            symbol: Trading symbol

        Returns:
            Number of trades for symbol today
        """
        counters = await self.get_counters(account_id)
        return counters.get_symbol_count(symbol)

    async def get_last_trade_time(self, account_id: int) -> Optional[datetime]:
        """
        Get timestamp of last trade for account.

        Args:
            account_id: Target account ID

        Returns:
            Datetime of last trade, or None if no trades today
        """
        counters = await self.get_counters(account_id)
        return counters.last_trade_at
