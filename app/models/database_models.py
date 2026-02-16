"""
Database Models for Unified Trading Engine

This module contains ORM models unique to the infrastructure layer.
Shared models (User, Signal, Trade, Position, Order) are imported from models.py
to avoid duplicate SQLAlchemy mapper registrations.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum, Index, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

# Import Base from the centralized database module
from app.db.database import Base

# Import shared models from models.py to avoid duplicate mapper registrations
from app.models.models import User, Signal, Trade, Position, Order


# Enums unique to this module
class BrokerType(enum.Enum):
    TRADELOCKER = "tradelocker"
    TRADOVATE = "tradovate"
    PROJECTX = "projectx"
    TOPSTEP = "topstep"
    TRUFOREX = "truforex"
    MT4 = "mt4"
    MT5 = "mt5"


class AccountType(enum.Enum):
    LIVE = "live"
    DEMO = "demo"
    FUNDED = "funded"
    EVALUATION = "evaluation"


class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CLOSING = "closing"


class SignalStatus(enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    EXECUTED = "executed"
    FAILED = "failed"
    IGNORED = "ignored"


class AccountGroup(Base):
    """Account grouping for organizing trading accounts"""
    __tablename__ = "account_groups"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # "Prop Firm Accounts", "Personal"
    description = Column(String(500))
    color = Column(String(7), default="#6366f1")  # Hex color for UI
    icon = Column(String(50), default="folder")  # Icon name for UI
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    accounts = relationship("TradingAccount", back_populates="group")


class TradingAccount(Base):
    __tablename__ = "trading_accounts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    broker = Column(Enum(BrokerType), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    account_number = Column(String(100), nullable=False)
    account_name = Column(String(255))

    # Credentials (encrypted)
    api_key = Column(String(500))
    api_secret = Column(String(500))
    access_token = Column(Text)
    refresh_token = Column(Text)

    # OAuth token management
    token_expires_at = Column(DateTime)
    oauth_environment = Column(String(10))  # "demo" or "live"

    # Account Info
    currency = Column(String(10), default="USD")
    leverage = Column(Float, default=1.0)
    balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    margin = Column(Float, default=0.0)
    free_margin = Column(Float, default=0.0)
    margin_level = Column(Float, default=0.0)

    # Position sizing settings
    position_sizing_mode = Column(String(20), default="fixed")  # fixed, percent_balance, percent_equity, risk_based
    fixed_lot_size = Column(Float, default=0.01)
    percent_of_balance = Column(Float, default=1.0)
    percent_of_equity = Column(Float, default=1.0)
    risk_percent_per_trade = Column(Float, default=1.0)

    # Risk limits
    max_position_size = Column(Float)  # Maximum lots per position
    max_daily_loss = Column(Float)  # Maximum daily loss in account currency
    max_daily_loss_pct = Column(Float)  # Maximum daily loss as % of balance
    max_daily_profit = Column(Float)  # Maximum daily profit target in account currency (halt when reached)
    max_daily_profit_pct = Column(Float)  # Maximum daily profit target as % of balance (halt when reached)
    max_drawdown_pct = Column(Float)  # Maximum drawdown % from peak
    max_open_positions = Column(Integer)  # Maximum concurrent positions
    max_daily_trades = Column(Integer)  # Maximum trades per day
    trade_cooldown_seconds = Column(Integer)  # Minimum seconds between trades
    max_positions_per_symbol = Column(Integer, default=1)  # Maximum positions per instrument
    # Default stop loss/take profit in broker-specific units (pips/points/percent)
    # NOTE: These are stored in broker-specific units because they cannot be converted
    # to absolute prices without an entry price. When used with a signal, the backend
    # should convert them using the signal's entry price. Backend conversion is not
    # yet implemented, so these are stored as metadata for future enhancement.
    default_stop_loss = Column(Float, nullable=True)  # Default stop loss in broker-specific units
    default_take_profit = Column(Float, nullable=True)  # Default take profit in broker-specific units
    trailing_stop_pips = Column(Float, nullable=True)  # Trailing stop distance in pips
    sl_type = Column(String(20), nullable=True, default='pips')  # 'pips' or 'price' - how SL is specified
    tp_type = Column(String(20), nullable=True, default='pips')  # 'pips' or 'price' - how TP is specified

    # Partial TP and platform-managed SL/TP
    partial_tp_enabled = Column(Boolean, default=False)  # Enable partial take profit feature
    partial_tp_config = Column(JSON, nullable=True)  # Configuration: {levels: [{ratio: 1, close_percent: 50}, ...]}
    platform_managed_sl_tp = Column(Boolean, default=False)  # TradeFlow manages SL/TP instead of broker

    # Account grouping
    group_id = Column(Integer, ForeignKey("account_groups.id"))
    group_name = Column(String(100))  # "Prop Firm", "Personal", etc. (cached for quick display)
    group_color = Column(String(7))  # Hex color for UI grouping

    # Routing preference
    is_signal_enabled = Column(Boolean, default=True)  # Whether this account receives signals
    signal_priority = Column(Integer, default=0)  # Priority when routing (higher = first)
    auto_confirm = Column(Boolean, default=True)  # Auto-execute trades without manual confirmation

    # Symbol blocking - list of symbols blocked from trading on this account
    blocked_symbols = Column(JSON, nullable=True, default=list)  # ["XAUUSD", "BTCUSD", ...]

    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    last_sync = Column(DateTime)

    # Per-broker webhook key (Patch 1.2.1)
    webhook_key = Column(Text, unique=True, nullable=True, index=True)

    # Broker account selection (for multi-account brokers)
    enabled_broker_account_ids = Column(JSON, nullable=True)  # List of enabled broker account IDs
    default_broker_account_id = Column(String(100), nullable=True)  # Default broker account ID
    discovered_accounts_cache = Column(JSON, nullable=True)  # Cached discovered accounts metadata

    # Metadata
    extra_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="accounts")
    group = relationship("AccountGroup", back_populates="accounts")
    trades = relationship("Trade", back_populates="account")
    positions = relationship("Position", back_populates="account")
    orders = relationship("Order", back_populates="account")
    strategies = relationship("AccountStrategy", back_populates="account")
    alerts = relationship("Alert", backref="account")
    execution_logs = relationship("ExecutionLog", backref="account")
    broker_symbol_format = relationship("BrokerSymbolFormat", back_populates="account", uselist=False)
    contract_positions = relationship("UserContractPosition", back_populates="account")
    position_trades = relationship("PositionTrade", back_populates="account")
    symbol_settings = relationship("SymbolSettings", back_populates="account", cascade="all, delete-orphan")


class SymbolSettings(Base):
    """
    Symbol-specific trading settings per account.

    Allows users to configure SL/TP defaults per symbol, e.g.:
    - XAUUSD: SL=200 pips, TP=400 pips
    - BTCUSD: SL=500 points, TP=1000 points
    - NAS100: SL=50 points, TP=100 points
    """
    __tablename__ = "symbol_settings"
    __table_args__ = (
        Index('ix_symbol_settings_account_symbol', 'account_id', 'symbol', unique=True),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)  # e.g., "XAUUSD", "BTCUSD", "NAS100"

    # SL/TP settings for this symbol
    default_stop_loss = Column(Float, nullable=True)  # Value in units specified by sl_type
    default_take_profit = Column(Float, nullable=True)  # Value in units specified by tp_type
    sl_type = Column(String(20), nullable=True, default='pips')  # 'pips', 'points', 'percent', 'price'
    tp_type = Column(String(20), nullable=True, default='pips')  # 'pips', 'points', 'percent', 'price'

    # Optional: override position sizing for this symbol
    position_size_override = Column(Float, nullable=True)  # Override lot size for this symbol
    max_positions = Column(Integer, nullable=True)  # Max positions for this symbol (overrides account level)

    # Metadata
    notes = Column(Text, nullable=True)  # User notes for this symbol config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("TradingAccount", back_populates="symbol_settings")


class PositionTradeStatus(enum.Enum):
    """Status of a tracked position for partial TP"""
    OPEN = "open"
    PARTIAL = "partial"  # Partially closed
    CLOSED = "closed"


class PositionTrade(Base):
    """
    Tracks open positions with partial TP and platform-managed SL/TP.

    This table is used for:
    - Monitoring positions for partial take profit execution
    - Platform-managed SL/TP (TradeFlow triggers close instead of broker)
    - Trailing stop management when broker doesn't support it natively
    """
    __tablename__ = "position_trades"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('trading_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    broker_position_id = Column(String(100), nullable=True, index=True)  # Broker's position ID
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)  # 'buy' or 'sell'
    entry_price = Column(Float, nullable=False)
    initial_volume = Column(Float, nullable=False)
    current_volume = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)  # Final TP level

    # Partial TP configuration
    partial_tp_levels = Column(JSON, nullable=True)  # Array of {level: float, close_percent: float, triggered: bool}
    executed_tp_levels = Column(JSON, default=list)  # Indices of already executed TP levels

    # Trailing stop
    trailing_stop_distance = Column(Float, nullable=True)  # Distance in pips/points
    current_trailing_sl = Column(Float, nullable=True)  # Current trailing SL price

    # Status
    status = Column(String(20), default='open', nullable=False, index=True)  # open, partial, closed

    # Signal tracking
    webhook_id = Column(String(100), nullable=True)
    signal_id = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationship
    account = relationship("TradingAccount", back_populates="position_trades")


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Config
    name = Column(String(255), nullable=False)
    webhook_key = Column(String(255), unique=True, index=True, nullable=False)
    source = Column(String(100), nullable=False)  # tradingview, trailhacker, custom

    # Routing Configuration
    routing_strategy = Column(String(30), default="default_only")  # all_accounts, specific_accounts, rules_based, default_only
    default_account_id = Column(Integer, ForeignKey("trading_accounts.id"))
    specific_account_ids = Column(JSON)  # List of account IDs for "specific_accounts" strategy
    routing_rules = Column(JSON)  # Complex routing logic for "rules_based" strategy

    # Filters
    symbol_filter = Column(JSON)  # Which symbols to accept
    action_filter = Column(JSON)  # Which actions to accept

    # Status
    is_active = Column(Boolean, default=True)

    # Stats
    total_signals = Column(Integer, default=0)
    successful_signals = Column(Integer, default=0)
    failed_signals = Column(Integer, default=0)
    last_signal_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="webhooks")


class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)

    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20))  # daily, weekly, monthly

    # Trading Stats
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    # P&L
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)

    # Risk Metrics
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    profit_factor = Column(Float)

    # Account Metrics
    starting_balance = Column(Float, default=0.0)
    ending_balance = Column(Float, default=0.0)
    peak_balance = Column(Float, default=0.0)

    # Created
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Action Details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100))  # account, order, position, etc.
    resource_id = Column(String(255))

    # Details
    description = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(String(500))

    # Data
    request_data = Column(JSON)
    response_data = Column(JSON)

    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class RejectedSignalReason(enum.Enum):
    """Reasons why a signal was rejected by risk management"""
    DAILY_LIMIT = "daily_limit"
    CONCURRENT_LIMIT = "concurrent_limit"
    SYMBOL_LIMIT = "symbol_limit"
    COOLDOWN = "cooldown"
    DAILY_LOSS = "daily_loss"
    DRAWDOWN = "drawdown"
    RISK_REWARD = "risk_reward"
    DISABLED = "disabled"
    DUPLICATE_ENTRY = "duplicate_entry"  # Position already open for symbol in same direction
    TRIAL_EXPIRED = "trial_expired"  # Free trial has ended (50 trades or 7 days)


class RejectedSignal(Base):
    """Log of signals that were rejected by risk management"""
    __tablename__ = "rejected_signals"
    __table_args__ = (
        Index('ix_rejected_signals_user_date', 'user_id', 'created_at'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), index=True)

    # Signal details
    symbol = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    quantity = Column(Float)
    source = Column(String(50))  # tradingview, trailhacker, etc.

    # Rejection info
    reason = Column(Enum(RejectedSignalReason), nullable=False)
    reason_detail = Column(String(500))  # Human-readable explanation
    limit_value = Column(Float)  # The limit that was hit
    current_value = Column(Float)  # The current value at rejection time

    # Metadata
    webhook_config_id = Column(Integer, ForeignKey("webhook_configs.id"))
    original_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")
    account = relationship("TradingAccount")


class Credential(Base):
    """
    Secure credential storage model.

    Stores encrypted credentials for broker APIs, databases, and external services.
    The encrypted_data column contains Fernet-encrypted JSON.
    """
    __tablename__ = "credentials"

    id = Column(String(36), primary_key=True, index=True)  # UUID string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # api_key, password, certificate, token, oauth
    service = Column(String(50), nullable=False, index=True)  # mt4, mt5, tradelocker, tradovate, projectx, etc.
    encrypted_data = Column(Text, nullable=False)  # Fernet encrypted JSON
    description = Column(Text, nullable=True)

    # Lifecycle tracking
    expires_at = Column(DateTime(timezone=True), nullable=True)
    rotation_days = Column(Integer, nullable=True, default=90)
    last_rotated = Column(DateTime(timezone=True), nullable=True)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="credentials")

    __table_args__ = (
        Index('ix_credentials_user_service', 'user_id', 'service'),
        {'extend_existing': True}
    )


class DailyPnL(Base):
    """Daily profit/loss tracking per account"""
    __tablename__ = "daily_pnl"
    __table_args__ = (
        Index('ix_daily_pnl_account_date', 'account_id', 'date', unique=True),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # P&L tracking
    starting_balance = Column(Float, nullable=False)  # Balance at start of day
    current_balance = Column(Float)  # Current balance (updated on sync)
    realized_pnl = Column(Float, default=0.0)  # Realized P&L from closed trades
    unrealized_pnl = Column(Float, default=0.0)  # Unrealized P&L from open positions
    total_pnl = Column(Float, default=0.0)  # realized + unrealized
    pnl_percent = Column(Float, default=0.0)  # total_pnl / starting_balance * 100

    # Trade stats
    trades_count = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)

    # Status
    is_trading_halted = Column(Boolean, default=False)  # True if daily loss limit hit
    halt_reason = Column(String(100))  # Reason for halt
    halted_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("TradingAccount")


class DailyCounter(Base):
    """Daily trade counters per account for risk management"""
    __tablename__ = "daily_counters"
    __table_args__ = (
        Index('ix_daily_counters_account_id', 'account_id'),
        Index('ix_daily_counters_date', 'date'),
        Index('ix_daily_counters_account_date', 'account_id', 'date', unique=True),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id", ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)

    # Counters
    signals_received = Column(Integer, nullable=False, default=0, server_default='0')
    trades_executed = Column(Integer, nullable=False, default=0, server_default='0')
    trades_rejected = Column(Integer, nullable=False, default=0, server_default='0')
    last_trade_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=sa_text('now()'))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=sa_text('now()'))

    # Relationships
    account = relationship("TradingAccount")


class AccountEquityHistory(Base):
    """Equity snapshots for drawdown calculation"""
    __tablename__ = "account_equity_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False, index=True)

    # Equity snapshot
    equity = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    peak_equity = Column(Float, nullable=False)  # Highest equity seen
    drawdown = Column(Float, default=0.0)  # Current drawdown from peak (absolute)
    drawdown_pct = Column(Float, default=0.0)  # Drawdown as percentage

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    account = relationship("TradingAccount")


class MomentumSettings(Base):
    """User-level momentum guard configuration for Signal Intelligence Layer"""
    __tablename__ = "momentum_settings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Momentum guard settings
    warn_at = Column(Integer, nullable=False, default=6)  # Threshold for warning modal
    auto_breakeven = Column(Boolean, nullable=False, default=False)  # Auto move SL to entry on warning
    pause_on_chop = Column(Boolean, nullable=False, default=True)  # Pause new entries when choppy

    # Exposure limits
    max_exposure = Column(Float, nullable=False, default=5000.0)  # Max dollar exposure
    auto_pause_on_exposure = Column(Boolean, nullable=False, default=True)  # Auto-pause when limit hit

    # Hedge settings
    allow_hedge = Column(Boolean, nullable=False, default=False)  # Allow hedging on momentum warning

    # Position P&L check settings (warn when trading against profitable positions)
    check_position_pnl = Column(Boolean, nullable=False, default=True)  # Enable P&L-based momentum check
    profit_pnl_threshold = Column(Float, nullable=False, default=500.0)  # Warn if opposite signal and positions in $X+ profit
    block_pnl_signals = Column(Boolean, nullable=False, default=False)  # Block signals (vs just warn) when trading against profit

    # Staleness settings
    staleness_enabled = Column(Boolean, nullable=False, default=True)  # Enable staleness check
    staleness_seconds = Column(Integer, nullable=False, default=5)  # Max age in seconds
    force_old_signals = Column(Boolean, nullable=False, default=False)  # Allow old signals anyway

    # Discard bin settings
    discard_flush_interval = Column(String(10), nullable=False, default="24h")  # 1h, 24h, 30d

    # Trading Session settings - control when webhooks are active
    trading_session_enabled = Column(Boolean, nullable=False, default=False)  # Enable trading session restriction
    trading_session_start = Column(String(5), nullable=True, default="09:30")  # Start time HH:MM (24h format)
    trading_session_end = Column(String(5), nullable=True, default="16:00")  # End time HH:MM (24h format)
    trading_session_timezone = Column(String(50), nullable=True, default="America/New_York")  # IANA timezone
    trading_session_days = Column(JSON, nullable=True, default=[1, 2, 3, 4, 5])  # Days of week: 1=Mon, 7=Sun

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")


class SignalCounter(Base):
    """Per-session signal momentum tracking for Signal Intelligence Layer"""
    __tablename__ = "signal_counters"
    __table_args__ = {'extend_existing': True}

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, primary_key=True)
    session_key = Column(String(255), nullable=False, primary_key=True)  # user_id + symbol + strategy_id

    # Momentum tracking
    current_bias = Column(String(10), nullable=False, default="none")  # 'buy', 'sell', 'none'
    opposite_momentum = Column(Integer, nullable=False, default=0)  # Count of opposite signals
    last_signal_ts = Column(DateTime(timezone=True), nullable=True)  # Timestamp of last signal

    # Pattern tracking
    last8_pattern = Column(String(16), nullable=True)  # Compact string like 'BBSBSBSB' for chop detection
    chop_mode = Column(Boolean, nullable=False, default=False)  # True if market is choppy

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")


class ProvisioningJobStatus(enum.Enum):
    """Status of MetaApi provisioning job"""
    PENDING = "pending"
    CREATING = "creating"
    DEPLOYING = "deploying"
    CONNECTING = "connecting"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProvisioningJob(Base):
    """Track async MetaApi account provisioning jobs"""
    __tablename__ = "provisioning_jobs"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    trading_account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=True, index=True)

    # Job metadata
    platform = Column(String(10), nullable=False)  # "mt4" or "mt5"
    login = Column(String(50), nullable=False)
    server = Column(String(255), nullable=False)
    account_name = Column(String(255), nullable=True)

    # Status tracking
    status = Column(Enum(ProvisioningJobStatus), default=ProvisioningJobStatus.PENDING, nullable=False, index=True)
    status_message = Column(Text, nullable=True)
    progress_percent = Column(Integer, default=0)

    # Result
    metaapi_account_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    trading_account = relationship("TradingAccount")


class DiscardBin(Base):
    """Audit trail for discarded signals"""
    __tablename__ = "discard_bin"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Signal metadata
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason = Column(String(50), nullable=False, index=True)  # 'stale', 'momentum', 'exposure', etc.
    age_ms = Column(Integer, nullable=True)  # Signal age in milliseconds

    # Signal data (stored as JSON for audit)
    raw_signal_json = Column(JSON, nullable=True)
    normalized_signal_json = Column(JSON, nullable=True)

    # Quick lookup fields
    broker_target = Column(String(50), nullable=True)
    symbol = Column(String(50), nullable=True)
    side = Column(String(10), nullable=True)  # 'buy', 'sell'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
