"""
Database Models for Unified Trading Engine

This module contains ORM models unique to the infrastructure layer.
Shared models (User, Signal, Trade, Position, Order) are imported from models.py
to avoid duplicate SQLAlchemy mapper registrations.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum, Index
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
    max_drawdown_pct = Column(Float)  # Maximum drawdown % from peak
    max_open_positions = Column(Integer)  # Maximum concurrent positions
    max_daily_trades = Column(Integer)  # Maximum trades per day
    trade_cooldown_seconds = Column(Integer)  # Minimum seconds between trades
    max_positions_per_symbol = Column(Integer, default=1)  # Maximum positions per instrument

    # Account grouping
    group_id = Column(Integer, ForeignKey("account_groups.id"))
    group_name = Column(String(100))  # "Prop Firm", "Personal", etc. (cached for quick display)
    group_color = Column(String(7))  # Hex color for UI grouping

    # Routing preference
    is_signal_enabled = Column(Boolean, default=True)  # Whether this account receives signals
    signal_priority = Column(Integer, default=0)  # Priority when routing (higher = first)

    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    last_sync = Column(DateTime)

    # Metadata
    extra_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (no back_populates - User.accounts refers to Account model, not TradingAccount)
    user = relationship("User")
    group = relationship("AccountGroup", back_populates="accounts")


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
