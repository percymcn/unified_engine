"""
Risk Enforcement Service - Domain Service

Evaluates and enforces trade/signal limits before execution.
This is the core service for all risk management features.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Protocol
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskCheckResult(Enum):
    """Result of risk check"""
    PASSED = "passed"
    BLOCKED = "blocked"


@dataclass
class RiskViolation:
    """Details of a risk limit violation"""
    reason: str  # RejectedSignalReason value (e.g., "daily_limit")
    detail: str  # Human-readable explanation
    limit_value: float  # The limit that was hit
    current_value: float  # The current value at rejection time


@dataclass
class RiskEvaluation:
    """Result of risk evaluation"""
    result: RiskCheckResult
    violations: List[RiskViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if evaluation passed"""
        return self.result == RiskCheckResult.PASSED

    @property
    def blocked(self) -> bool:
        """Check if evaluation blocked the signal"""
        return self.result == RiskCheckResult.BLOCKED

    @property
    def first_violation(self) -> Optional[RiskViolation]:
        """Get the first (primary) violation"""
        return self.violations[0] if self.violations else None

    @property
    def all_reasons(self) -> List[str]:
        """Get all violation reasons"""
        return [v.reason for v in self.violations]


@dataclass
class AccountRiskSettings:
    """Account risk settings for evaluation"""
    max_daily_trades: Optional[int] = None
    max_open_positions: Optional[int] = None
    max_positions_per_symbol: int = 1
    trade_cooldown_seconds: Optional[int] = None
    max_daily_loss: Optional[float] = None
    max_daily_loss_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    risk_management_enabled: bool = True

    @classmethod
    def from_account(cls, account) -> "AccountRiskSettings":
        """
        Create settings from a TradingAccount model.

        Args:
            account: TradingAccount model instance

        Returns:
            AccountRiskSettings instance
        """
        return cls(
            max_daily_trades=getattr(account, 'max_daily_trades', None),
            max_open_positions=getattr(account, 'max_open_positions', None),
            max_positions_per_symbol=getattr(account, 'max_positions_per_symbol', None) or 1,
            trade_cooldown_seconds=getattr(account, 'trade_cooldown_seconds', None),
            max_daily_loss=getattr(account, 'max_daily_loss', None),
            max_daily_loss_pct=getattr(account, 'max_daily_loss_pct', None),
            max_drawdown_pct=getattr(account, 'max_drawdown_pct', None),
        )


class PositionCounterPort(Protocol):
    """Port for counting positions"""

    async def count_open(self, account_id: int) -> int:
        """Count total open positions for account"""
        ...

    async def count_open_for_symbol(self, account_id: int, symbol: str) -> int:
        """Count open positions for specific symbol"""
        ...


class DailyCounterPort(Protocol):
    """Port for daily counters"""

    async def get_counters(self, account_id: int):
        """Get daily counters for account"""
        ...


class RiskEnforcementService:
    """
    Evaluates and enforces risk limits before signal execution.

    Checks performed:
    1. Daily signal limit (max_daily_trades)
    2. Concurrent position limit (max_open_positions)
    3. Per-symbol position limit (max_positions_per_symbol)
    4. Trade cooldown (trade_cooldown_seconds)

    Future checks (Phase 22-03):
    - Daily loss limit
    - Drawdown limit
    - Risk/reward ratio
    """

    def __init__(
        self,
        counter_service: DailyCounterPort,
        position_counter: PositionCounterPort,
    ):
        """
        Initialize risk enforcement service.

        Args:
            counter_service: Service for daily counters
            position_counter: Service/repo for position counting
        """
        self._counters = counter_service
        self._positions = position_counter

    async def evaluate(
        self,
        account_id: int,
        symbol: str,
        action: str,
        settings: AccountRiskSettings,
    ) -> RiskEvaluation:
        """
        Evaluate all risk limits for a signal.

        Args:
            account_id: Target account ID
            symbol: Trading symbol
            action: Signal action (buy, sell, close)
            settings: Account risk settings

        Returns:
            RiskEvaluation with pass/block result and any violations
        """
        violations = []

        # Skip checks for close actions - always allow closing
        if action.lower() in ('close', 'close_all', 'flatten'):
            logger.debug(f"Skipping risk checks for close action on account {account_id}")
            return RiskEvaluation(RiskCheckResult.PASSED, [])

        # Check 1: Daily trade limit
        if settings.max_daily_trades is not None and settings.max_daily_trades > 0:
            counters = await self._counters.get_counters(account_id)
            if counters.trades_executed >= settings.max_daily_trades:
                violations.append(RiskViolation(
                    reason="daily_limit",
                    detail=f"Daily trade limit reached ({counters.trades_executed}/{settings.max_daily_trades})",
                    limit_value=float(settings.max_daily_trades),
                    current_value=float(counters.trades_executed)
                ))
                logger.info(
                    f"Account {account_id}: Daily limit blocked - "
                    f"{counters.trades_executed}/{settings.max_daily_trades} trades"
                )

        # Check 2: Concurrent position limit (total)
        if settings.max_open_positions is not None and settings.max_open_positions > 0:
            open_positions = await self._positions.count_open(account_id)
            if open_positions >= settings.max_open_positions:
                violations.append(RiskViolation(
                    reason="concurrent_limit",
                    detail=f"Max open positions reached ({open_positions}/{settings.max_open_positions})",
                    limit_value=float(settings.max_open_positions),
                    current_value=float(open_positions)
                ))
                logger.info(
                    f"Account {account_id}: Concurrent limit blocked - "
                    f"{open_positions}/{settings.max_open_positions} positions"
                )

        # Check 3: Per-symbol position limit
        if settings.max_positions_per_symbol is not None and settings.max_positions_per_symbol > 0:
            symbol_positions = await self._positions.count_open_for_symbol(account_id, symbol)
            if symbol_positions >= settings.max_positions_per_symbol:
                violations.append(RiskViolation(
                    reason="symbol_limit",
                    detail=f"Max positions for {symbol} reached ({symbol_positions}/{settings.max_positions_per_symbol})",
                    limit_value=float(settings.max_positions_per_symbol),
                    current_value=float(symbol_positions)
                ))
                logger.info(
                    f"Account {account_id}: Symbol limit blocked - "
                    f"{symbol} has {symbol_positions}/{settings.max_positions_per_symbol} positions"
                )

        # Check 4: Trade cooldown
        if settings.trade_cooldown_seconds is not None and settings.trade_cooldown_seconds > 0:
            counters = await self._counters.get_counters(account_id)
            if counters.last_trade_at:
                elapsed = (datetime.utcnow() - counters.last_trade_at).total_seconds()
                if elapsed < settings.trade_cooldown_seconds:
                    remaining = settings.trade_cooldown_seconds - elapsed
                    violations.append(RiskViolation(
                        reason="cooldown",
                        detail=f"Trade cooldown active ({remaining:.0f}s remaining)",
                        limit_value=float(settings.trade_cooldown_seconds),
                        current_value=float(elapsed)
                    ))
                    logger.info(
                        f"Account {account_id}: Cooldown blocked - "
                        f"{remaining:.0f}s remaining of {settings.trade_cooldown_seconds}s"
                    )

        # Determine result
        result = RiskCheckResult.BLOCKED if violations else RiskCheckResult.PASSED

        if result == RiskCheckResult.PASSED:
            logger.debug(f"Account {account_id}: Risk checks passed for {symbol} {action}")

        return RiskEvaluation(result, violations)

    def evaluate_sync(
        self,
        trades_executed: int,
        open_positions: int,
        symbol_positions: int,
        last_trade_elapsed: Optional[float],
        settings: AccountRiskSettings,
        symbol: str,
        action: str,
    ) -> RiskEvaluation:
        """
        Synchronous evaluation for testing or when data is pre-fetched.

        Args:
            trades_executed: Number of trades executed today
            open_positions: Number of open positions
            symbol_positions: Number of open positions for symbol
            last_trade_elapsed: Seconds since last trade (None if no trades)
            settings: Account risk settings
            symbol: Trading symbol
            action: Signal action

        Returns:
            RiskEvaluation
        """
        violations = []

        # Skip checks for close actions
        if action.lower() in ('close', 'close_all', 'flatten'):
            return RiskEvaluation(RiskCheckResult.PASSED, [])

        # Check 1: Daily trade limit
        if settings.max_daily_trades and trades_executed >= settings.max_daily_trades:
            violations.append(RiskViolation(
                reason="daily_limit",
                detail=f"Daily trade limit reached ({trades_executed}/{settings.max_daily_trades})",
                limit_value=float(settings.max_daily_trades),
                current_value=float(trades_executed)
            ))

        # Check 2: Concurrent position limit
        if settings.max_open_positions and open_positions >= settings.max_open_positions:
            violations.append(RiskViolation(
                reason="concurrent_limit",
                detail=f"Max open positions reached ({open_positions}/{settings.max_open_positions})",
                limit_value=float(settings.max_open_positions),
                current_value=float(open_positions)
            ))

        # Check 3: Per-symbol limit
        if settings.max_positions_per_symbol and symbol_positions >= settings.max_positions_per_symbol:
            violations.append(RiskViolation(
                reason="symbol_limit",
                detail=f"Max positions for {symbol} reached ({symbol_positions}/{settings.max_positions_per_symbol})",
                limit_value=float(settings.max_positions_per_symbol),
                current_value=float(symbol_positions)
            ))

        # Check 4: Cooldown
        if settings.trade_cooldown_seconds and last_trade_elapsed is not None:
            if last_trade_elapsed < settings.trade_cooldown_seconds:
                remaining = settings.trade_cooldown_seconds - last_trade_elapsed
                violations.append(RiskViolation(
                    reason="cooldown",
                    detail=f"Trade cooldown active ({remaining:.0f}s remaining)",
                    limit_value=float(settings.trade_cooldown_seconds),
                    current_value=float(last_trade_elapsed)
                ))

        result = RiskCheckResult.BLOCKED if violations else RiskCheckResult.PASSED
        return RiskEvaluation(result, violations)
