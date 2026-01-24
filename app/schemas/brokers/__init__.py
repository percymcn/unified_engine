"""
Normalized Broker Response Schemas

Shared Pydantic models for broker-agnostic responses.
All schemas include:
- Standard fields (broker, account_id, symbol, side, qty, price, status, timestamps)
- Provider-specific fields under `raw: dict | None`
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    BRACKET = "bracket"  # OCO
    CHAIN = "chain"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    """Position side."""
    LONG = "long"
    SHORT = "short"


# ============================================================================
# Account Schemas
# ============================================================================

class AccountOut(BaseModel):
    """Normalized account response."""
    broker: str = Field(..., description="Broker identifier")
    account_id: str = Field(..., description="Broker account ID")
    account_type: str = Field(..., description="Account type (live, demo, evaluation)")
    currency: str = Field(default="USD", description="Account currency")
    balance: float = Field(..., description="Account balance")
    equity: float = Field(..., description="Account equity")
    margin: float = Field(default=0.0, description="Used margin")
    free_margin: float = Field(default=0.0, description="Free margin")
    margin_level: float = Field(default=0.0, description="Margin level percentage")
    leverage: int = Field(default=100, description="Account leverage")
    is_active: bool = Field(default=True, description="Account active status")
    is_live: bool = Field(default=True, description="Live account flag")
    created_at: Optional[str] = Field(None, description="Account creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


# ============================================================================
# Position Schemas
# ============================================================================

class PositionOut(BaseModel):
    """Normalized position response."""
    broker: str = Field(..., description="Broker identifier")
    account_id: str = Field(..., description="Broker account ID")
    position_id: str = Field(..., description="Position ID")
    symbol: str = Field(..., description="Instrument symbol")
    side: PositionSide = Field(..., description="Position side (long/short)")
    size: float = Field(..., description="Position size (quantity)")
    entry_price: float = Field(..., description="Entry price")
    current_price: Optional[float] = Field(None, description="Current market price")
    unrealized_pnl: float = Field(default=0.0, description="Unrealized P&L")
    realized_pnl: float = Field(default=0.0, description="Realized P&L")
    margin: float = Field(default=0.0, description="Margin used")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    opened_at: Optional[str] = Field(None, description="Position open timestamp")
    closed_at: Optional[str] = Field(None, description="Position close timestamp")
    is_active: bool = Field(default=True, description="Position active status")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


# ============================================================================
# Order Schemas
# ============================================================================

class OrderOut(BaseModel):
    """Normalized order response."""
    broker: str = Field(..., description="Broker identifier")
    account_id: Optional[str] = Field(None, description="Broker account ID")
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Instrument symbol")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    order_type: OrderType = Field(..., description="Order type")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(None, description="Order price (for limit orders)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    status: OrderStatus = Field(..., description="Order status")
    filled_quantity: float = Field(default=0.0, description="Filled quantity")
    filled_price: Optional[float] = Field(None, description="Average fill price")
    created_at: Optional[str] = Field(None, description="Order creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    filled_at: Optional[str] = Field(None, description="Fill timestamp")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


# ============================================================================
# Market Data Schemas
# ============================================================================

class QuoteOut(BaseModel):
    """Normalized market quote response."""
    broker: str = Field(..., description="Broker identifier")
    symbol: str = Field(..., description="Instrument symbol")
    bid: float = Field(..., description="Bid price")
    ask: float = Field(..., description="Ask price")
    last: Optional[float] = Field(None, description="Last traded price")
    volume: Optional[int] = Field(None, description="Trading volume")
    timestamp: Optional[str] = Field(None, description="Quote timestamp")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


class OHLCVOut(BaseModel):
    """Normalized OHLCV candle data."""
    broker: str = Field(..., description="Broker identifier")
    symbol: str = Field(..., description="Instrument symbol")
    timestamp: str = Field(..., description="Candle timestamp")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: Optional[int] = Field(None, description="Volume")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


class OrderBookLevel(BaseModel):
    """Order book level."""
    price: float = Field(..., description="Price level")
    size: float = Field(..., description="Size at this level")


class OrderBookOut(BaseModel):
    """Normalized Level 2 orderbook response."""
    broker: str = Field(..., description="Broker identifier")
    symbol: str = Field(..., description="Instrument symbol")
    bids: List[OrderBookLevel] = Field(..., description="Bid levels")
    asks: List[OrderBookLevel] = Field(..., description="Ask levels")
    best_bid: float = Field(..., description="Best bid price")
    best_ask: float = Field(..., description="Best ask price")
    spread: float = Field(..., description="Spread (best_ask - best_bid)")
    timestamp: Optional[str] = Field(None, description="Orderbook timestamp")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


# ============================================================================
# Analytics Schemas
# ============================================================================

class PerformanceStatsOut(BaseModel):
    """Normalized performance statistics."""
    broker: str = Field(..., description="Broker identifier")
    account_id: Optional[str] = Field(None, description="Broker account ID")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    total_return: Optional[float] = Field(None, description="Total return")
    volatility: Optional[float] = Field(None, description="Volatility")
    win_rate: Optional[float] = Field(None, description="Win rate")
    profit_factor: Optional[float] = Field(None, description="Profit factor")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


class SessionStatsOut(BaseModel):
    """Normalized session statistics."""
    broker: str = Field(..., description="Broker identifier")
    account_id: Optional[str] = Field(None, description="Broker account ID")
    session_type: Optional[str] = Field(None, description="Session type")
    total_trades: int = Field(default=0, description="Total trades")
    winning_trades: int = Field(default=0, description="Winning trades")
    losing_trades: int = Field(default=0, description="Losing trades")
    win_rate: float = Field(default=0.0, description="Win rate")
    total_pnl: float = Field(default=0.0, description="Total P&L")
    average_win: float = Field(default=0.0, description="Average win")
    average_loss: float = Field(default=0.0, description="Average loss")
    profit_factor: float = Field(default=0.0, description="Profit factor")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


class PortfolioMetricsOut(BaseModel):
    """Normalized portfolio metrics."""
    broker: str = Field(..., description="Broker identifier")
    account_id: Optional[str] = Field(None, description="Broker account ID")
    total_pnl: float = Field(default=0.0, description="Total P&L")
    win_rate: float = Field(default=0.0, description="Win rate")
    total_positions: int = Field(default=0, description="Total positions")
    winning_positions: int = Field(default=0, description="Winning positions")
    losing_positions: int = Field(default=0, description="Losing positions")
    raw: Optional[Dict[str, Any]] = Field(None, description="Provider-specific fields")


# ============================================================================
# Request Schemas
# ============================================================================

class OrderCreate(BaseModel):
    """Order creation request."""
    account_id: int = Field(..., description="Database account ID")
    symbol: str = Field(..., description="Instrument symbol")
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Limit price (required for limit orders)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")


class BracketOrderCreate(BaseModel):
    """Bracket order (OCO) creation request."""
    account_id: int = Field(..., description="Database account ID")
    symbol: str = Field(..., description="Instrument symbol")
    side: OrderSide = Field(..., description="Order side")
    quantity: float = Field(..., gt=0, description="Order quantity")
    entry_price: Optional[float] = Field(None, description="Entry price (None = market)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")


class OrderModify(BaseModel):
    """Order modification request."""
    price: Optional[float] = Field(None, description="New price")
    stop_loss: Optional[float] = Field(None, description="New stop loss")
    take_profit: Optional[float] = Field(None, description="New take profit")
    quantity: Optional[float] = Field(None, gt=0, description="New quantity")


class StreamSubscribe(BaseModel):
    """Stream subscription request."""
    account_id: int = Field(..., description="Database account ID")
    symbol: str = Field(..., description="Instrument symbol")
    topics: Optional[List[str]] = Field(None, description="Topics to subscribe to")
