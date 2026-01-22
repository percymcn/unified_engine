"""
Equity History Repository - Infrastructure Layer

Repository for account equity history tracking.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import AccountEquityHistory


class EquityHistoryRepository:
    """Repository for equity history tracking"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_latest(self, account_id: int) -> Optional[AccountEquityHistory]:
        """
        Get most recent equity snapshot for account.

        Args:
            account_id: Account ID

        Returns:
            Most recent AccountEquityHistory record or None
        """
        stmt = select(AccountEquityHistory).where(
            AccountEquityHistory.account_id == account_id
        ).order_by(AccountEquityHistory.timestamp.desc()).limit(1)

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        account_id: int,
        equity: float,
        balance: float,
        peak_equity: float,
        drawdown: float,
        drawdown_pct: float
    ) -> AccountEquityHistory:
        """
        Create new equity history record.

        Args:
            account_id: Account ID
            equity: Current equity
            balance: Current balance
            peak_equity: Peak equity (high water mark)
            drawdown: Drawdown from peak (absolute)
            drawdown_pct: Drawdown percentage

        Returns:
            Created AccountEquityHistory record
        """
        record = AccountEquityHistory(
            account_id=account_id,
            equity=equity,
            balance=balance,
            peak_equity=peak_equity,
            drawdown=drawdown,
            drawdown_pct=drawdown_pct
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def update_peak(self, account_id: int, new_peak: float):
        """
        Update peak equity for an account.
        This is a dangerous operation - use with caution.

        Args:
            account_id: Account ID
            new_peak: New peak equity value
        """
        # Get latest record
        latest = await self.get_latest(account_id)
        if latest:
            # Create new record with updated peak
            await self.create(
                account_id=account_id,
                equity=latest.equity,
                balance=latest.balance,
                peak_equity=new_peak,
                drawdown=max(0, new_peak - latest.equity),
                drawdown_pct=(max(0, new_peak - latest.equity) / new_peak * 100) if new_peak > 0 else 0
            )
