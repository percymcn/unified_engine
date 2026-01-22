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
    min_risk_reward_ratio: Optional[float] = None
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
            min_risk_reward_ratio=getattr(account, 'min_risk_reward_ratio', None),
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


class DailyPnLPort(Protocol):
    """Port for daily P&L tracking"""

    async def check_daily_loss_limit(
        self,
        account_id: int,
        max_daily_loss: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None
    ) -> tuple[bool, Optional[str]]:
        """Check if daily loss limit exceeded"""
        ...


class DrawdownPort(Protocol):
    """Port for drawdown tracking"""

    async def check_drawdown_limit(
        self,
        account_id: int,
        max_drawdown_pct: float
    ) -> tuple[bool, Optional[str]]:
        """Check if drawdown limit exceeded"""
        ...


class RiskEnforcementService:
    """
    Evaluates and enforces risk limits before signal execution.

    Checks performed:
    1. Daily signal limit (max_daily_trades)
    2. Concurrent position limit (max_open_positions)
    3. Per-symbol position limit (max_positions_per_symbol)
    4. Trade cooldown (trade_cooldown_seconds)
    5. Daily loss limit (max_daily_loss, max_daily_loss_pct)
    6. Maximum drawdown limit (max_drawdown_pct)

    Future checks:
    - Risk/reward ratio
    """

    def __init__(
        self,
        counter_service: DailyCounterPort,
        position_counter: PositionCounterPort,
        daily_pnl_service: Optional[DailyPnLPort] = None,
        drawdown_service: Optional[DrawdownPort] = None,
    ):
        """
        Initialize risk enforcement service.

        Args:
            counter_service: Service for daily counters
            position_counter: Service/repo for position counting
            daily_pnl_service: Service for daily P&L tracking (optional)
            drawdown_service: Service for drawdown tracking (optional)
        """
        self._counters = counter_service
        self._positions = position_counter
        self._daily_pnl = daily_pnl_service
        self._drawdown = drawdown_service

    async def evaluate(
        self,
        account_id: int,
        symbol: str,
        action: str,
        settings: AccountRiskSettings,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> RiskEvaluation:
        """
        Evaluate all risk limits for a signal.

        Args:
            account_id: Target account ID
            symbol: Trading symbol
            action: Signal action (buy, sell, close)
            settings: Account risk settings
            entry_price: Entry price for risk-reward calculation
            stop_loss: Stop loss price for risk-reward calculation
            take_profit: Take profit price for risk-reward calculation

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

        # Check 5: Daily loss limit
        if self._daily_pnl and (settings.max_daily_loss or settings.max_daily_loss_pct):
            is_exceeded, reason = await self._daily_pnl.check_daily_loss_limit(
                account_id,
                max_daily_loss=settings.max_daily_loss,
                max_daily_loss_pct=settings.max_daily_loss_pct
            )
            if is_exceeded:
                violations.append(RiskViolation(
                    reason="daily_loss",
                    detail=reason,
                    limit_value=settings.max_daily_loss or settings.max_daily_loss_pct,
                    current_value=0.0  # Actual value is in the detail string
                ))
                logger.info(f"Account {account_id}: Daily loss limit blocked - {reason}")

        # Check 6: Maximum drawdown limit
        if self._drawdown and settings.max_drawdown_pct:
            is_exceeded, reason = await self._drawdown.check_drawdown_limit(
                account_id,
                max_drawdown_pct=settings.max_drawdown_pct
            )
            if is_exceeded:
                violations.append(RiskViolation(
                    reason="drawdown",
                    detail=reason,
                    limit_value=settings.max_drawdown_pct,
                    current_value=0.0  # Actual value is in the detail string
                ))
                logger.info(f"Account {account_id}: Drawdown limit blocked - {reason}")

        # Check 7: Risk-reward ratio
        if settings.min_risk_reward_ratio and entry_price and stop_loss and take_profit:
            is_valid, reason, ratio = self.validate_risk_reward(
                entry_price, stop_loss, take_profit, settings.min_risk_reward_ratio
            )
            if not is_valid:
                violations.append(RiskViolation(
                    reason="risk_reward",
                    detail=reason,
                    limit_value=settings.min_risk_reward_ratio,
                    current_value=ratio
                ))
                logger.info(f"Account {account_id}: Risk-reward blocked - {reason}")

        # Determine result
        result = RiskCheckResult.BLOCKED if violations else RiskCheckResult.PASSED

        if result == RiskCheckResult.PASSED:
            logger.debug(f"Account {account_id}: Risk checks passed for {symbol} {action}")

        return RiskEvaluation(result, violations)

    def validate_risk_reward(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        min_risk_reward: float = 1.0
    ) -> tuple[bool, Optional[str], float]:
        """
        Validate risk-reward ratio meets minimum threshold.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            min_risk_reward: Minimum required R:R ratio

        Returns:
            (is_valid, reason, actual_ratio) tuple
        """
        if not stop_loss or not take_profit:
            # Can't validate without SL/TP
            return True, None, 0.0

        # Calculate risk and reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk == 0:
            return False, "Invalid stop loss (zero risk)", 0.0

        ratio = reward / risk

        if ratio < min_risk_reward:
            reason = f"Risk-reward ratio {ratio:.2f}:1 below minimum {min_risk_reward}:1"
            return False, reason, ratio

        return True, None, ratio

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
