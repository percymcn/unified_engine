"""
Drawdown Service - Domain Service

Tracks equity peaks and calculates drawdown.
"""

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class DrawdownState:
    """Current drawdown state for an account"""
    account_id: int
    current_equity: float
    peak_equity: float
    drawdown: float  # Absolute drawdown from peak
    drawdown_pct: float  # Percentage drawdown
    is_at_peak: bool


class EquityHistoryRepositoryPort(Protocol):
    """Port for equity history repository"""

    async def get_latest(self, account_id: int):
        """Get latest equity snapshot"""
        ...

    async def create(
        self,
        account_id: int,
        equity: float,
        balance: float,
        peak_equity: float,
        drawdown: float,
        drawdown_pct: float
    ):
        """Create equity snapshot"""
        ...

    async def update_peak(self, account_id: int, new_peak: float):
        """Update peak equity"""
        ...


class DrawdownService:
    """
    Tracks equity peaks and calculates drawdown.

    Drawdown = (Peak Equity - Current Equity) / Peak Equity * 100

    Key responsibilities:
    1. Record equity snapshots
    2. Track peak equity (high water mark)
    3. Calculate current drawdown
    4. Check if max drawdown exceeded
    """

    def __init__(self, repository: EquityHistoryRepositoryPort):
        self._repo = repository

    async def record_equity(self, account_id: int, equity: float, balance: float) -> DrawdownState:
        """
        Record equity snapshot and update drawdown calculation.

        Args:
            account_id: Account ID
            equity: Current equity
            balance: Current balance

        Returns:
            Updated DrawdownState
        """
        # Get current peak
        latest = await self._repo.get_latest(account_id)
        peak_equity = max(equity, latest.peak_equity if latest else equity)

        # Calculate drawdown
        drawdown = peak_equity - equity
        drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0

        # Record snapshot
        await self._repo.create(
            account_id=account_id,
            equity=equity,
            balance=balance,
            peak_equity=peak_equity,
            drawdown=drawdown,
            drawdown_pct=drawdown_pct
        )

        return DrawdownState(
            account_id=account_id,
            current_equity=equity,
            peak_equity=peak_equity,
            drawdown=drawdown,
            drawdown_pct=drawdown_pct,
            is_at_peak=equity >= peak_equity
        )

    async def get_current_state(self, account_id: int) -> Optional[DrawdownState]:
        """
        Get current drawdown state for account.

        Args:
            account_id: Account ID

        Returns:
            DrawdownState or None if no history exists
        """
        latest = await self._repo.get_latest(account_id)
        if not latest:
            return None

        return DrawdownState(
            account_id=account_id,
            current_equity=latest.equity,
            peak_equity=latest.peak_equity,
            drawdown=latest.drawdown,
            drawdown_pct=latest.drawdown_pct,
            is_at_peak=latest.equity >= latest.peak_equity
        )

    async def check_drawdown_limit(
        self,
        account_id: int,
        max_drawdown_pct: float
    ) -> tuple[bool, Optional[str]]:
        """
        Check if maximum drawdown limit has been exceeded.

        Args:
            account_id: Account ID
            max_drawdown_pct: Maximum allowed drawdown percentage

        Returns:
            (is_exceeded, reason) tuple
        """
        state = await self.get_current_state(account_id)
        if not state:
            return False, None

        if state.drawdown_pct >= max_drawdown_pct:
            reason = f"Max drawdown hit: {state.drawdown_pct:.2f}% >= {max_drawdown_pct}%"
            return True, reason

        return False, None

    async def reset_peak(self, account_id: int, new_peak: float):
        """
        Reset peak equity (e.g., after deposit or account reset).

        Use with caution - this affects drawdown calculations.

        Args:
            account_id: Account ID
            new_peak: New peak equity value
        """
        await self._repo.update_peak(account_id, new_peak)
