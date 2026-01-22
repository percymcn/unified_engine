"""
Position Counter Adapter

Implements PositionCounterPort for counting positions by account and symbol.
Uses the database to query position counts.
"""

from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Position
import logging

logger = logging.getLogger(__name__)


class PositionCounterAdapter:
    """
    Adapter for counting open positions.

    Implements PositionCounterPort protocol for RiskEnforcementService.
    Can work with both sync and async sessions.
    """

    def __init__(self, session: Session = None, async_session: AsyncSession = None):
        """
        Initialize with session.

        Args:
            session: Sync SQLAlchemy session
            async_session: Async SQLAlchemy session
        """
        self._session = session
        self._async_session = async_session

    async def count_open(self, account_id: int) -> int:
        """
        Count total open positions for account.

        Args:
            account_id: Account ID

        Returns:
            Number of open positions
        """
        if self._async_session:
            return await self._count_open_async(account_id)
        elif self._session:
            return self._count_open_sync(account_id)
        else:
            logger.warning(f"No session available for position count, returning 0")
            return 0

    async def count_open_for_symbol(self, account_id: int, symbol: str) -> int:
        """
        Count open positions for specific symbol.

        Args:
            account_id: Account ID
            symbol: Trading symbol

        Returns:
            Number of open positions for symbol
        """
        if self._async_session:
            return await self._count_open_for_symbol_async(account_id, symbol)
        elif self._session:
            return self._count_open_for_symbol_sync(account_id, symbol)
        else:
            logger.warning(f"No session available for symbol position count, returning 0")
            return 0

    async def _count_open_async(self, account_id: int) -> int:
        """Async count of open positions"""
        try:
            stmt = select(func.count(Position.id)).where(
                and_(
                    Position.account_id == account_id,
                    Position.status == PositionStatus.OPEN
                )
            )
            result = await self._async_session.execute(stmt)
            count = result.scalar() or 0
            logger.debug(f"Account {account_id}: {count} open positions")
            return count
        except Exception as e:
            logger.error(f"Error counting positions for account {account_id}: {e}")
            return 0

    async def _count_open_for_symbol_async(self, account_id: int, symbol: str) -> int:
        """Async count of open positions for symbol"""
        try:
            stmt = select(func.count(Position.id)).where(
                and_(
                    Position.account_id == account_id,
                    Position.symbol == symbol,
                    Position.status == PositionStatus.OPEN
                )
            )
            result = await self._async_session.execute(stmt)
            count = result.scalar() or 0
            logger.debug(f"Account {account_id}, symbol {symbol}: {count} open positions")
            return count
        except Exception as e:
            logger.error(f"Error counting positions for account {account_id} symbol {symbol}: {e}")
            return 0

    def _count_open_sync(self, account_id: int) -> int:
        """Sync count of open positions"""
        try:
            count = self._session.query(func.count(Position.id)).filter(
                and_(
                    Position.account_id == account_id,
                    Position.status == PositionStatus.OPEN
                )
            ).scalar() or 0
            logger.debug(f"Account {account_id}: {count} open positions (sync)")
            return count
        except Exception as e:
            logger.error(f"Error counting positions for account {account_id}: {e}")
            return 0

    def _count_open_for_symbol_sync(self, account_id: int, symbol: str) -> int:
        """Sync count of open positions for symbol"""
        try:
            count = self._session.query(func.count(Position.id)).filter(
                and_(
                    Position.account_id == account_id,
                    Position.symbol == symbol,
                    Position.status == PositionStatus.OPEN
                )
            ).scalar() or 0
            logger.debug(f"Account {account_id}, symbol {symbol}: {count} open positions (sync)")
            return count
        except Exception as e:
            logger.error(f"Error counting positions for account {account_id} symbol {symbol}: {e}")
            return 0


class InMemoryPositionCounter:
    """
    In-memory position counter for testing or when database is not available.

    Also useful when position data comes from broker API instead of database.
    """

    def __init__(self):
        """Initialize with empty state"""
        self._positions = {}  # {account_id: {symbol: count}}

    async def count_open(self, account_id: int) -> int:
        """Count total open positions for account"""
        account_positions = self._positions.get(account_id, {})
        return sum(account_positions.values())

    async def count_open_for_symbol(self, account_id: int, symbol: str) -> int:
        """Count open positions for symbol"""
        account_positions = self._positions.get(account_id, {})
        return account_positions.get(symbol, 0)

    def set_position_count(self, account_id: int, symbol: str, count: int) -> None:
        """Set position count (for testing)"""
        if account_id not in self._positions:
            self._positions[account_id] = {}
        self._positions[account_id][symbol] = count

    def clear(self) -> None:
        """Clear all position counts"""
        self._positions.clear()
