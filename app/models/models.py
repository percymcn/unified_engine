from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PREMIUM_USER = "premium_user"
    FREE_USER = "free_user"

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"

class AccountType(str, enum.Enum):
    LIVE = "live"
    DEMO = "demo"
    EVALUATION = "evaluation"

class OrderType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class SignalSource(str, enum.Enum):
    TRADINGVIEW = "tradingview"
    TRAILHACKER = "trailhacker"
    MANUAL = "manual"
    API = "api"

class BrokerType(str, enum.Enum):
    TRADELOCKER = "tradelocker"
    TOPSTEP = "topstep"
    TRUFOREX = "truforex"
    MT4 = "mt4"
    MT5 = "mt5"
    TRADOVATE = "tradovate"
    PROJECTX = "projectx"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)  # Nullable for OAuth users
    full_name = Column(String)
    phone = Column(String)
    avatar_url = Column(String(500))  # User profile avatar URL
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Subscription fields
    stripe_customer_id = Column(String, index=True)
    subscription_tier = Column(String, default="free")  # free, pro
    subscription_status = Column(String, default="active")  # active, past_due, canceled
    subscription_ends_at = Column(DateTime(timezone=True))

    # Trial fields
    trial_trade_count = Column(Integer, default=0)  # Trades used during trial
    trial_started_at = Column(DateTime(timezone=True))  # When trial began
    trial_ended_at = Column(DateTime(timezone=True))  # When trial expired
    trial_status = Column(String(20), default="pending")  # pending, active, expired

    # Global risk settings (defaults for all accounts)
    default_max_daily_trades = Column(Integer)  # Default max trades per day
    default_max_open_positions = Column(Integer)  # Default max concurrent positions
    default_max_daily_loss = Column(Float)  # Default max daily loss $
    default_max_daily_loss_pct = Column(Float)  # Default max daily loss %
    default_max_drawdown_pct = Column(Float)  # Default max drawdown %
    default_trade_cooldown_seconds = Column(Integer)  # Default cooldown

    # Global position sizing defaults
    default_position_sizing_mode = Column(String(20), default="fixed")
    default_fixed_lot_size = Column(Float, default=0.01)
    default_risk_percent_per_trade = Column(Float, default=1.0)

    # Global risk enforcement toggle
    risk_management_enabled = Column(Boolean, default=True)

    # Signal deduplication settings
    enable_deduplication = Column(Boolean, default=True)  # Prevent duplicate entry signals
    deduplication_scope = Column(String(20), default="per_account")  # per_account, global

    # User preferences
    timezone = Column(String(50), default="UTC")
    notification_preferences = Column(JSON, default=lambda: {
        "trade_alerts": True,
        "error_notifications": True,
        "daily_summary": False,
        "email_notifications": True
    })

    # Relationships
    accounts = relationship("Account", back_populates="owner")
    sessions = relationship("UserSession", back_populates="user")
    signals = relationship("Signal", back_populates="user")
    # Relationships for database_models.py classes
    webhooks = relationship("WebhookConfig", back_populates="user")
    credentials = relationship("Credential", back_populates="user")

class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String)
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, index=True)  # Multi-tenancy (FK disabled for now)
    account_id = Column(String, unique=True, index=True, nullable=False)
    broker = Column(SQLEnum(BrokerType), nullable=False)
    account_type = Column(SQLEnum(AccountType), nullable=False)
    currency = Column(String, default="USD")
    balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    margin = Column(Float, default=0.0)
    free_margin = Column(Float, default=0.0)
    leverage = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    api_key = Column(String)  # Encrypted
    api_secret = Column(String)  # Encrypted
    server = Column(String)
    login = Column(Integer)
    password = Column(String)  # Encrypted
    broker_config = Column(JSON)  # Store broker-specific config
    last_sync = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="accounts")
    # organization = relationship("Organization", back_populates="accounts")  # Disabled
    trades = relationship("Trade", back_populates="account")
    positions = relationship("Position", back_populates="account")
    orders = relationship("Order", back_populates="account")

class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    trade_id = Column(String, unique=True, index=True, nullable=False)
    broker_trade_id = Column(String, index=True)  # Original broker trade ID
    symbol = Column(String, nullable=False)
    type = Column(SQLEnum(OrderType), nullable=False)
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    status = Column(String, default="open")
    open_time = Column(DateTime(timezone=True), server_default=func.now())
    close_time = Column(DateTime(timezone=True))
    comment = Column(Text)
    magic_number = Column(Integer)
    broker_data = Column(JSON)  # Store broker-specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="trades")

class Position(Base):
    __tablename__ = "positions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    position_id = Column(String, unique=True, index=True, nullable=False)
    broker_position_id = Column(String, index=True)  # Original broker position ID
    symbol = Column(String, nullable=False)
    type = Column(SQLEnum(OrderType), nullable=False)
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    current_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    margin = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    open_time = Column(DateTime(timezone=True), server_default=func.now())
    close_time = Column(DateTime(timezone=True))
    comment = Column(Text)
    magic_number = Column(Integer)
    broker_data = Column(JSON)  # Store broker-specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="positions")

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    order_id = Column(String, unique=True, index=True, nullable=False)
    broker_order_id = Column(String, index=True)  # Original broker order ID
    symbol = Column(String, nullable=False)
    type = Column(SQLEnum(OrderType), nullable=False)
    volume = Column(Float, nullable=False)
    price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    filled_volume = Column(Float, default=0.0)
    remaining_volume = Column(Float)
    expire_time = Column(DateTime(timezone=True))
    comment = Column(Text)
    magic_number = Column(Integer)
    broker_data = Column(JSON)  # Store broker-specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="orders")

class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    source = Column(SQLEnum(SignalSource), nullable=False)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)  # BUY, SELL, CLOSE
    volume = Column(Float)
    price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    comment = Column(Text)
    status = Column(String, default="pending")  # pending, processed, failed
    target_accounts = Column(JSON)  # List of target account IDs
    processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    raw_payload = Column(JSON)  # Original webhook payload
    signal_data = Column(JSON)  # Additional signal metadata
    # Strategy tracking fields
    strategy_id = Column(String, index=True)  # Strategy identifier
    strategy_version = Column(String)  # Strategy version
    strategy_name = Column(String)  # Human-readable strategy name
    strategy_source = Column(String)  # tradingview|inhouse|manual
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="signals")

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, nullable=False)
    source_ip = Column(String)
    user_agent = Column(Text)
    payload = Column(Text, nullable=False)
    response_status = Column(Integer)
    response_body = Column(Text)
    processed = Column(Boolean, default=False)
    error_message = Column(Text)
    processing_time_ms = Column(Integer)  # Processing time in milliseconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, ForeignKey("signals.signal_id"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    broker = Column(SQLEnum(BrokerType), nullable=False)
    action = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    volume = Column(Float, nullable=False)
    price = Column(Float)
    status = Column(String, nullable=False)  # success, failed, timeout
    broker_response = Column(JSON)
    error_message = Column(Text)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemConfig(Base):
    __tablename__ = "system_config"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    alert_type = Column(String, nullable=False)  # margin_call, stop_out, etc.
    message = Column(Text, nullable=False)
    severity = Column(String, default="info")  # info, warning, error, critical
    is_read = Column(Boolean, default=False)
    alert_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True))

class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String, unique=True, index=True, nullable=False)  # Hashed API key
    name = Column(String, nullable=False)  # User-friendly name
    permissions = Column(JSON)  # List of permissions/scopes
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))  # Optional expiration
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="api_keys")

class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, unique=True, index=True, nullable=False)
    strategy_name = Column(String, nullable=False)
    strategy_version = Column(String, nullable=False, default="1.0.0")
    strategy_source = Column(String, nullable=False)  # tradingview, inhouse, manual
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    parameters = Column(JSON)  # Strategy-specific parameters
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AccountStrategy(Base):
    __tablename__ = "account_strategies"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    is_enabled = Column(Boolean, default=False)
    parameters = Column(JSON)  # Account-specific strategy parameters
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", backref="strategies")
    strategy = relationship("Strategy", backref="accounts")


class SymbolAlias(Base):
    """
    Symbol alias mapping for TradingView to broker symbol resolution.

    Stores user-defined and auto-detected symbol mappings to handle
    variations like US30 -> US30.pro (TradeLocker) or US30 -> YM (Tradovate).
    """
    __tablename__ = "symbol_aliases"
    __table_args__ = (
        # Unique constraint: one mapping per user/source/broker combination
        {'extend_existing': True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_symbol = Column(String(50), nullable=False, index=True)  # TradingView symbol
    broker_type = Column(String(50), nullable=False, index=True)  # e.g., "tradelocker"
    target_symbol = Column(String(50), nullable=False)  # Broker's format
    is_auto_detected = Column(Boolean, default=False)  # True if system-generated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="symbol_aliases")


class BrokerSymbolFormat(Base):
    """
    Stores detected symbol format patterns per account.

    Auto-detected during connection testing to enable intelligent
    symbol resolution without manual configuration.
    """
    __tablename__ = "broker_symbol_formats"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, unique=True, index=True)
    detected_patterns = Column(JSON)  # {"suffix": ".pro", "prefix": "", "case": "upper", "confidence": 0.95}
    sample_symbols = Column(JSON)     # ["EURUSD.pro", "GBPUSD.pro", "US30.pro"] - first 20 symbols
    common_symbols_map = Column(JSON) # {"EURUSD": "EURUSD.pro", "US30": "US30.pro"} - mapped common symbols
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    account = relationship("Account", backref="symbol_format")


class FuturesContract(Base):
    """
    Futures contract tracking for expiration and rollover management.

    Stores contract specifications including expiration dates and
    relationships between contract months for TopStep/ProjectX brokers.
    """
    __tablename__ = "futures_contracts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    symbol_root = Column(String(10), nullable=False, index=True)  # "NQ", "ES", "CL"
    contract_code = Column(String(20), nullable=False, unique=True, index=True)  # "NQH25"
    month_code = Column(String(1), nullable=False)  # "H" (March)
    year = Column(Integer, nullable=False)  # 2025
    expiration_date = Column(DateTime(timezone=True), nullable=False)
    last_trading_day = Column(DateTime(timezone=True), nullable=False)
    rollover_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    next_contract = Column(String(20))  # "NQM25" (next quarter)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserContractPosition(Base):
    """
    Tracks which futures contracts a user is trading per account.

    Used for sending expiration notifications and rollover suggestions.
    """
    __tablename__ = "user_contract_positions"
    __table_args__ = (
        # Unique constraint: one position per user/account/contract
        {'extend_existing': True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    contract_code = Column(String(20), nullable=False, index=True)  # "NQH25"
    symbol_root = Column(String(10), nullable=False)  # "NQ"
    last_traded_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="contract_positions")
    account = relationship("Account", backref="contract_positions")


# Enhanced models import disabled - causes User relationship conflicts
# These models require database schema updates before use
# try:
#     from app.models.enhanced_models import (
#         Organization, Role, Permission, UserSubscription, OAuthAccount,
#         Notification, NotificationPreference, AuditLog, UsageMetric,
#         user_organization_table, permission_role_table
#     )
# except ImportError:
#     pass