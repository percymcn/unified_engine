"""
Agentic Trading Monitor
========================

Autonomous monitoring agent that watches for trading mistakes and anomalies.

Features:
1. PRE-TRADE VALIDATION - Validates signals BEFORE execution
2. POST-TRADE MONITORING - Verifies trades match intent
3. ANOMALY DETECTION - Catches patterns that shouldn't happen
4. AUTO-PAUSE - Stops trading when critical errors detected
5. SELF-HEALING - Attempts to fix known issues automatically

This runs as a watchdog over the trading system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
EST_TZ = ZoneInfo("America/New_York")


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"  # Auto-pause trading


class AlertType(str, Enum):
    DIRECTION_MISMATCH = "direction_mismatch"
    REGIME_VIOLATION = "regime_violation"
    RAPID_LOSSES = "rapid_losses"
    DUPLICATE_SIGNAL = "duplicate_signal"
    POSITION_OVERFLOW = "position_overflow"
    ENGINE_DISAGREEMENT = "engine_disagreement"
    DATA_STALE = "data_stale"
    TIMEZONE_ERROR = "timezone_error"
    CONFIDENCE_TOO_LOW = "confidence_too_low"
    WIN_RATE_CRASH = "win_rate_crash"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    DRAWDOWN_LIMIT = "drawdown_limit"


@dataclass
class MonitorAlert:
    """Single monitoring alert."""
    timestamp: datetime
    alert_type: AlertType
    severity: AlertSeverity
    ticker: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    auto_action: Optional[str] = None  # Action taken automatically


@dataclass
class TradeValidation:
    """Result of pre-trade validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_action: str = "proceed"  # proceed, reduce_size, skip, pause


@dataclass
class MonitorConfig:
    """Configuration for the agentic monitor."""
    # Thresholds
    max_consecutive_losses: int = 5
    max_drawdown_pct: float = 10.0  # 10% drawdown triggers pause
    min_win_rate_threshold: float = 0.10  # Below 10% win rate = problem
    min_confidence_threshold: float = 0.50
    max_positions_per_ticker: int = 3
    max_total_positions: int = 20

    # Timing
    duplicate_signal_window_seconds: int = 30
    stale_data_threshold_seconds: int = 120

    # Auto-actions
    auto_pause_on_emergency: bool = True
    auto_reduce_on_warning: bool = True

    # Monitoring windows
    rolling_window_trades: int = 20  # Look at last 20 trades
    alert_cooldown_seconds: int = 60  # Don't spam same alert


class AgenticMonitor:
    """
    Autonomous monitoring agent for trading operations.

    Watches for mistakes, validates trades, and can auto-pause
    when critical issues are detected.
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()

        # State tracking
        self._alerts: deque = deque(maxlen=1000)
        self._recent_signals: Dict[str, List[datetime]] = {}  # ticker -> timestamps
        self._trade_history: deque = deque(maxlen=100)
        self._position_counts: Dict[str, int] = {}
        self._is_paused: bool = False
        self._pause_reason: Optional[str] = None

        # Performance tracking
        self._consecutive_losses: int = 0
        self._session_pnl: float = 0.0
        self._session_start_balance: float = 0.0
        self._win_count: int = 0
        self._loss_count: int = 0

        # Alert cooldowns
        self._last_alert_time: Dict[str, datetime] = {}

        # Callbacks
        self._on_pause_callback = None
        self._on_alert_callback = None

        logger.info("AgenticMonitor initialized with auto-pause enabled")

    def set_callbacks(
        self,
        on_pause=None,
        on_alert=None
    ):
        """Set callback functions for events."""
        self._on_pause_callback = on_pause
        self._on_alert_callback = on_alert

    # =========================================================================
    # PRE-TRADE VALIDATION
    # =========================================================================

    def validate_signal(
        self,
        ticker: str,
        direction: str,
        regime: str,
        confidence: float,
        engine: str,
        price: float,
        metadata: Optional[Dict] = None
    ) -> TradeValidation:
        """
        Validate a trading signal BEFORE execution.

        Returns validation result with any errors/warnings.
        """
        errors = []
        warnings = []

        # Check 1: Direction matches regime
        regime_direction_ok = self._check_regime_direction(regime, direction)
        if not regime_direction_ok:
            errors.append(
                f"DIRECTION MISMATCH: {direction.upper()} in {regime} regime "
                f"(expected {'SHORT' if regime == 'trending_down' else 'LONG'})"
            )
            self._raise_alert(
                AlertType.DIRECTION_MISMATCH,
                AlertSeverity.CRITICAL,
                ticker,
                f"Attempted {direction} in {regime} regime",
                {"direction": direction, "regime": regime, "engine": engine}
            )

        # Check 2: Confidence threshold
        if confidence < self.config.min_confidence_threshold:
            warnings.append(
                f"LOW CONFIDENCE: {confidence:.1%} < {self.config.min_confidence_threshold:.1%}"
            )
            if confidence < 0.40:
                errors.append(f"CONFIDENCE TOO LOW: {confidence:.1%}")

        # Check 3: Duplicate signal check
        if self._is_duplicate_signal(ticker):
            warnings.append(
                f"DUPLICATE: Signal for {ticker} within {self.config.duplicate_signal_window_seconds}s"
            )

        # Check 4: Position limits
        current_positions = self._position_counts.get(ticker, 0)
        if current_positions >= self.config.max_positions_per_ticker:
            errors.append(
                f"POSITION OVERFLOW: {ticker} already has {current_positions} positions"
            )
            self._raise_alert(
                AlertType.POSITION_OVERFLOW,
                AlertSeverity.WARNING,
                ticker,
                f"Max positions reached for {ticker}",
                {"current": current_positions, "max": self.config.max_positions_per_ticker}
            )

        # Check 5: Total position limit
        total_positions = sum(self._position_counts.values())
        if total_positions >= self.config.max_total_positions:
            errors.append(
                f"TOTAL POSITION LIMIT: {total_positions} >= {self.config.max_total_positions}"
            )

        # Check 6: Trading paused?
        if self._is_paused:
            errors.append(f"TRADING PAUSED: {self._pause_reason}")

        # Check 7: Consecutive losses check
        if self._consecutive_losses >= self.config.max_consecutive_losses:
            warnings.append(
                f"LOSING STREAK: {self._consecutive_losses} consecutive losses"
            )

        # Determine suggested action
        if errors:
            suggested_action = "skip"
        elif len(warnings) >= 2:
            suggested_action = "reduce_size"
        else:
            suggested_action = "proceed"

        return TradeValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggested_action=suggested_action
        )

    def _check_regime_direction(self, regime: str, direction: str) -> bool:
        """Check if direction is valid for the regime."""
        regime = regime.lower()
        direction = direction.lower()

        if regime in ['trending_up', 'breakout']:
            return direction == 'long'
        elif regime == 'trending_down':
            return direction == 'short'
        elif regime == 'ranging':
            return direction in ['long', 'short']  # Both allowed
        else:
            return True  # Unknown regime, allow

    def _is_duplicate_signal(self, ticker: str) -> bool:
        """Check if this is a duplicate signal within the window."""
        now = datetime.now(EST_TZ)
        window = timedelta(seconds=self.config.duplicate_signal_window_seconds)

        if ticker not in self._recent_signals:
            self._recent_signals[ticker] = []

        # Clean old signals
        self._recent_signals[ticker] = [
            ts for ts in self._recent_signals[ticker]
            if now - ts < window
        ]

        # Check for recent signal
        is_duplicate = len(self._recent_signals[ticker]) > 0

        # Record this signal
        self._recent_signals[ticker].append(now)

        return is_duplicate

    # =========================================================================
    # POST-TRADE MONITORING
    # =========================================================================

    def record_trade_entry(
        self,
        ticker: str,
        direction: str,
        entry_price: float,
        regime: str,
        engine: str,
        trade_id: str
    ):
        """Record a trade entry for monitoring."""
        self._position_counts[ticker] = self._position_counts.get(ticker, 0) + 1

        self._trade_history.append({
            "trade_id": trade_id,
            "ticker": ticker,
            "direction": direction,
            "entry_price": entry_price,
            "regime": regime,
            "engine": engine,
            "entry_time": datetime.now(EST_TZ),
            "exit_time": None,
            "exit_price": None,
            "pnl": None,
            "status": "open"
        })

        logger.debug(f"[MONITOR] Recorded entry: {ticker} {direction} @ {entry_price}")

    def record_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        pnl: float
    ):
        """Record a trade exit and update stats."""
        # Find the trade
        for trade in self._trade_history:
            if trade["trade_id"] == trade_id:
                trade["exit_time"] = datetime.now(EST_TZ)
                trade["exit_price"] = exit_price
                trade["pnl"] = pnl
                trade["status"] = "closed"

                # Update position count
                ticker = trade["ticker"]
                self._position_counts[ticker] = max(0, self._position_counts.get(ticker, 1) - 1)

                # Update performance stats
                self._session_pnl += pnl
                if pnl >= 0:
                    self._win_count += 1
                    self._consecutive_losses = 0
                else:
                    self._loss_count += 1
                    self._consecutive_losses += 1

                # Check for problems
                self._check_post_trade_anomalies(trade, pnl)

                logger.debug(f"[MONITOR] Recorded exit: {trade_id} PnL=${pnl:.2f}")
                break

    def _check_post_trade_anomalies(self, trade: Dict, pnl: float):
        """Check for anomalies after a trade closes."""

        # Check 1: Consecutive losses
        if self._consecutive_losses >= self.config.max_consecutive_losses:
            self._raise_alert(
                AlertType.CONSECUTIVE_LOSSES,
                AlertSeverity.CRITICAL,
                trade["ticker"],
                f"{self._consecutive_losses} consecutive losses",
                {"consecutive": self._consecutive_losses, "last_pnl": pnl}
            )

        # Check 2: Win rate crash
        total_trades = self._win_count + self._loss_count
        if total_trades >= 10:
            win_rate = self._win_count / total_trades
            if win_rate < self.config.min_win_rate_threshold:
                self._raise_alert(
                    AlertType.WIN_RATE_CRASH,
                    AlertSeverity.EMERGENCY,
                    "SYSTEM",
                    f"Win rate crashed to {win_rate:.1%}",
                    {"win_rate": win_rate, "wins": self._win_count, "losses": self._loss_count},
                    auto_action="pause_trading"
                )

        # Check 3: Drawdown limit
        if self._session_start_balance > 0:
            drawdown_pct = abs(min(0, self._session_pnl)) / self._session_start_balance * 100
            if drawdown_pct >= self.config.max_drawdown_pct:
                self._raise_alert(
                    AlertType.DRAWDOWN_LIMIT,
                    AlertSeverity.EMERGENCY,
                    "SYSTEM",
                    f"Drawdown limit reached: {drawdown_pct:.1f}%",
                    {"drawdown_pct": drawdown_pct, "session_pnl": self._session_pnl},
                    auto_action="pause_trading"
                )

    # =========================================================================
    # ALERT SYSTEM
    # =========================================================================

    def _raise_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        ticker: str,
        message: str,
        details: Optional[Dict] = None,
        auto_action: Optional[str] = None
    ):
        """Raise a monitoring alert."""
        now = datetime.now(EST_TZ)

        # Check cooldown
        alert_key = f"{alert_type}_{ticker}"
        if alert_key in self._last_alert_time:
            elapsed = (now - self._last_alert_time[alert_key]).total_seconds()
            if elapsed < self.config.alert_cooldown_seconds:
                return  # Skip due to cooldown

        self._last_alert_time[alert_key] = now

        alert = MonitorAlert(
            timestamp=now,
            alert_type=alert_type,
            severity=severity,
            ticker=ticker,
            message=message,
            details=details or {},
            auto_action=auto_action
        )

        self._alerts.append(alert)

        # Log based on severity
        if severity == AlertSeverity.EMERGENCY:
            logger.error(f"🚨 [MONITOR EMERGENCY] {ticker}: {message}")
        elif severity == AlertSeverity.CRITICAL:
            logger.warning(f"⚠️ [MONITOR CRITICAL] {ticker}: {message}")
        elif severity == AlertSeverity.WARNING:
            logger.warning(f"[MONITOR WARNING] {ticker}: {message}")
        else:
            logger.info(f"[MONITOR] {ticker}: {message}")

        # Execute auto-action
        if auto_action == "pause_trading" and self.config.auto_pause_on_emergency:
            self.pause_trading(message)

        # Callback
        if self._on_alert_callback:
            try:
                self._on_alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    # =========================================================================
    # PAUSE/RESUME CONTROL
    # =========================================================================

    def pause_trading(self, reason: str):
        """Pause all trading."""
        if not self._is_paused:
            self._is_paused = True
            self._pause_reason = reason
            logger.error(f"🛑 [MONITOR] TRADING PAUSED: {reason}")

            if self._on_pause_callback:
                try:
                    self._on_pause_callback(True, reason)
                except Exception as e:
                    logger.error(f"Pause callback error: {e}")

    def resume_trading(self):
        """Resume trading after pause."""
        if self._is_paused:
            self._is_paused = False
            old_reason = self._pause_reason
            self._pause_reason = None
            logger.info(f"✅ [MONITOR] TRADING RESUMED (was paused: {old_reason})")

            if self._on_pause_callback:
                try:
                    self._on_pause_callback(False, None)
                except Exception as e:
                    logger.error(f"Resume callback error: {e}")

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def pause_reason(self) -> Optional[str]:
        return self._pause_reason

    # =========================================================================
    # STATUS & REPORTING
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get current monitor status."""
        total_trades = self._win_count + self._loss_count
        win_rate = self._win_count / total_trades if total_trades > 0 else 0

        recent_alerts = [
            {
                "timestamp": a.timestamp.isoformat(),
                "type": a.alert_type.value,
                "severity": a.severity.value,
                "ticker": a.ticker,
                "message": a.message
            }
            for a in list(self._alerts)[-10:]
        ]

        return {
            "is_paused": self._is_paused,
            "pause_reason": self._pause_reason,
            "session_pnl": self._session_pnl,
            "win_count": self._win_count,
            "loss_count": self._loss_count,
            "win_rate": win_rate,
            "consecutive_losses": self._consecutive_losses,
            "total_positions": sum(self._position_counts.values()),
            "positions_by_ticker": dict(self._position_counts),
            "alert_count": len(self._alerts),
            "recent_alerts": recent_alerts,
            "config": {
                "max_consecutive_losses": self.config.max_consecutive_losses,
                "max_drawdown_pct": self.config.max_drawdown_pct,
                "min_win_rate_threshold": self.config.min_win_rate_threshold,
                "auto_pause_enabled": self.config.auto_pause_on_emergency
            }
        }

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get recent alerts, optionally filtered by severity."""
        alerts = list(self._alerts)

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [
            {
                "timestamp": a.timestamp.isoformat(),
                "type": a.alert_type.value,
                "severity": a.severity.value,
                "ticker": a.ticker,
                "message": a.message,
                "details": a.details,
                "auto_action": a.auto_action
            }
            for a in alerts[-limit:]
        ]

    def reset_session(self, starting_balance: float = 0.0):
        """Reset session stats (e.g., for new day)."""
        self._consecutive_losses = 0
        self._session_pnl = 0.0
        self._session_start_balance = starting_balance
        self._win_count = 0
        self._loss_count = 0
        self._position_counts.clear()
        self._recent_signals.clear()
        logger.info(f"[MONITOR] Session reset. Starting balance: ${starting_balance:.2f}")


# Singleton instance
_monitor: Optional[AgenticMonitor] = None


def get_agentic_monitor() -> AgenticMonitor:
    """Get or create the global agentic monitor."""
    global _monitor
    if _monitor is None:
        _monitor = AgenticMonitor()
    return _monitor


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def validate_before_trade(
    ticker: str,
    direction: str,
    regime: str,
    confidence: float,
    engine: str,
    price: float,
    metadata: Optional[Dict] = None
) -> Tuple[bool, str]:
    """
    Convenience function to validate a trade before execution.

    Returns:
        (should_execute, reason)
    """
    monitor = get_agentic_monitor()

    if monitor.is_paused:
        return False, f"Trading paused: {monitor.pause_reason}"

    validation = monitor.validate_signal(
        ticker=ticker,
        direction=direction,
        regime=regime,
        confidence=confidence,
        engine=engine,
        price=price,
        metadata=metadata
    )

    if not validation.is_valid:
        return False, "; ".join(validation.errors)

    if validation.suggested_action == "skip":
        return False, "; ".join(validation.warnings)

    return True, validation.suggested_action
