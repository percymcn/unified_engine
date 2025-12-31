from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.models import UserStatus, AccountType, OrderType, OrderStatus, SignalSource, BrokerType

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Session Schemas
class UserSession(BaseModel):
    id: int
    user_id: int
    session_token: str
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Account Schemas
class AccountBase(BaseModel):
    account_id: str
    broker: BrokerType
    account_type: AccountType
    currency: str = "USD"
    leverage: int = 100
    is_active: bool = True

class AccountCreate(AccountBase):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    server: Optional[str] = None
    login: Optional[int] = None
    password: Optional[str] = None
    broker_config: Optional[Dict[str, Any]] = None

class AccountUpdate(BaseModel):
    balance: Optional[float] = None
    equity: Optional[float] = None
    margin: Optional[float] = None
    free_margin: Optional[float] = None
    is_active: Optional[bool] = None
    is_connected: Optional[bool] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    broker_config: Optional[Dict[str, Any]] = None

class Account(AccountBase):
    id: int
    user_id: int
    is_connected: bool
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Order Schemas
class OrderBase(BaseModel):
    symbol: str
    type: OrderType
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = None
    magic_number: Optional[int] = None

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: int
    account_id: int
    order_id: str
    broker_order_id: Optional[str] = None
    status: OrderStatus
    filled_volume: float = 0.0
    remaining_volume: Optional[float] = None
    expire_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Trade Schemas
class TradeBase(BaseModel):
    symbol: str
    type: OrderType
    volume: float
    open_price: float
    close_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = None
    magic_number: Optional[int] = None

class TradeCreate(TradeBase):
    pass

class Trade(TradeBase):
    id: int
    account_id: int
    trade_id: str
    broker_trade_id: Optional[str] = None
    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    status: str
    open_time: datetime
    close_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Position Schemas
class PositionBase(BaseModel):
    symbol: str
    type: OrderType
    volume: float
    open_price: float
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = None
    magic_number: Optional[int] = None

class PositionCreate(PositionBase):
    pass

class Position(PositionBase):
    id: int
    account_id: int
    position_id: str
    broker_position_id: Optional[str] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    margin: float = 0.0
    is_active: bool
    open_time: datetime
    close_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Signal Schemas
class SignalBase(BaseModel):
    signal_id: str
    source: SignalSource
    symbol: str
    action: str  # BUY, SELL, CLOSE
    volume: Optional[float] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = None
    target_accounts: Optional[List[int]] = None

class SignalCreate(SignalBase):
    raw_payload: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class Signal(SignalBase):
    id: int
    user_id: Optional[int] = None
    status: str  # pending, processed, failed
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Webhook Schemas
class WebhookLogBase(BaseModel):
    webhook_id: str
    source: str
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    payload: str

class WebhookLogCreate(WebhookLogBase):
    pass

class WebhookLog(WebhookLogBase):
    id: int
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    processed: bool
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Execution Schemas
class ExecutionLogBase(BaseModel):
    signal_id: Optional[str] = None
    account_id: int
    broker: BrokerType
    action: str
    symbol: str
    volume: float
    price: Optional[float] = None

class ExecutionLogCreate(ExecutionLogBase):
    broker_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

class ExecutionLog(ExecutionLogBase):
    id: int
    status: str  # success, failed, timeout
    broker_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Alert Schemas
class AlertBase(BaseModel):
    user_id: int
    account_id: Optional[int] = None
    alert_type: str
    message: str
    severity: str = "info"
    metadata: Optional[Dict[str, Any]] = None

class AlertCreate(AlertBase):
    pass

class Alert(AlertBase):
    id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# System Config Schemas
class SystemConfigBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    is_active: bool = True

class SystemConfigCreate(SystemConfigBase):
    pass

class SystemConfig(SystemConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

# API Response Schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

# Dashboard Schemas
class DashboardStats(BaseModel):
    total_accounts: int
    active_accounts: int
    total_trades: int
    open_positions: int
    total_pnl: float
    today_pnl: float
    active_signals: int
    pending_orders: int

class AccountSummary(BaseModel):
    id: int
    account_id: str
    broker: BrokerType
    account_type: AccountType
    balance: float
    equity: float
    margin: float
    free_margin: float
    is_active: bool
    is_connected: bool
    last_sync: Optional[datetime] = None

class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float

# Webhook Payload Schemas
class TradingViewWebhook(BaseModel):
    ticker: str
    exchange: str
    price: float
    volume: Optional[float] = None
    text: str
    timestamp: Optional[datetime] = None

class TrailHackerWebhook(BaseModel):
    symbol: str
    action: str
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: Optional[datetime] = None

# Broker Request/Response Schemas
class BrokerRequest(BaseModel):
    action: str
    symbol: str
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = None
    magic_number: Optional[int] = None

class BrokerResponse(BaseModel):
    success: bool
    order_id: Optional[str] = None
    trade_id: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None