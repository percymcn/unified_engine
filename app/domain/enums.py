"""
Domain Enums

Pure Python enums for the domain layer with no framework dependencies.
All enums inherit from (str, Enum) to enable JSON serialization.
"""

from enum import Enum


class OrderType(str, Enum):
    """
    Types of trading orders.

    Market orders execute immediately at current price.
    Limit orders execute only at specified price or better.
    Stop orders become market orders when price is reached.
    """
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"


class OrderStatus(str, Enum):
    """
    Status of an order in its lifecycle.

    - PENDING: Order created but not yet submitted to broker
    - EXECUTED: Order fully filled
    - CANCELLED: Order cancelled before execution
    - REJECTED: Broker rejected the order
    - PARTIALLY_FILLED: Order partially executed (not all volume filled)
    """
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"


class SignalSource(str, Enum):
    """
    Source of trading signals.

    Identifies where a trading signal originated from for tracking and routing.
    """
    TRADINGVIEW = "tradingview"
    TRAILHACKER = "trailhacker"
    MANUAL = "manual"
    API = "api"


class SignalAction(str, Enum):
    """
    Action to be taken for a signal.

    - BUY: Open long position
    - SELL: Open short position
    - CLOSE: Close existing position
    - MODIFY: Modify existing position (SL/TP)
    """
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    MODIFY = "modify"


class BrokerType(str, Enum):
    """
    Supported broker platforms.

    Each broker type has its own adapter implementation for trade execution.
    """
    TRADELOCKER = "tradelocker"
    TOPSTEP = "topstep"
    TRADOVATE = "tradovate"
    MT4 = "mt4"
    MT5 = "mt5"
    PROJECTX = "projectx"


class AccountType(str, Enum):
    """
    Type of trading account.

    - LIVE: Real money trading account
    - DEMO: Practice account with virtual money
    - EVALUATION: Funded evaluation account (TopStep, etc.)
    """
    LIVE = "live"
    DEMO = "demo"
    EVALUATION = "evaluation"


class PositionSide(str, Enum):
    """
    Direction of a position.

    - LONG: Profit when price increases (bought)
    - SHORT: Profit when price decreases (sold)
    """
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    """
    Status of a trade.

    - OPEN: Trade is currently active
    - CLOSED: Trade has been closed
    - PARTIALLY_CLOSED: Part of the position has been closed
    """
    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"


class SignalStatus(str, Enum):
    """
    Processing status of a signal.

    - PENDING: Signal received, awaiting processing
    - PROCESSING: Currently being executed across accounts
    - PROCESSED: Successfully executed on all target accounts
    - FAILED: Execution failed
    - SKIPPED: Signal intentionally skipped (account disabled, etc.)
    """
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"
