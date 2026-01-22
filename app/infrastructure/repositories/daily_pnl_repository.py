"""
Daily P&L Repository - Infrastructure Layer

Repository for daily profit/loss records.
"""

from typing import Optional
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import DailyPnL


class DailyPnLRepository:
    """Repository for daily P&L tracking"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_account_date(self, account_id: int, date_val: date) -> Optional[DailyPnL]:
        """
        Get daily P&L record for specific account and date.

        Args:
            account_id: Account ID
            date_val: Date to query

        Returns:
            DailyPnL record or None if not found
        """
        stmt = select(DailyPnL).where(
            DailyPnL.account_id == account_id,
            DailyPnL.date == date_val
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        account_id: int,
        date: date,
        starting_balance: float,
        current_balance: float
    ) -> DailyPnL:
        """
        Create new daily P&L record.

        Args:
            account_id: Account ID
            date: Date
            starting_balance: Starting balance
            current_balance: Current balance

        Returns:
            Created DailyPnL record
        """
        record = DailyPnL(
            account_id=account_id,
            date=date,
            starting_balance=starting_balance,
            current_balance=current_balance,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            total_pnl=0.0,
            pnl_percent=0.0,
            trades_count=0,
            winning_trades=0,
            losing_trades=0,
            is_trading_halted=False
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def save(self, record: DailyPnL) -> DailyPnL:
        """
        Save (update) existing daily P&L record.

        Args:
            record: DailyPnL record to save

        Returns:
            Updated record
        """
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_latest_for_account(self, account_id: int) -> Optional[DailyPnL]:
        """
        Get most recent daily P&L record for account.

        Args:
            account_id: Account ID

        Returns:
            Most recent DailyPnL record or None
        """
        stmt = select(DailyPnL).where(
            DailyPnL.account_id == account_id
        ).order_by(DailyPnL.date.desc()).limit(1)

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
