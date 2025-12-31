"""
Pydantic Schemas for API Request/Response Validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class BrokerType(str, Enum):
    TRADELOCKER = "tradelocker"
    TRADOVATE = "tradovate"
    PROJECTX = "projectx"
    TOPSTEP = "topstep"
    TRUFOREX = "truforex"
    MT4 = "mt4"
    MT5 = "mt5"


class AccountType(str, Enum):
    LIVE = "live"
    DEMO = "demo"
    FUNDED = "funded"
    EVALUATION = "evaluation"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SignalAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    MODIFY = "modify"


# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    api_key: Optional[str]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str]
    token_type: str = "bearer"
    expires_in: int


# Trading Account Schemas
class TradingAccountCreate(BaseModel):
    broker: BrokerType
    account_type: AccountType
    account_number: str
    account_name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    currency: str = "USD"
    leverage: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


class TradingAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    is_active: Optional[bool] = None
    leverage: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class TradingAccountResponse(BaseModel):
    id: int
    user_id: int
    broker: BrokerType
    account_type: AccountType
    account_number: str
    account_name: Optional[str]
    currency: str
    leverage: float
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    is_active: bool
    is_connected: bool
    last_sync: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Position Schemas
class PositionResponse(BaseModel):
    id: int
    account_id: int
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    current_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    unrealized_pnl: float
    realized_pnl: float
    commission: float
    swap: float
    status: str
    broker_position_id: Optional[str]
    opened_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Order Schemas
class OrderCreate(BaseModel):
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class OrderModify(BaseModel):
    quantity: Optional[float] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class OrderResponse(BaseModel):
    id: int
    account_id: int
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    filled_quantity: float
    price: Optional[float]
    average_fill_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: OrderStatus
    broker_order_id: Optional[str]
    created_at: datetime
    filled_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


# Trade Schemas
class TradeResponse(BaseModel):
    id: int
    account_id: int
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    exit_price: Optional[float]
    gross_pnl: float
    commission: float
    swap: float
    net_pnl: float
    broker_trade_id: Optional[str]
    opened_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Webhook Signal Schemas
class WebhookSignalTradingView(BaseModel):
    """TradingView webhook payload"""
    ticker: Optional[str] = None
    action: Optional[str] = None
    sentiment: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time: Optional[str] = None
    interval: Optional[str] = None
    # Allow any additional fields
    extra: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class WebhookSignalGeneric(BaseModel):
    """Generic webhook signal"""
    symbol: str
    action: SignalAction
    quantity: Optional[float] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    account_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class SignalRequest(BaseModel):
    """Signal request for trading"""
    broker: str
    account_id: int
    symbol: str
    action: str
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    magic_number: Optional[int] = None
    comment: Optional[str] = None
    source: Optional[str] = None
    # Strategy tracking fields
    strategy_id: Optional[str] = None
    strategy_version: Optional[str] = None
    strategy_name: Optional[str] = None


class OrderRequest(BaseModel):
    """Order request"""
    account_id: int
    symbol: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class OrderResponse(BaseModel):
    """Order response"""
    id: int
    account_id: int
    symbol: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: datetime


class TradeRequest(BaseModel):
    """Trade request"""
    account_id: int
    symbol: str
    action: str
    quantity: float
    price: Optional[float] = None


class TradeResponse(BaseModel):
    """Trade response"""
    id: int
    account_id: int
    symbol: str
    action: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: datetime


class WebhookRequest(BaseModel):
    """Webhook request"""
    source: str
    payload: Dict[str, Any]


class WebhookResponse(BaseModel):
    """Webhook response"""
    success: bool
    message: str
    signal_id: Optional[str] = None
    timestamp: datetime


class Position(BaseModel):
    """Position model"""
    id: int
    account_id: int
    position_id: str
    broker_position_id: Optional[str] = None
    symbol: str
    type: str
    volume: float
    price_open: float
    price_current: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    margin: float = 0.0
    is_active: bool
    open_time: datetime
    close_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class Account(BaseModel):
    """Account model"""
    id: int
    user_id: int
    broker: str
    account_number: str
    account_type: str
    currency: str
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    leverage: int = 100
    is_connected: bool
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]


class SignalResponse(BaseModel):
    id: int
    user_id: int
    source: str
    symbol: str
    action: str
    quantity: Optional[float]
    price: Optional[float]
    status: str
    received_at: datetime
    processed_at: Optional[datetime]
    executed_at: Optional[datetime]
    execution_results: Optional[Dict[str, Any]]
    error_message: Optional[str]

    class Config:
        from_attributes = True


# Webhook Config Schemas
class WebhookConfigCreate(BaseModel):
    name: str
    source: str = "tradingview"
    default_account_id: Optional[int] = None
    routing_rules: Optional[Dict[str, Any]] = None
    symbol_filter: Optional[List[str]] = None
    action_filter: Optional[List[str]] = None


class WebhookConfigResponse(BaseModel):
    id: int
    user_id: int
    name: str
    webhook_key: str
    source: str
    default_account_id: Optional[int]
    routing_rules: Optional[Dict[str, Any]]
    symbol_filter: Optional[Dict[str, Any]]
    action_filter: Optional[Dict[str, Any]]
    is_active: bool
    total_signals: int
    successful_signals: int
    failed_signals: int
    created_at: datetime

    class Config:
        from_attributes = True


# Performance Schemas
class PerformanceMetricsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    period_type: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    total_commission: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    profit_factor: Optional[float]
    starting_balance: float
    ending_balance: float
    peak_balance: float

    class Config:
        from_attributes = True


# Dashboard Schemas
class DashboardSummary(BaseModel):
    total_accounts: int
    active_accounts: int
    total_balance: float
    total_equity: float
    total_pnl: float
    total_positions: int
    total_pending_orders: int
    recent_signals: List[SignalResponse]


class UnifiedAccountSummary(BaseModel):
    accounts: List[TradingAccountResponse]
    total_balance: float
    total_equity: float
    total_margin: float
    total_free_margin: float


class UnifiedPositionSummary(BaseModel):
    positions: List[PositionResponse]
    total_unrealized_pnl: float
    total_positions: int
    symbols: List[str]


# Market Data Schemas
class QuoteData(BaseModel):
    symbol: str
    bid: float
    ask: float
    last: Optional[float]
    volume: Optional[float]
    timestamp: datetime


class InstrumentInfo(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str]
    asset_type: Optional[str]
    min_quantity: Optional[float]
    max_quantity: Optional[float]
    tick_size: Optional[float]
    leverage: Optional[float]


# WebSocket Messages
class WSMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Error Response
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# Success Response
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
