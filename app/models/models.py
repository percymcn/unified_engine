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
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

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

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)  # Nullable for OAuth users
    full_name = Column(String)
    phone = Column(String)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    
    # Enhanced features
    role = Column(String, default="free_user", index=True)  # Will reference Role model
    role_id = Column(Integer, ForeignKey("roles.id"), index=True)
    avatar_url = Column(String)
    timezone = Column(String, default="UTC")
    locale = Column(String, default="en")
    
    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE, index=True)
    stripe_customer_id = Column(String, index=True)
    
    # Multi-tenancy
    primary_organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    
    # OAuth
    oauth_provider = Column(String)  # google, github, microsoft
    oauth_id = Column(String, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    accounts = relationship("Account", back_populates="owner")
    sessions = relationship("UserSession", back_populates="user")
    signals = relationship("Signal", back_populates="user")
    role_obj = relationship("Role", foreign_keys=[role_id], back_populates="users")
    subscription = relationship("UserSubscription", back_populates="user", uselist=False)
    oauth_accounts = relationship("OAuthAccount", back_populates="user")
    organizations = relationship("Organization", secondary="user_organizations", back_populates="members")
    notifications = relationship("Notification", back_populates="user")
    notification_preferences = relationship("NotificationPreference", back_populates="user", uselist=False)

class UserSession(Base):
    __tablename__ = "user_sessions"
    
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
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)  # Multi-tenancy
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
    organization = relationship("Organization", back_populates="accounts")
    trades = relationship("Trade", back_populates="account")
    positions = relationship("Position", back_populates="account")
    orders = relationship("Order", back_populates="account")

class Trade(Base):
    __tablename__ = "trades"
    
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
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    
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

# Import enhanced models (optional - only if they exist)
try:
    from app.models.enhanced_models import (
        Organization, Role, Permission, UserSubscription, OAuthAccount,
        Notification, NotificationPreference, AuditLog, UsageMetric,
        user_organization_table, permission_role_table
    )
except ImportError:
    # Enhanced models not available yet
    pass