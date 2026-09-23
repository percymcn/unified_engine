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

    Postgres ``signalsource`` was created before ``CUSTOM`` existed. Persisting
    the name ``CUSTOM`` (or the value ``custom``) raises
    ``invalid input value for enum signalsource``. ``TRAILHACKER`` is a label
    that already exists. Unknown and custom sources coerce to ``API``.
    """
    TRADINGVIEW = "tradingview"
    TRAILHACKER = "trailhacker"
    MANUAL = "manual"
    API = "api"
    # Accepted in Python only. coerce_signal_source() never returns this.
    CUSTOM = "custom"


# Labels that already exist on the Postgres signalsource enum.
_PERSISTED_SIGNAL_SOURCES = {
    "tradingview": SignalSource.TRADINGVIEW,
    "tv": SignalSource.TRADINGVIEW,
    "trailhacker": SignalSource.TRAILHACKER,
    "trail_hacker": SignalSource.TRAILHACKER,
    "manual": SignalSource.MANUAL,
    "api": SignalSource.API,
}


def coerce_signal_source(raw: object, *, default: "SignalSource | None" = None) -> "SignalSource":
    """Map a webhook/source token onto a SignalSource Postgres will accept.

    TrailHacker (any casing) becomes ``TRAILHACKER``. ``CUSTOM`` / ``custom`` /
    empty / unknown tokens become ``API`` so test pings and custom webhooks
    do not insert an enum label the database rejects. TradingView stays
    ``TRADINGVIEW``.
    """
    fallback = default if default is not None else SignalSource.API
    if isinstance(raw, SignalSource):
        if raw is SignalSource.CUSTOM:
            return fallback if fallback is not SignalSource.CUSTOM else SignalSource.API
        return raw

    token = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if token in ("custom", "unknown", "none", "null", ""):
        return fallback if fallback is not SignalSource.CUSTOM else SignalSource.API
    return _PERSISTED_SIGNAL_SOURCES.get(token, fallback if fallback is not SignalSource.CUSTOM else SignalSource.API)


def is_empty_signal_payload(payload: object) -> bool:
    """True when a webhook body has no symbol and no action (empty/test POST)."""
    if not isinstance(payload, dict) or not payload:
        return True
    symbol = payload.get("symbol") or payload.get("ticker")
    action = payload.get("signal") or payload.get("action") or payload.get("order_action")
    return not str(symbol or "").strip() and not str(action or "").strip()


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
