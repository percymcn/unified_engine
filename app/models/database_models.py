"""
Comprehensive Database Models for Unified Trading Engine
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    api_key = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    accounts = relationship("TradingAccount", back_populates="user", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="user", cascade="all, delete-orphan")
    webhooks = relationship("WebhookConfig", back_populates="user", cascade="all, delete-orphan")


class TradingAccount(Base):
    __tablename__ = "trading_accounts"

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

    # Account Info
    currency = Column(String(10), default="USD")
    leverage = Column(Float, default=1.0)
    balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    margin = Column(Float, default=0.0)
    free_margin = Column(Float, default=0.0)
    margin_level = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    last_sync = Column(DateTime)

    # Metadata
    extra_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="accounts")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="account", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="account", cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)

    # Position Details
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)

    # Risk Management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    trailing_stop = Column(Float)

    # P&L
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)

    # Status
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN)

    # Broker Info
    broker_position_id = Column(String(255), unique=True, index=True)
    broker_data = Column(JSON)

    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("TradingAccount", back_populates="positions")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)

    # Order Details
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, default=0.0)

    # Pricing
    price = Column(Float)  # Limit/Stop price
    trigger_price = Column(Float)  # For stop orders
    average_fill_price = Column(Float)

    # Risk Management
    stop_loss = Column(Float)
    take_profit = Column(Float)

    # Status
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)

    # Broker Info
    broker_order_id = Column(String(255), unique=True, index=True)
    broker_data = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Error info
    error_message = Column(Text)

    # Relationships
    account = relationship("TradingAccount", back_populates="orders")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)

    # Trade Details
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)

    # P&L
    gross_pnl = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)

    # Broker Info
    broker_trade_id = Column(String(255), unique=True, index=True)
    broker_data = Column(JSON)

    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)

    # Relationships
    account = relationship("TradingAccount", back_populates="trades")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Signal Source
    source = Column(String(100), nullable=False, index=True)  # tradingview, trailhacker, custom
    source_id = Column(String(255))

    # Signal Details
    symbol = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # BUY, SELL, CLOSE, MODIFY
    quantity = Column(Float)
    price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)

    # Routing
    target_accounts = Column(JSON)  # List of account IDs
    target_broker = Column(Enum(BrokerType))

    # Status
    status = Column(Enum(SignalStatus), default=SignalStatus.RECEIVED)

    # Execution Results
    execution_results = Column(JSON)
    error_message = Column(Text)

    # Raw Data
    raw_payload = Column(JSON)

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    executed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="signals")


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Config
    name = Column(String(255), nullable=False)
    webhook_key = Column(String(255), unique=True, index=True, nullable=False)
    source = Column(String(100), nullable=False)  # tradingview, trailhacker, custom

    # Routing Rules
    default_account_id = Column(Integer, ForeignKey("trading_accounts.id"))
    routing_rules = Column(JSON)  # Complex routing logic

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


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text)
    value_type = Column(String(50))  # string, int, float, bool, json
    description = Column(Text)
    is_encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
