"""
Daily P&L Service - Domain Service

Tracks daily profit/loss per account.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Protocol


@dataclass
class DailyPnLState:
    """Current daily P&L state"""
    account_id: int
    date: date
    starting_balance: float
    current_balance: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    pnl_percent: float
    is_trading_halted: bool
    halt_reason: Optional[str] = None


class DailyPnLRepositoryPort(Protocol):
    """Port for daily P&L repository"""

    async def get_by_account_date(self, account_id: int, date_val: date):
        """Get daily P&L record for account and date"""
        ...

    async def create(
        self,
        account_id: int,
        date: date,
        starting_balance: float,
        current_balance: float
    ):
        """Create new daily P&L record"""
        ...

    async def save(self, record):
        """Save daily P&L record"""
        ...


class DailyPnLService:
    """
    Tracks daily profit/loss per account.

    Key responsibilities:
    1. Initialize daily record with starting balance
    2. Update P&L on trade close
    3. Check if daily loss limit exceeded
    4. Halt trading when limit hit
    """

    def __init__(self, repository: DailyPnLRepositoryPort):
        self._repo = repository

    async def get_or_initialize(self, account_id: int, starting_balance: float) -> DailyPnLState:
        """
        Get today's P&L record or initialize new one.

        Args:
            account_id: Account ID
            starting_balance: Starting balance for the day (if creating new record)

        Returns:
            DailyPnLState with current state
        """
        today = date.today()
        record = await self._repo.get_by_account_date(account_id, today)

        if not record:
            record = await self._repo.create(
                account_id=account_id,
                date=today,
                starting_balance=starting_balance,
                current_balance=starting_balance
            )

        return DailyPnLState(
            account_id=record.account_id,
            date=record.date,
            starting_balance=record.starting_balance,
            current_balance=record.current_balance or record.starting_balance,
            realized_pnl=record.realized_pnl or 0,
            unrealized_pnl=record.unrealized_pnl or 0,
            total_pnl=record.total_pnl or 0,
            pnl_percent=record.pnl_percent or 0,
            is_trading_halted=record.is_trading_halted,
            halt_reason=record.halt_reason
        )

    async def record_trade_close(
        self,
        account_id: int,
        pnl: float,
        is_win: bool
    ) -> DailyPnLState:
        """
        Record a closed trade's P&L.

        Args:
            account_id: Account ID
            pnl: Profit/loss from the trade
            is_win: Whether the trade was profitable

        Returns:
            Updated DailyPnLState
        """
        # Get existing record or create one (starting balance will be 0 if not set)
        record = await self._repo.get_by_account_date(account_id, date.today())
        if not record:
            # Initialize with 0 starting balance - should be set elsewhere
            record = await self._repo.create(
                account_id=account_id,
                date=date.today(),
                starting_balance=0,
                current_balance=0
            )

        # Update P&L
        record.realized_pnl = (record.realized_pnl or 0) + pnl
        record.total_pnl = record.realized_pnl + (record.unrealized_pnl or 0)
        record.pnl_percent = (record.total_pnl / record.starting_balance) * 100 if record.starting_balance else 0
        record.trades_count = (record.trades_count or 0) + 1

        if is_win:
            record.winning_trades = (record.winning_trades or 0) + 1
        else:
            record.losing_trades = (record.losing_trades or 0) + 1

        await self._repo.save(record)

        return DailyPnLState(
            account_id=record.account_id,
            date=record.date,
            starting_balance=record.starting_balance,
            current_balance=record.current_balance or record.starting_balance,
            realized_pnl=record.realized_pnl or 0,
            unrealized_pnl=record.unrealized_pnl or 0,
            total_pnl=record.total_pnl or 0,
            pnl_percent=record.pnl_percent or 0,
            is_trading_halted=record.is_trading_halted,
            halt_reason=record.halt_reason
        )

    async def update_unrealized_pnl(
        self,
        account_id: int,
        unrealized_pnl: float,
        current_balance: float
    ) -> DailyPnLState:
        """
        Update unrealized P&L from open positions.

        Args:
            account_id: Account ID
            unrealized_pnl: Unrealized P&L from open positions
            current_balance: Current account balance

        Returns:
            Updated DailyPnLState
        """
        record = await self._repo.get_by_account_date(account_id, date.today())
        if record:
            record.unrealized_pnl = unrealized_pnl
            record.current_balance = current_balance
            record.total_pnl = (record.realized_pnl or 0) + unrealized_pnl
            record.pnl_percent = (record.total_pnl / record.starting_balance) * 100 if record.starting_balance else 0
            await self._repo.save(record)

        return await self.get_or_initialize(account_id, 0)

    async def check_daily_loss_limit(
        self,
        account_id: int,
        max_daily_loss: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if daily loss limit has been exceeded.

        Args:
            account_id: Account ID
            max_daily_loss: Maximum daily loss in account currency
            max_daily_loss_pct: Maximum daily loss as percentage

        Returns:
            (is_exceeded, reason) tuple
        """
        state = await self.get_or_initialize(account_id, 0)

        # Already halted
        if state.is_trading_halted:
            return True, state.halt_reason

        # Check absolute loss limit
        if max_daily_loss and state.total_pnl < 0:
            if abs(state.total_pnl) >= max_daily_loss:
                reason = f"Daily loss limit hit: ${abs(state.total_pnl):.2f} >= ${max_daily_loss:.2f}"
                await self._halt_trading(account_id, reason)
                return True, reason

        # Check percentage loss limit
        if max_daily_loss_pct and state.pnl_percent < 0:
            if abs(state.pnl_percent) >= max_daily_loss_pct:
                reason = f"Daily loss % limit hit: {abs(state.pnl_percent):.2f}% >= {max_daily_loss_pct}%"
                await self._halt_trading(account_id, reason)
                return True, reason

        return False, None

    async def check_daily_profit_target(
        self,
        account_id: int,
        max_daily_profit: Optional[float] = None,
        max_daily_profit_pct: Optional[float] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if daily profit target has been reached (should halt trading).

        Args:
            account_id: Account ID
            max_daily_profit: Maximum daily profit in account currency (HALT when reached)
            max_daily_profit_pct: Maximum daily profit as percentage (HALT when reached)

        Returns:
            (is_exceeded, reason) tuple
        """
        state = await self.get_or_initialize(account_id, 0)

        # Already halted
        if state.is_trading_halted:
            return True, state.halt_reason

        # Check absolute profit target
        if max_daily_profit and state.total_pnl > 0:
            if state.total_pnl >= max_daily_profit:
                reason = f"Daily profit target reached: ${state.total_pnl:.2f} >= ${max_daily_profit:.2f}"
                await self._halt_trading(account_id, reason)
                return True, reason

        # Check percentage profit target
        if max_daily_profit_pct and state.pnl_percent > 0:
            if state.pnl_percent >= max_daily_profit_pct:
                reason = f"Daily profit % target reached: {state.pnl_percent:.2f}% >= {max_daily_profit_pct}%"
                await self._halt_trading(account_id, reason)
                return True, reason

        return False, None

    async def _halt_trading(self, account_id: int, reason: str):
        """
        Halt trading for the day.

        Args:
            account_id: Account ID
            reason: Reason for halting
        """
        record = await self._repo.get_by_account_date(account_id, date.today())
        if record:
            record.is_trading_halted = True
            record.halt_reason = reason
            record.halted_at = datetime.utcnow()
            await self._repo.save(record)
