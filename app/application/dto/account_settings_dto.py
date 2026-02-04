"""
Account Settings DTOs - Input/Output contracts for account settings use cases.

Handles per-account position sizing and risk management configuration.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class PositionSizingMode(str, Enum):
    """Position sizing calculation method"""
    FIXED = "fixed"  # Fixed lot size
    PERCENT_BALANCE = "percent_balance"  # Percentage of account balance
    PERCENT_EQUITY = "percent_equity"  # Percentage of account equity
    RISK_BASED = "risk_based"  # Based on risk per trade


@dataclass(frozen=True)
class AccountSettingsRequest:
    """Request to update account settings"""
    account_id: int

    # Position sizing
    position_sizing_mode: Optional[PositionSizingMode] = None
    fixed_lot_size: Optional[float] = None  # 0.01 - 100
    percent_of_balance: Optional[float] = None  # 0.1 - 100
    percent_of_equity: Optional[float] = None  # 0.1 - 100
    risk_percent_per_trade: Optional[float] = None  # 0.1 - 10

    # Risk limits
    max_position_size: Optional[float] = None  # >= 0.01
    max_daily_loss: Optional[float] = None  # >= 0
    max_daily_loss_pct: Optional[float] = None  # 0 - 100
    max_drawdown_pct: Optional[float] = None  # 0 - 100
    max_open_positions: Optional[int] = None  # 1 - 100
    max_positions_per_symbol: Optional[int] = None  # 1 - 50 (max positions per instrument)
    max_daily_trades: Optional[int] = None  # 1 - 1000
    trade_cooldown_seconds: Optional[int] = None  # 0 - 3600
    # Default stop loss/take profit in broker-specific units (pips/points/percent)
    # Backend converts to absolute prices using signal's entry price
    default_stop_loss: Optional[float] = None  # Value in units specified by sl_type
    default_take_profit: Optional[float] = None  # Value in units specified by tp_type
    sl_type: Optional[str] = None  # 'pips', 'points', 'percent', or 'price'
    tp_type: Optional[str] = None  # 'pips', 'points', 'percent', or 'price'

    # Grouping
    group_id: Optional[int] = None

    # Routing
    is_signal_enabled: Optional[bool] = None
    signal_priority: Optional[int] = None  # 0 - 100
    auto_confirm: Optional[bool] = None

    # Symbol blocking - list of symbols blocked from trading on this account
    blocked_symbols: Optional[List[str]] = None  # ["XAUUSD", "BTCUSD", ...]


@dataclass(frozen=True)
class AccountSettingsResponse:
    """Response with current account settings"""
    account_id: int

    # Position sizing
    position_sizing_mode: str
    fixed_lot_size: float
    percent_of_balance: float
    percent_of_equity: float
    risk_percent_per_trade: float

    # Risk limits
    max_position_size: Optional[float]
    max_daily_loss: Optional[float]
    max_daily_loss_pct: Optional[float]
    max_drawdown_pct: Optional[float]
    max_open_positions: Optional[int]
    max_positions_per_symbol: Optional[int]
    max_daily_trades: Optional[int]
    trade_cooldown_seconds: Optional[int]
    # Default stop loss/take profit in broker-specific units (pips/points/percent)
    default_stop_loss: Optional[float]
    default_take_profit: Optional[float]
    sl_type: str  # 'pips', 'points', 'percent', or 'price'
    tp_type: str  # 'pips', 'points', 'percent', or 'price'

    # Grouping
    group_id: Optional[int]
    group_name: Optional[str]
    group_color: Optional[str]

    # Routing
    is_signal_enabled: bool
    signal_priority: int
    auto_confirm: bool

    # Symbol blocking
    blocked_symbols: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class GetAccountSettingsRequest:
    """Request to get account settings"""
    account_id: int
    user_id: int  # For ownership verification
