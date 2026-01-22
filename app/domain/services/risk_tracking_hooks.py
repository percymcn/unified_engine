"""
Risk Tracking Hooks - Domain Service

Helper functions to update risk tracking when trades close or equity changes.
These can be called from signal processors, webhooks, or sync services.
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskTrackingHooks:
    """
    Helper service for updating risk tracking on trade events.

    This service provides hooks that should be called by:
    - Signal processors when trades close
    - Account sync services when equity updates
    - Webhook handlers when receiving broker notifications
    """

    def __init__(
        self,
        daily_pnl_service=None,
        drawdown_service=None
    ):
        """
        Initialize risk tracking hooks.

        Args:
            daily_pnl_service: DailyPnLService instance
            drawdown_service: DrawdownService instance
        """
        self._daily_pnl = daily_pnl_service
        self._drawdown = drawdown_service

    async def on_trade_closed(
        self,
        account_id: int,
        pnl: float,
        is_win: bool
    ):
        """
        Call when a trade is closed to update daily P&L tracking.

        Args:
            account_id: Account ID
            pnl: Profit/loss from the closed trade
            is_win: True if trade was profitable, False otherwise

        Example:
            await hooks.on_trade_closed(account_id=1, pnl=-50.0, is_win=False)
        """
        if not self._daily_pnl:
            logger.debug("Daily P&L service not configured, skipping trade P&L update")
            return

        try:
            state = await self._daily_pnl.record_trade_close(account_id, pnl, is_win)
            logger.info(
                f"Updated daily P&L for account {account_id}: "
                f"total={state.total_pnl:.2f}, trades={state.realized_pnl:.2f}"
            )

            # Check if we hit daily loss limit
            if state.is_trading_halted:
                logger.warning(
                    f"Account {account_id} halted: {state.halt_reason}"
                )

        except Exception as e:
            logger.error(f"Error updating daily P&L for account {account_id}: {e}")

    async def on_equity_update(
        self,
        account_id: int,
        equity: float,
        balance: float,
        unrealized_pnl: Optional[float] = None
    ):
        """
        Call when account equity is updated to track drawdown and unrealized P&L.

        This should be called:
        - After syncing account state from broker
        - When receiving real-time position updates
        - Periodically to maintain accurate drawdown tracking

        Args:
            account_id: Account ID
            equity: Current account equity
            balance: Current account balance
            unrealized_pnl: Unrealized P&L from open positions (optional)

        Example:
            await hooks.on_equity_update(
                account_id=1,
                equity=10500.0,
                balance=10000.0,
                unrealized_pnl=500.0
            )
        """
        try:
            # Update drawdown tracking
            if self._drawdown:
                state = await self._drawdown.record_equity(account_id, equity, balance)
                logger.debug(
                    f"Updated drawdown for account {account_id}: "
                    f"equity={equity:.2f}, peak={state.peak_equity:.2f}, "
                    f"drawdown={state.drawdown_pct:.2f}%"
                )

                # Log warning if approaching max drawdown
                if state.drawdown_pct > 0:
                    logger.info(
                        f"Account {account_id} drawdown: {state.drawdown_pct:.2f}% "
                        f"from peak ${state.peak_equity:.2f}"
                    )

            # Update unrealized P&L
            if self._daily_pnl and unrealized_pnl is not None:
                await self._daily_pnl.update_unrealized_pnl(
                    account_id,
                    unrealized_pnl,
                    balance
                )
                logger.debug(
                    f"Updated unrealized P&L for account {account_id}: {unrealized_pnl:.2f}"
                )

        except Exception as e:
            logger.error(f"Error updating equity tracking for account {account_id}: {e}")

    async def initialize_daily_pnl(
        self,
        account_id: int,
        starting_balance: float
    ):
        """
        Initialize daily P&L record for an account.

        Call this at the start of the trading day or when first tracking begins.

        Args:
            account_id: Account ID
            starting_balance: Starting balance for the day
        """
        if not self._daily_pnl:
            logger.debug("Daily P&L service not configured, skipping initialization")
            return

        try:
            state = await self._daily_pnl.get_or_initialize(account_id, starting_balance)
            logger.info(
                f"Initialized daily P&L for account {account_id}: "
                f"starting_balance=${starting_balance:.2f}"
            )
        except Exception as e:
            logger.error(f"Error initializing daily P&L for account {account_id}: {e}")
