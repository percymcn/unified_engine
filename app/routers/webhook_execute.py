"""
Webhook Execute Endpoint - TradingView Alert Execution

Standardized endpoint for immediate trade execution from TradingView alerts.
Supports multi-account routing with configurable strategies.

Payload format:
{
    "webhook_key": "unique-per-account-key",  // REQUIRED
    "action": "buy" | "sell" | "close",       // REQUIRED
    "symbol": "EURUSD",                       // REQUIRED
    "quantity": 0.1,                          // Optional, default 0.01
    "sl": 1.0800,                             // Optional stop loss
    "tp": 1.0900,                             // Optional take profit
    "timestamp": "2026-01-25T10:00:00Z",      // Optional for staleness check
    "strategy_id": "my_strategy",             // Optional (used for rules_based routing)
    "comment": "TV alert",                    // Optional
    "target_account_ids": [1, 2, 3]           // Optional: override routing to specific accounts
}

Routing Strategies (configured in WebhookConfig):
- direct_account_key: Webhook key matches a single account's webhook_key
- all_accounts: Route to all signal-enabled accounts for the user
- specific_accounts: Route to accounts in specific_account_ids list
- rules_based: Apply routing_rules by symbol/strategy
- default_only: Route only to default_account_id
"""
import logging
import uuid
import json
from json import JSONDecodeError
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.models import WebhookLog, ExecutionLog, BrokerType as ModelsBrokerType, Signal as SignalORM, SignalSource as ModelsSignalSource, SymbolAlias
from app.models.database_models import TradingAccount, DiscardBin, WebhookConfig
from app.models.schemas import WebhookLogCreate
from app.dependencies import get_container
from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.enums import SignalSource, SignalAction
from app.services.signal_intelligence_guard import SignalIntelligenceGuard, GuardDecision, GuardResult
from app.domain.entities.signal import Signal
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId
from app.domain.services.account_routing_service import AccountRoutingService
from app.domain.services.risk_unit_converter import RiskUnitConverter, RiskUnitMode
from app.domain.services.daily_counter_service import DailyCounterService
from app.infrastructure.repositories import get_daily_counter_repository
from app.services.compat_positions_cache import record_open, record_close, is_enabled as compat_positions_enabled
from app.services.position_sync_service import sync_positions_before_check
from app.models.database_models import DailyPnL, AccountEquityHistory, CircuitBreakerSettings, DynamicSizingSettings, EquityCurveState
from app.services.trade_analytics_service import TradeAnalyticsService
from datetime import date as date_type

logger = logging.getLogger(__name__)

# EST timezone for market hours
EST = ZoneInfo("America/New_York")


def is_market_hours() -> tuple[bool, str]:
    """
    Check if current time is during US market hours (EST).

    Returns:
        (is_open: bool, session: str)
        session can be: 'premarket', 'regular', 'afterhours', 'closed'
    """
    now_est = datetime.now(EST)
    weekday = now_est.weekday()  # 0=Monday, 6=Sunday
    hour = now_est.hour
    minute = now_est.minute
    current_minutes = hour * 60 + minute

    # Weekend - market closed
    if weekday >= 5:
        return False, "closed"

    # Premarket: 4:00am - 9:30am EST
    if 4 * 60 <= current_minutes < 9 * 60 + 30:
        return True, "premarket"

    # Regular hours: 9:30am - 4:00pm EST
    if 9 * 60 + 30 <= current_minutes < 16 * 60:
        return True, "regular"

    # Afterhours: 4:00pm - 8:00pm EST
    if 16 * 60 <= current_minutes < 20 * 60:
        return True, "afterhours"

    return False, "closed"


def get_market_hours_confidence_boost(source: str = None) -> float:
    """
    Get confidence boost based on market hours.

    TradingView signals during regular hours get higher confidence.

    Returns:
        Confidence multiplier (1.0 = no boost, 1.2 = 20% boost, etc.)
    """
    is_open, session = is_market_hours()

    if session == "regular":
        # Regular market hours - highest confidence
        return 1.2  # 20% boost
    elif session == "premarket":
        # Premarket - moderate confidence
        return 1.1  # 10% boost
    elif session == "afterhours":
        # Afterhours - slight boost
        return 1.05  # 5% boost
    else:
        # Market closed - no boost
        return 1.0


def normalize_confidence(confidence_value: Any) -> Optional[float]:
    """Normalize confidence values to a percentage (0-100)."""
    if confidence_value is None:
        return None
    try:
        value = float(confidence_value)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return 0.0
    if value <= 1:
        return value * 100
    return value


FOREX_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "AUD", "CHF"}


def is_forex_symbol(symbol: str) -> bool:
    """Detect common 6-letter forex pairs (optionally prefixed with C:)."""
    if not symbol:
        return False
    normalized = symbol.upper().replace("/", "").replace("-", "").replace("_", "")
    if normalized.startswith("C:"):
        normalized = normalized[2:]
    if len(normalized) < 6:
        return False
    base = normalized[:3]
    quote = normalized[3:6]
    return base in FOREX_CURRENCIES and quote in FOREX_CURRENCIES


def utc_to_est(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to EST."""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(EST)


def est_to_utc(est_dt: datetime) -> datetime:
    """Convert EST datetime to UTC."""
    if est_dt.tzinfo is None:
        est_dt = est_dt.replace(tzinfo=EST)
    return est_dt.astimezone(timezone.utc)


# ============================================================================
# PENDING POSITIONS TRACKER - Prevents race condition in position enforcement
# ============================================================================
# When multiple signals arrive rapidly, they can all pass the position check
# before any orders are actually placed. This tracker counts pending orders
# that haven't yet been confirmed by the broker.
import threading
from collections import defaultdict
import time

class PendingPositionsTracker:
    """
    Thread-safe tracker for pending position orders.

    Prevents race condition where multiple signals slip through position limits
    because they all check positions before any orders are confirmed.
    """
    def __init__(self, ttl_seconds: int = 30):
        self._pending: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._timestamps: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def _make_key(self, account_id: int, symbol: str) -> tuple:
        """Create normalized key for account+symbol."""
        return (str(account_id), symbol.upper().strip())

    def _cleanup_expired(self, account_key: str, symbol_key: str):
        """Remove expired pending entries."""
        now = time.time()
        if now - self._timestamps[account_key][symbol_key] > self._ttl:
            self._pending[account_key][symbol_key] = 0
            self._timestamps[account_key][symbol_key] = now

    def get_pending_count(self, account_id: int, symbol: str) -> int:
        """Get count of pending orders for account+symbol."""
        account_key, symbol_key = self._make_key(account_id, symbol)
        with self._lock:
            self._cleanup_expired(account_key, symbol_key)
            return self._pending[account_key][symbol_key]

    def increment(self, account_id: int, symbol: str) -> int:
        """Increment pending count, returns new count."""
        account_key, symbol_key = self._make_key(account_id, symbol)
        with self._lock:
            self._cleanup_expired(account_key, symbol_key)
            self._pending[account_key][symbol_key] += 1
            self._timestamps[account_key][symbol_key] = time.time()
            return self._pending[account_key][symbol_key]

    def decrement(self, account_id: int, symbol: str) -> int:
        """Decrement pending count after order completes."""
        account_key, symbol_key = self._make_key(account_id, symbol)
        with self._lock:
            if self._pending[account_key][symbol_key] > 0:
                self._pending[account_key][symbol_key] -= 1
            return self._pending[account_key][symbol_key]

    def reset(self, account_id: int, symbol: str):
        """Reset pending count for account+symbol."""
        account_key, symbol_key = self._make_key(account_id, symbol)
        with self._lock:
            self._pending[account_key][symbol_key] = 0


# Global singleton for tracking pending positions per symbol
_pending_tracker = PendingPositionsTracker(ttl_seconds=30)


class PendingTotalPositionsTracker:
    """
    Thread-safe tracker for pending total position orders per account.

    Prevents race condition where multiple signals slip through max_open_positions
    because they all check before any orders are confirmed.
    """
    def __init__(self, ttl_seconds: int = 30):
        self._pending: Dict[str, int] = defaultdict(int)
        self._timestamps: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def _make_key(self, account_id: int) -> str:
        """Create normalized key for account."""
        return str(account_id)

    def _cleanup_expired(self, account_key: str):
        """Remove expired pending entries."""
        now = time.time()
        if now - self._timestamps[account_key] > self._ttl:
            self._pending[account_key] = 0
            self._timestamps[account_key] = now

    def get_pending_count(self, account_id: int) -> int:
        """Get count of pending orders for account."""
        account_key = self._make_key(account_id)
        with self._lock:
            self._cleanup_expired(account_key)
            return self._pending[account_key]

    def increment(self, account_id: int) -> int:
        """Increment pending count, returns new count."""
        account_key = self._make_key(account_id)
        with self._lock:
            self._cleanup_expired(account_key)
            self._pending[account_key] += 1
            self._timestamps[account_key] = time.time()
            return self._pending[account_key]

    def decrement(self, account_id: int) -> int:
        """Decrement pending count after order completes."""
        account_key = self._make_key(account_id)
        with self._lock:
            if self._pending[account_key] > 0:
                self._pending[account_key] -= 1
            return self._pending[account_key]


# Global singleton for tracking total pending positions per account
_pending_total_tracker = PendingTotalPositionsTracker(ttl_seconds=30)


def validate_sl_tp_distance(
    sl_price: float,
    tp_price: float,
    entry_price: float,
    symbol: str,
    is_buy: bool,
    min_percent_distance: float = 0.01  # 0.01% minimum distance
) -> tuple[float | None, float | None, list[str]]:
    """
    Validate SL/TP prices have minimum distance from entry.

    Rejects SL/TP values that are too close to entry price (likely tick values
    mistakenly sent as absolute prices).

    Args:
        sl_price: Stop loss price (or None)
        tp_price: Take profit price (or None)
        entry_price: Entry/current price
        symbol: Symbol for logging
        is_buy: True for buy orders
        min_percent_distance: Minimum distance as percentage (default 0.01%)

    Returns:
        Tuple of (validated_sl, validated_tp, warnings)
        Invalid values are set to None with warnings logged
    """
    warnings = []
    validated_sl = sl_price
    validated_tp = tp_price

    if not entry_price or entry_price <= 0:
        return validated_sl, validated_tp, warnings

    min_distance = entry_price * (min_percent_distance / 100)

    # Validate SL distance
    if sl_price is not None:
        sl_distance = abs(float(sl_price) - entry_price)
        sl_percent = (sl_distance / entry_price) * 100

        if sl_distance < min_distance:
            warnings.append(
                f"SL {sl_price} too close to entry {entry_price} "
                f"({sl_percent:.6f}% < {min_percent_distance}% min). "
                f"Ignoring signal SL - will use account default if set."
            )
            validated_sl = None

        # Also validate SL direction (should be below entry for buy, above for sell)
        elif is_buy and float(sl_price) >= entry_price:
            warnings.append(
                f"SL {sl_price} invalid for BUY (should be below entry {entry_price}). Ignoring."
            )
            validated_sl = None
        elif not is_buy and float(sl_price) <= entry_price:
            warnings.append(
                f"SL {sl_price} invalid for SELL (should be above entry {entry_price}). Ignoring."
            )
            validated_sl = None

    # Validate TP distance
    if tp_price is not None:
        tp_distance = abs(float(tp_price) - entry_price)
        tp_percent = (tp_distance / entry_price) * 100

        if tp_distance < min_distance:
            warnings.append(
                f"TP {tp_price} too close to entry {entry_price} "
                f"({tp_percent:.6f}% < {min_percent_distance}% min). "
                f"Ignoring signal TP - will use account default if set."
            )
            validated_tp = None

        # Also validate TP direction (should be above entry for buy, below for sell)
        elif is_buy and float(tp_price) <= entry_price:
            warnings.append(
                f"TP {tp_price} invalid for BUY (should be above entry {entry_price}). Ignoring."
            )
            validated_tp = None
        elif not is_buy and float(tp_price) >= entry_price:
            warnings.append(
                f"TP {tp_price} invalid for SELL (should be below entry {entry_price}). Ignoring."
            )
            validated_tp = None

    return validated_sl, validated_tp, warnings


CRYPTO_SYMBOL_HINTS = {
    "BTCUSD", "ETHUSD", "BTC", "ETH", "XBTUSD", "XETHUSD", "BTCUSDT", "ETHUSDT", "SOLUSD", "SOLUSDT",
}


def _normalize_execution_target_broker_account_id(raw_target: Any) -> Optional[str]:
    """Normalize broker subaccount ids and drop empty/invalid placeholders."""
    if raw_target is None:
        return None
    normalized = str(raw_target).strip()
    if not normalized:
        return None
    if normalized.lower() in {"none", "null", "undefined", "nan"}:
        return None
    return normalized


def _execution_target_key(account_id: int, target_broker_account_id: Optional[Any]) -> str:
    normalized_target = _normalize_execution_target_broker_account_id(target_broker_account_id)
    return f"{account_id}:{normalized_target or 'parent'}"


def _execution_target_label(account_id: int, broker: str, target_broker_account_id: Optional[Any]) -> str:
    normalized_target = _normalize_execution_target_broker_account_id(target_broker_account_id)
    if normalized_target:
        return f"account={account_id} broker={broker} subaccount={normalized_target}"
    return f"account={account_id} broker={broker} subaccount=parent"


def _is_obviously_unsupported_for_broker(symbol: str, broker: str) -> Optional[str]:
    normalized_symbol = (symbol or "").upper().replace("/", "").replace("-", "").replace("_", "")
    if normalized_symbol.startswith("X:"):
        normalized_symbol = normalized_symbol[2:]
    if broker.lower() in {"projectx", "topstep"} and normalized_symbol in CRYPTO_SYMBOL_HINTS:
        return f"{broker} does not support crypto symbol {symbol}"
    return None


def resolve_symbol_for_broker(
    db: Session,
    user_id: int,
    source_symbol: str,
    broker_type: str
) -> str:
    """
    Resolve a source symbol to the broker-specific format using symbol aliases.

    Looks up user's symbol alias table to map TradingView symbols to broker-specific formats.
    E.g., "BTCUSD" -> "BTC/USD" for TradeLocker, or "BTCUSD" -> "BTCUSD.ecn" for MT5.

    Args:
        db: Database session
        user_id: User ID to look up aliases for
        source_symbol: The incoming symbol (e.g., from TradingView)
        broker_type: The broker type (e.g., "tradelocker", "mt5", "projectx")

    Returns:
        The mapped symbol for the broker, or the original symbol if no mapping found.
    """
    source_upper = source_symbol.upper().strip()
    broker_lower = broker_type.lower().strip()

    # Look up alias for this user/symbol/broker combination
    alias = db.query(SymbolAlias).filter(
        SymbolAlias.user_id == user_id,
        SymbolAlias.source_symbol == source_upper,
        SymbolAlias.broker_type == broker_lower
    ).first()

    if alias and alias.target_symbol:
        logger.info(f"Symbol mapped: {source_symbol} -> {alias.target_symbol} for {broker_type}")
        return alias.target_symbol

    normalized_source = source_upper.replace("/", "").replace("-", "").replace("_", "")

    if broker_lower in {"projectx", "topstep"}:
        try:
            from app.services.contract_resolver import ContractResolver
            resolved_symbol = ContractResolver.normalize_symbol(source_upper)
            if resolved_symbol and resolved_symbol != source_symbol:
                logger.info(f"Contract-normalized symbol: {source_symbol} -> {resolved_symbol} for {broker_type}")
                return resolved_symbol
        except Exception:
            pass

    if broker_lower == "tradelocker" and normalized_source in CRYPTO_SYMBOL_HINTS:
        base = normalized_source[:-3] if normalized_source.endswith("USD") else normalized_source
        mapped = f"{base}/USD"
        logger.info(f"Heuristic crypto symbol map: {source_symbol} -> {mapped} for {broker_type}")
        return mapped

    # No alias found - return original symbol
    return source_symbol


router = APIRouter()


class TradingViewPayload(BaseModel):
    """Standardized TradingView webhook payload"""
    webhook_key: str = Field(..., description="Unique webhook key for account identification")
    action: str = Field(..., description="Trade action: buy, sell, or close")
    symbol: str = Field(..., description="Trading symbol")
    quantity: Optional[float] = Field(0.01, description="Trade quantity/lots")
    sl: Optional[float] = Field(None, description="Stop loss price (alias: stop_loss)")
    tp: Optional[float] = Field(None, description="Take profit price (alias: take_profit)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price (alias: sl)")
    take_profit: Optional[float] = Field(None, description="Take profit price (alias: tp)")
    trailing_stop: Optional[float] = Field(None, description="Trailing stop distance (in ticks for ProjectX)")
    order_type: Optional[str] = Field("market", description="Order type: market or limit")
    limit_price: Optional[float] = Field(None, description="Limit price for limit orders")
    timestamp: Optional[str] = Field(None, description="Signal timestamp for staleness check")
    strategy_id: Optional[str] = Field(None, description="Strategy identifier")
    comment: Optional[str] = Field(None, description="Trade comment")
    target_account_ids: Optional[List[int]] = Field(None, description="Override routing to specific accounts")


class AccountExecutionResult(BaseModel):
    """Result for a single account execution target."""
    account_id: int
    broker: str
    success: bool
    status: str
    error: Optional[str] = None
    execution_id: Optional[str] = None
    target_broker_account_id: Optional[str] = None
    target_label: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Standard execution response with multi-account support"""
    success: bool
    signal_id: str
    status: str  # executed, partial, rejected, paused, failed
    webhook_id: str
    routing_strategy: str = "default_only"
    routing_reason: Optional[str] = None
    total_accounts: int = 0
    total_execution_targets: int = 0
    successful_accounts: int = 0
    failed_accounts: int = 0
    successful_targets: int = 0
    failed_targets: int = 0
    account_results: List[AccountExecutionResult] = []
    # Legacy single-account fields for backwards compatibility
    account_id: Optional[int] = None
    broker: Optional[str] = None
    errors: list = []
    guard_decision: Optional[str] = None
    guard_reason: Optional[str] = None
    modal_data: Optional[Dict[str, Any]] = None
    processing_time_ms: int = 0


def log_event(event_type: str, **kwargs):
    """Structured logging helper (structlog-compatible format)"""
    log_data = {"event": event_type, "ts": datetime.utcnow().isoformat(), **kwargs}
    logger.info(json.dumps(log_data))


def _get_client_ip(request: Request) -> str:
    """Extract real client IP handling Cloudflare and proxy headers."""
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    # Nginx
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    # Standard proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Direct
    return request.client.host if request.client else "unknown"


# Known TradingView IP ranges (as of 2024)
# Reference: https://www.tradingview.com/support/solutions/43000529348
TRADINGVIEW_IP_RANGES = [
    "52.89.214.",
    "34.212.75.",
    "54.218.53.",
    "52.32.178.",
    "167.89.101.",
    "167.89.100.",
]


def _is_tradingview_ip(ip: str) -> bool:
    """Check if IP is from known TradingView ranges."""
    for prefix in TRADINGVIEW_IP_RANGES:
        if ip.startswith(prefix):
            return True
    return False


@router.post("/execute", response_model=ExecuteResponse)
async def execute_tradingview_signal(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Execute a TradingView signal immediately.

    Flow:
    1. Parse JSON payload → require webhook_key
    2. Lookup account by webhook_key
    3. Run signal intelligence guard
    4. Execute via broker if approved
    5. Persist execution log

    Returns:
        200: Execution completed (success or failure)
        202: Awaiting confirmation (guard modal required)
        403: Invalid webhook_key
        422: Invalid payload
    """
    start_time = datetime.utcnow()
    webhook_id = str(uuid.uuid4())

    # Get and log client IP for security auditing
    client_ip = _get_client_ip(request)
    is_tv_ip = _is_tradingview_ip(client_ip)

    try:
        # Parse JSON payload
        raw_payload = await request.json()
    except Exception as e:
        logger.warning(f"Invalid JSON payload from {client_ip}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON payload"
        )

    # Log webhook received with IP info for security auditing
    log_event(
        "webhook_received",
        webhook_id=webhook_id,
        has_key=bool(raw_payload.get("webhook_key")),
        client_ip=client_ip,
        is_tradingview_ip=is_tv_ip,
        user_agent=request.headers.get("user-agent", "")[:100]
    )

    # Validate required fields
    webhook_key = raw_payload.get("webhook_key")
    if not webhook_key:
        log_event("webhook_rejected_missing_key", webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: webhook_key"
        )

    # === PINESCRIPT FORMAT TRANSLATION ===
    # Translate PineScript webhook formats to standard format BEFORE validation
    # This allows PineScript users to send their native format without changes
    action_str = raw_payload.get("action", "").lower().strip()
    data_str = raw_payload.get("data", "").lower().strip()

    # 1. Translate data="long"/"short" to action="buy"/"sell" (PineScript entry signals)
    if data_str in ["long", "short"] and action_str not in ["buy", "sell", "close"]:
        action_str = "buy" if data_str == "long" else "sell"
        logger.info(f"PineScript translation: data='{data_str}' -> action='{action_str}'")

    # 2. Translate partial_close, tp1, tp2, tp3 to close (PineScript exit signals)
    if action_str in ["partial_close", "tp1", "tp2", "tp3", "sl", "exit"]:
        original_action = action_str
        action_str = "close"
        # Store original for potential partial close size handling
        raw_payload["_original_action"] = original_action
        logger.info(f"PineScript translation: action='{original_action}' -> action='close'")

    # Update raw_payload with translated action for downstream processing
    raw_payload["action"] = action_str

    if action_str not in ["buy", "sell", "close"]:
        log_event("webhook_rejected_invalid_action", webhook_id=webhook_id, action=action_str)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action: {action_str}. Must be 'buy', 'sell', or 'close'"
        )

    # Accept both 'symbol' and 'ticker' for compatibility with different brokers
    symbol = raw_payload.get("symbol") or raw_payload.get("ticker")
    if not symbol:
        log_event("webhook_rejected_missing_symbol", webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: symbol or ticker"
        )

    # Create webhook log with extracted fields for easier querying
    quantity = raw_payload.get("quantity") or raw_payload.get("qty") or raw_payload.get("size")
    # Track if quantity was explicitly provided (for partial close support)
    explicit_close_quantity = quantity if action_str == "close" else None
    price = raw_payload.get("price") or raw_payload.get("entry_price")
    sl = raw_payload.get("sl") or raw_payload.get("stop_loss")
    tp = raw_payload.get("tp") or raw_payload.get("take_profit")

    # Check market hours and apply confidence boost
    market_open, market_session = is_market_hours()
    confidence_boost = get_market_hours_confidence_boost()
    now_est = datetime.now(EST)
    logger.info(f"📊 Signal received: {symbol} {action_str} | Market: {market_session} | EST: {now_est.strftime('%H:%M')} | Confidence boost: {confidence_boost:.0%}")

    try:
        webhook_log = WebhookLog(
            webhook_id=webhook_id,
            source="tradingview",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(raw_payload),
            symbol=symbol,
            action=action_str,
            quantity=float(quantity) if quantity else None,
            price=float(price) if price else None,
            stop_loss=float(sl) if sl else None,
            take_profit=float(tp) if tp else None,
        )
        db.add(webhook_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create webhook log: {e}")

    # Global try/except to ensure errors are always saved to webhook_log
    try:
        return await _execute_tradingview_signal_inner(
            request=request,
            db=db,
            webhook_id=webhook_id,
            webhook_log=webhook_log,
            raw_payload=raw_payload,
            webhook_key=webhook_key,
            action_str=action_str,
            symbol=symbol,
            start_time=start_time,
            explicit_close_quantity=explicit_close_quantity
        )
    except HTTPException:
        # Re-raise HTTP exceptions (they have their own error handling)
        raise
    except Exception as e:
        # Catch-all: save error to webhook_log
        logger.exception(f"Unhandled error in webhook execution: {e}")
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        try:
            if 'webhook_log' in locals() and webhook_log:
                webhook_log.processed = False
                webhook_log.error_message = str(e)[:500]
                webhook_log.response_status = 500
                webhook_log.processing_time_ms = processing_time_ms
                webhook_log.response_body = json.dumps({
                    "success": False,
                    "error": str(e)[:200],
                    "errors": [f"Internal error: {str(e)[:200]}"],
                    "processing_time_ms": processing_time_ms
                })
                db.commit()
        except Exception as log_err:
            logger.error(f"Failed to save error to webhook_log: {log_err}")
            db.rollback()

        return ExecuteResponse(
            success=False,
            signal_id=None,
            status="error",
            webhook_id=webhook_id,
            errors=[str(e)[:200]],
            processing_time_ms=processing_time_ms
        )


async def _execute_tradingview_signal_inner(
    request: Request,
    db: Session,
    webhook_id: str,
    webhook_log: WebhookLog,
    raw_payload: dict,
    webhook_key: str,
    action_str: str,
    symbol: str,
    start_time: datetime,
    explicit_close_quantity: Optional[str] = None
):
    """Inner implementation of webhook execution with all the main logic."""
    # === SMARTFLOW ML TRACKING ===
    # Extract signal_log_id if this is a SmartFlow signal for ML outcome tracking
    smartflow_signal_log_id = raw_payload.get("smartflow_signal_log_id")
    if smartflow_signal_log_id:
        logger.info(f"📊 SmartFlow signal {smartflow_signal_log_id} received for ML tracking")

    # === MULTI-ACCOUNT ROUTING ===
    routing_service = AccountRoutingService(db)
    strategy_id = raw_payload.get("strategy_id")
    target_account_ids_override = raw_payload.get("target_account_ids")

    # If payload specifies target_account_ids, use them directly
    if target_account_ids_override:
        accounts = db.query(TradingAccount).filter(
            TradingAccount.id.in_(target_account_ids_override),
            TradingAccount.is_active == True
        ).all()
        routing_strategy = "payload_override"
        routing_reason = f"Target accounts specified in payload: {target_account_ids_override}"
        user_id = accounts[0].user_id if accounts else 0
    else:
        # Use routing service to resolve accounts
        routing_decision = routing_service.resolve_accounts(
            webhook_key=webhook_key,
            symbol=symbol,
            strategy_id=strategy_id,
            action=action_str
        )
        accounts = routing_decision.accounts
        routing_strategy = routing_decision.strategy_used
        routing_reason = routing_decision.reason
        user_id = routing_decision.user_id

    # === SYMBOL BLOCKING FILTER ===
    # Filter out accounts that have this symbol in their blocked_symbols list
    symbol_upper = symbol.upper() if symbol else ""
    original_account_count = len(accounts)
    blocked_account_ids = []

    if symbol_upper and accounts:
        filtered_accounts = []
        for account in accounts:
            blocked = account.blocked_symbols or []
            # Check if symbol is blocked (exact match or partial match)
            is_blocked = False
            for blocked_sym in blocked:
                blocked_sym_upper = (blocked_sym or "").upper()
                if blocked_sym_upper and (symbol_upper == blocked_sym_upper or symbol_upper in blocked_sym_upper or blocked_sym_upper in symbol_upper):
                    is_blocked = True
                    blocked_account_ids.append(account.id)
                    break
            if not is_blocked:
                filtered_accounts.append(account)
        accounts = filtered_accounts

        if blocked_account_ids:
            log_event(
                "symbol_blocked",
                webhook_id=webhook_id,
                symbol=symbol,
                blocked_account_ids=blocked_account_ids,
                remaining_accounts=len(accounts)
            )
            routing_reason += f" (symbol blocked on {len(blocked_account_ids)} account(s))"

    # === FOREX BROKER VALIDATION ===
    if symbol_upper and accounts and is_forex_symbol(symbol_upper):
        filtered_accounts = []
        skipped_accounts = []
        for account in accounts:
            broker_str = account.broker.value if hasattr(account.broker, "value") else str(account.broker)
            if broker_str.lower() != "mt5":
                skipped_accounts.append((account.id, broker_str))
                continue
            filtered_accounts.append(account)
        if skipped_accounts:
            skipped_ids = [account_id for account_id, _ in skipped_accounts]
            logger.warning(
                "Forex routing skip: symbol=%s skipped_accounts=%s brokers=%s",
                symbol_upper,
                skipped_ids,
                [broker for _, broker in skipped_accounts],
            )
            log_event(
                "forex_broker_skipped",
                webhook_id=webhook_id,
                symbol=symbol,
                skipped_account_ids=skipped_ids,
                skipped_brokers=[broker for _, broker in skipped_accounts],
                remaining_accounts=len(filtered_accounts),
            )
            routing_reason += f" (forex restricted to MT5, skipped {len(skipped_accounts)} account(s))"
        accounts = filtered_accounts

    # Log routing decision
    log_event(
        "routing_decision",
        webhook_id=webhook_id,
        strategy=routing_strategy,
        reason=routing_reason,
        account_count=len(accounts),
        account_ids=[a.id for a in accounts] if accounts else []
    )

    if not accounts:
        log_event(
            "webhook_rejected_invalid_key",
            webhook_id=webhook_id,
            webhook_key_prefix=webhook_key[:12] + "..." if len(webhook_key) > 12 else webhook_key
        )

        # Log to discard_bin
        try:
            discard_entry = DiscardBin(
                user_id=0,  # Unknown user
                received_at=datetime.utcnow(),
                reason="invalid_webhook_key",
                age_ms=0,
                symbol=symbol,
                side=action_str,
                raw_payload=json.dumps(raw_payload)[:500]
            )
            db.add(discard_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log discard: {e}")

        # Update webhook log
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        try:
            webhook_log.processed = False
            webhook_log.response_status = 403
            webhook_log.error_message = "Invalid webhook_key - no accounts found"
            webhook_log.processing_time_ms = processing_time_ms
            webhook_log.response_body = json.dumps({
                "success": False,
                "error": "Invalid webhook_key",
                "errors": ["Invalid webhook_key - no accounts found for routing"],
                "processing_time_ms": processing_time_ms
            })
            db.commit()
        except:
            pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook_key. Signal not executed."
        )

    # Accounts found - log context
    log_event(
        "webhook_accounts_resolved",
        webhook_id=webhook_id,
        account_ids=[a.id for a in accounts],
        user_id=user_id,
        brokers=[a.broker.value if hasattr(a.broker, 'value') else str(a.broker) for a in accounts],
        routing_strategy=routing_strategy
    )
    first_account = accounts[0]

    # Map action
    action_map = {
        "buy": SignalAction.BUY,
        "sell": SignalAction.SELL,
        "close": SignalAction.CLOSE,
    }
    action = action_map[action_str]

    # Build signal entity for guard evaluation
    # Accept quantity, contracts, or volume for compatibility with different brokers
    quantity = float(
        raw_payload.get("quantity") or
        raw_payload.get("contracts") or
        raw_payload.get("volume") or
        0.01
    )
    # Support both short (sl, tp) and long (stop_loss, take_profit) field names
    sl_price_raw = raw_payload.get("sl") or raw_payload.get("stop_loss")
    tp_price_raw = raw_payload.get("tp") or raw_payload.get("take_profit")
    trailing_stop = raw_payload.get("trailing_stop")  # Trailing stop distance
    order_type_payload = raw_payload.get("order_type", "market").lower()
    limit_price = raw_payload.get("limit_price")

    # Signal-level SL/TP type parsing (pips, points, percent, price)
    # If not specified, defaults to "price" (absolute price value)
    signal_sl_type = raw_payload.get("sl_type", "price").lower()
    signal_tp_type = raw_payload.get("tp_type", "price").lower()

    # Convert SL/TP from signal type to absolute price if needed
    # This handles signals sending values in ticks/pips/percent format
    sl_price = sl_price_raw
    tp_price = tp_price_raw

    # Get entry price hint for conversion (if available from payload or symbol lookup)
    entry_price_hint = float(raw_payload.get("price") or raw_payload.get("entry_price") or 0)
    is_buy_action = action_str.lower() == "buy"

    if sl_price_raw and entry_price_hint and signal_sl_type != "price":
        try:
            sl_unit_mode = RiskUnitMode(signal_sl_type)
            # Use symbol-specific tick size/digits for accurate conversion
            sl_price = RiskUnitConverter.convert_risk_unit_to_price(
                value=float(sl_price_raw),
                mode=sl_unit_mode,
                entry_price=entry_price_hint,
                is_buy=is_buy_action,
                is_stop_loss=True,
                digits=RiskUnitConverter.get_digits_for_symbol(symbol),
                tick_size=RiskUnitConverter.get_tick_size_for_symbol(symbol)
            )
            logger.info(f"Signal SL converted: {sl_price_raw} {signal_sl_type} -> {sl_price} (entry: {entry_price_hint}, symbol: {symbol})")
        except Exception as sl_conv_err:
            logger.warning(f"Failed to convert signal SL: {sl_conv_err}, using raw value")
            sl_price = sl_price_raw

    if tp_price_raw and entry_price_hint and signal_tp_type != "price":
        try:
            tp_unit_mode = RiskUnitMode(signal_tp_type)
            # Use symbol-specific tick size/digits for accurate conversion
            tp_price = RiskUnitConverter.convert_risk_unit_to_price(
                value=float(tp_price_raw),
                mode=tp_unit_mode,
                entry_price=entry_price_hint,
                is_buy=is_buy_action,
                is_stop_loss=False,
                digits=RiskUnitConverter.get_digits_for_symbol(symbol),
                tick_size=RiskUnitConverter.get_tick_size_for_symbol(symbol)
            )
            logger.info(f"Signal TP converted: {tp_price_raw} {signal_tp_type} -> {tp_price} (entry: {entry_price_hint}, symbol: {symbol})")
        except Exception as tp_conv_err:
            logger.warning(f"Failed to convert signal TP: {tp_conv_err}, using raw value")
            tp_price = tp_price_raw

    # === VALIDATE SL/TP DISTANCE FROM ENTRY ===
    # Reject values too close to entry (likely tick values sent as prices)
    if entry_price_hint and entry_price_hint > 0:
        validated_sl, validated_tp, sl_tp_warnings = validate_sl_tp_distance(
            sl_price=float(sl_price) if sl_price else None,
            tp_price=float(tp_price) if tp_price else None,
            entry_price=entry_price_hint,
            symbol=symbol,
            is_buy=is_buy_action,
            min_percent_distance=0.01  # 0.01% minimum (e.g., $0.05 for $500 entry)
        )

        # Log any validation warnings
        for warning in sl_tp_warnings:
            logger.warning(f"Signal {symbol}: {warning}")

        # Use validated values (None if invalid - will fall back to account defaults)
        sl_price = validated_sl
        tp_price = validated_tp

    signal_uuid = str(uuid.uuid4())

    signal_entity = Signal(
        id=SignalId(signal_uuid),
        source=SignalSource.TRADINGVIEW,
        symbol=Symbol(symbol),
        action=action,
        volume=Volume(Decimal(str(quantity))),
        price=None,  # Market order
        stop_loss=StopLoss(Price(Decimal(str(sl_price)))) if sl_price else None,
        take_profit=TakeProfit(Price(Decimal(str(tp_price)))) if tp_price else None,
        target_accounts=[AccountId(str(a.id)) for a in accounts],
        comment=raw_payload.get("comment"),
        strategy_id=raw_payload.get("strategy_id"),
        strategy_name=None,
        raw_payload=raw_payload,
    )

    # === PERSIST SIGNAL TO DATABASE ===
    # This must happen before any ExecutionLog entries (foreign key constraint)
    try:
        signal_orm = SignalORM(
            signal_id=signal_uuid,
            user_id=accounts[0].user_id if accounts else None,
            source=ModelsSignalSource.TRADINGVIEW,
            symbol=symbol,
            action=action_str.upper(),
            volume=quantity,
            price=None,  # Market order
            stop_loss=float(sl_price) if sl_price else None,
            take_profit=float(tp_price) if tp_price else None,
            comment=raw_payload.get("comment"),
            status="pending"
        )
        db.add(signal_orm)
        db.commit()
        logger.debug(f"Persisted signal {signal_uuid} to database")
    except Exception as e:
        logger.error(f"Failed to persist signal: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist signal: {e}"
        )

    # === CONFIDENCE THRESHOLD CHECK ===
    # Skip executions with missing/zero confidence, or below minimum threshold.
    if action_str.lower() != "close" and raw_payload.get("source") == "SmartFlow":
        confidence_raw = (
            raw_payload.get("confidence")
            or raw_payload.get("confidence_score")
            or raw_payload.get("confidenceScore")
            or raw_payload.get("signal_confidence")
        )
        confidence_pct = normalize_confidence(confidence_raw)
        min_confidence = 50.0  # Lowered from 60% to allow more signals through

        if confidence_pct is None or confidence_pct <= 0:
            confidence_reason = "Confidence missing or zero"
        elif confidence_pct < min_confidence:
            confidence_reason = f"Confidence below minimum ({confidence_pct:.1f}% < {min_confidence:.0f}%)"
        else:
            confidence_reason = None

        if confidence_reason:
            logger.warning(
                f"Skipping execution for {symbol} {action_str.upper()}: {confidence_reason}"
            )
            log_event(
                "confidence_rejected",
                webhook_id=webhook_id,
                signal_id=signal_entity.id.value,
                confidence=confidence_pct,
                reason=confidence_reason
            )
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            try:
                webhook_log.processed = False
                webhook_log.response_status = 200
                webhook_log.processing_time_ms = processing_time_ms
                webhook_log.response_body = json.dumps({
                    "signal_id": signal_entity.id.value,
                    "status": "rejected",
                    "guard_decision": "skip",
                    "guard_reason": confidence_reason,
                    "total_accounts": len(accounts),
                    "successful": 0,
                    "failed": len(accounts),
                })
                db.commit()

                for account in accounts:
                    try:
                        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)
                        models_broker = ModelsBrokerType(broker_str.lower())
                        exec_log = ExecutionLog(
                            signal_id=signal_entity.id.value,
                            account_id=account.id,
                            broker=models_broker,
                            action=action_str.upper(),
                            symbol=symbol,
                            volume=float(quantity),
                            status="failed",
                            error_message=f"Confidence rejected: {confidence_reason}",
                            execution_time_ms=processing_time_ms,
                        )
                        db.add(exec_log)
                    except Exception as e:
                        logger.warning(f"Failed to create confidence rejection ExecutionLog: {e}")
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to update webhook_log for confidence rejection: {e}")

            # Update WebhookConfig stats for rejection
            try:
                webhook_config = db.query(WebhookConfig).filter(
                    WebhookConfig.webhook_key == webhook_key
                ).first()
                if webhook_config:
                    webhook_config.total_signals = (webhook_config.total_signals or 0) + 1
                    webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
                    webhook_config.last_signal_at = datetime.utcnow()
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to update WebhookConfig stats for confidence rejection: {e}")
                db.rollback()

            return ExecuteResponse(
                success=False,
                signal_id=signal_entity.id.value,
                status="rejected",
                webhook_id=webhook_id,
                routing_strategy=routing_strategy,
                routing_reason=routing_reason,
                total_accounts=len(accounts),
                account_id=first_account.id,
                broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
                guard_decision="skip",
                guard_reason=confidence_reason,
                processing_time_ms=processing_time_ms
            )

    # === SIGNAL INTELLIGENCE GUARD ===
    guard = SignalIntelligenceGuard(db)

    # Get open positions summary for ALL target accounts
    # Include per-symbol P&L for momentum flip detection
    open_positions_summary = {}
    signal_symbol = symbol  # The symbol we're about to trade
    try:
        from app.models.models import Position
        for account in accounts:
            positions = db.query(Position).filter(
                Position.account_id == account.id,
                Position.is_active == True
            ).all()
            total_margin = sum(p.margin or 0.0 for p in positions) if positions else (account.margin or 0.0)

            # Build per-symbol P&L summary for momentum flip detection
            symbol_pnl = {}
            for pos in positions:
                pos_symbol = (pos.symbol or "").upper()
                pnl = pos.unrealized_pnl or 0.0
                # Determine side from position type or broker_data
                pos_side = "buy"  # default
                if pos.type and hasattr(pos.type, 'value'):
                    pos_side = "sell" if "sell" in pos.type.value.lower() else "buy"
                elif pos.broker_data and isinstance(pos.broker_data, dict):
                    pos_side = pos.broker_data.get("side", "buy").lower()

                if pos_symbol not in symbol_pnl:
                    symbol_pnl[pos_symbol] = {"buy_pnl": 0.0, "sell_pnl": 0.0, "buy_count": 0, "sell_count": 0}

                if "buy" in pos_side or "long" in pos_side:
                    symbol_pnl[pos_symbol]["buy_pnl"] += pnl
                    symbol_pnl[pos_symbol]["buy_count"] += 1
                else:
                    symbol_pnl[pos_symbol]["sell_pnl"] += pnl
                    symbol_pnl[pos_symbol]["sell_count"] += 1

            open_positions_summary[account.id] = {
                "total_margin": total_margin,
                "positions_count": len(positions) if positions else 0,
                "symbol_pnl": symbol_pnl  # Per-symbol P&L breakdown
            }
    except Exception as e:
        logger.debug(f"Could not query positions: {e}")
        for account in accounts:
            open_positions_summary[account.id] = {"total_margin": account.margin or 0.0, "positions_count": 0, "symbol_pnl": {}}

    # Evaluate guard (using first account for user context)
    guard_result = await guard.evaluate(
        signal=signal_entity,
        user_id=first_account.user_id,
        account_ids=[a.id for a in accounts],
        open_positions_summary=open_positions_summary
    )

    # Log guard decision
    log_event(
        "guard_decision",
        webhook_id=webhook_id,
        signal_id=signal_entity.id.value,
        account_ids=[a.id for a in accounts],
        decision=guard_result.decision.value,
        annotations=guard_result.annotations
    )

    # === TRADE ANALYTICS RISK MANAGEMENT ===
    # These checks are only applied for new entries (buy/sell), not closes
    risk_annotations = {}
    position_size_multiplier = 1.0

    if guard_result.decision == GuardDecision.EXECUTE and action_str.lower() != "close":
        analytics_service = TradeAnalyticsService(db)

        # 1. Circuit Breaker Check (daily loss limit, consecutive losses, win rate)
        try:
            cb_allowed, cb_reason = analytics_service.check_circuit_breakers(user_id)
            if not cb_allowed:
                log_event(
                    "circuit_breaker_triggered",
                    webhook_id=webhook_id,
                    user_id=user_id,
                    reason=cb_reason
                )
                risk_annotations["circuit_breaker"] = cb_reason
                # Convert guard result to SKIP
                guard_result = GuardResult(
                    decision=GuardDecision.SKIP,
                    annotations={"discard_reason": f"Circuit breaker: {cb_reason}", "circuit_breaker": True}
                )
        except Exception as cb_err:
            logger.warning(f"Circuit breaker check failed: {cb_err}")

        # 2. Equity Curve Trading Check (pause when below MA)
        if guard_result.decision == GuardDecision.EXECUTE:
            try:
                eq_status = analytics_service.get_equity_curve_status(user_id)
                # Check if equity curve filter is enabled and we're below MA
                eq_settings = db.query(DynamicSizingSettings).filter(
                    DynamicSizingSettings.user_id == user_id
                ).first()

                if eq_settings and eq_settings.equity_curve_enabled:
                    if not eq_status.get('is_above_ma', True):
                        if eq_settings.pause_below_ma:
                            log_event(
                                "equity_curve_pause",
                                webhook_id=webhook_id,
                                user_id=user_id,
                                cumulative_pnl=eq_status.get('cumulative_pnl'),
                                equity_ma=eq_status.get('equity_ma')
                            )
                            risk_annotations["equity_curve"] = "Below MA - trading paused"
                            guard_result = GuardResult(
                                decision=GuardDecision.SKIP,
                                annotations={"discard_reason": "Equity curve below MA - trading paused", "equity_curve": True}
                            )
                        else:
                            # Just reduce size, don't pause
                            risk_annotations["equity_curve"] = "Below MA - size reduced"
            except Exception as eq_err:
                logger.warning(f"Equity curve check failed: {eq_err}")

        # 3. Dynamic Position Sizing (apply multiplier based on streaks)
        if guard_result.decision == GuardDecision.EXECUTE:
            try:
                position_size_multiplier = analytics_service.get_position_size_multiplier(user_id, float(quantity))
                if position_size_multiplier != 1.0:
                    log_event(
                        "dynamic_sizing_applied",
                        webhook_id=webhook_id,
                        user_id=user_id,
                        original_quantity=float(quantity),
                        multiplier=position_size_multiplier,
                        adjusted_quantity=float(quantity) * position_size_multiplier
                    )
                    risk_annotations["position_sizing"] = f"Multiplier: {position_size_multiplier:.2f}x"
                    # Apply the multiplier to quantity
                    quantity = float(quantity) * position_size_multiplier
                    # Update signal entity volume
                    signal_entity = Signal(
                        id=signal_entity.id,
                        source=signal_entity.source,
                        symbol=signal_entity.symbol,
                        action=signal_entity.action,
                        volume=Volume(Decimal(str(quantity))),
                        price=signal_entity.price,
                        stop_loss=signal_entity.stop_loss,
                        take_profit=signal_entity.take_profit,
                        target_accounts=signal_entity.target_accounts,
                        comment=signal_entity.comment,
                        strategy_id=signal_entity.strategy_id,
                        strategy_name=signal_entity.strategy_name,
                        raw_payload=signal_entity.raw_payload,
                    )
            except Exception as ps_err:
                logger.warning(f"Position sizing check failed: {ps_err}")

        # 4. Correlation Filter Check (prevent correlated trades)
        if guard_result.decision == GuardDecision.EXECUTE:
            try:
                # Built-in correlations
                CORRELATION_PAIRS = {
                    ("ES", "NQ"): 0.92, ("NQ", "ES"): 0.92,
                    ("ES", "YM"): 0.95, ("YM", "ES"): 0.95,
                    ("NQ", "YM"): 0.90, ("YM", "NQ"): 0.90,
                    ("EURUSD", "GBPUSD"): 0.85, ("GBPUSD", "EURUSD"): 0.85,
                    ("EURUSD", "USDCHF"): -0.90, ("USDCHF", "EURUSD"): -0.90,
                    ("AUDUSD", "NZDUSD"): 0.88, ("NZDUSD", "AUDUSD"): 0.88,
                    ("USDJPY", "USDCAD"): 0.75, ("USDCAD", "USDJPY"): 0.75,
                    ("XAUUSD", "XAGUSD"): 0.85, ("XAGUSD", "XAUUSD"): 0.85,
                }

                # Check CorrelationFilterSettings for config
                from app.models.database_models import CorrelationFilterSettings
                corr_settings = db.query(CorrelationFilterSettings).filter(
                    CorrelationFilterSettings.user_id == user_id
                ).first()

                correlation_enabled = corr_settings.enabled if corr_settings else False
                max_correlation = corr_settings.max_positive_correlation if corr_settings else 0.70

                if correlation_enabled:
                    # Get current open positions
                    from app.models.models import Position
                    open_symbols = set()
                    for account in accounts:
                        positions = db.query(Position).filter(
                            Position.account_id == account.id,
                            Position.is_active == True
                        ).all()
                        for pos in positions:
                            if pos.symbol:
                                open_symbols.add(pos.symbol.upper())

                    # Check if new symbol is highly correlated with any open position
                    signal_symbol_upper = symbol.upper()
                    for open_sym in open_symbols:
                        correlation = CORRELATION_PAIRS.get((signal_symbol_upper, open_sym), 0)
                        if abs(correlation) >= max_correlation:
                            log_event(
                                "correlation_filter_blocked",
                                webhook_id=webhook_id,
                                user_id=user_id,
                                symbol=symbol,
                                correlated_with=open_sym,
                                correlation=correlation
                            )
                            risk_annotations["correlation_filter"] = f"Blocked: {symbol} correlated with {open_sym} ({correlation*100:.0f}%)"
                            guard_result = GuardResult(
                                decision=GuardDecision.SKIP,
                                annotations={"discard_reason": f"Correlation filter: {symbol} highly correlated with open position {open_sym}", "correlation_filter": True}
                            )
                            break
            except Exception as cf_err:
                logger.warning(f"Correlation filter check failed: {cf_err}")

        # Log risk annotations if any
        if risk_annotations:
            log_event(
                "risk_management_applied",
                webhook_id=webhook_id,
                user_id=user_id,
                annotations=risk_annotations
            )

    # Handle guard decisions
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    if guard_result.decision == GuardDecision.SKIP:
        # Signal discarded (stale, etc.)
        guard_reason = guard_result.annotations.get("discard_reason") or guard_result.annotations.get("history_tag") or "guard_rejected"
        try:
            webhook_log.processed = False
            webhook_log.response_status = 200
            webhook_log.processing_time_ms = processing_time_ms
            webhook_log.response_body = json.dumps({
                "signal_id": signal_entity.id.value,
                "status": "rejected",
                "guard_decision": "skip",
                "guard_reason": guard_reason,
                "total_accounts": len(accounts),
                "successful": 0,
                "failed": len(accounts),
            })
            db.commit()

            # Create ExecutionLog entries for each account showing the rejection
            for account in accounts:
                try:
                    broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)
                    models_broker = ModelsBrokerType(broker_str.lower())
                    exec_log = ExecutionLog(
                        signal_id=signal_entity.id.value,
                        account_id=account.id,
                        broker=models_broker,
                        action=action_str.upper(),
                        symbol=symbol,
                        volume=float(quantity),
                        status="failed",
                        error_message=f"Guard rejected: {guard_reason}",
                        execution_time_ms=processing_time_ms,
                    )
                    db.add(exec_log)
                except Exception as e:
                    logger.warning(f"Failed to create rejection ExecutionLog: {e}")
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to update webhook_log for SKIP: {e}")

        # Update WebhookConfig stats for SKIP/rejected
        try:
            webhook_config = db.query(WebhookConfig).filter(
                WebhookConfig.webhook_key == webhook_key
            ).first()
            if webhook_config:
                webhook_config.total_signals = (webhook_config.total_signals or 0) + 1
                webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
                webhook_config.last_signal_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to update WebhookConfig stats for SKIP: {e}")
            db.rollback()

        return ExecuteResponse(
            success=False,
            signal_id=signal_entity.id.value,
            status="rejected",
            webhook_id=webhook_id,
            routing_strategy=routing_strategy,
            routing_reason=routing_reason,
            total_accounts=len(accounts),
            account_id=first_account.id,
            broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
            guard_decision="skip",
            guard_reason=guard_result.annotations.get("discard_reason", "guard_rejected"),
            processing_time_ms=processing_time_ms
        )

    if guard_result.decision == GuardDecision.WARN_MODAL_REQUIRED:
        # Check if any account has auto_confirm enabled - if so, skip the modal
        all_auto_confirm = all(getattr(a, 'auto_confirm', True) for a in accounts)
        if all_auto_confirm:
            # Auto-confirm enabled, proceed without modal
            logger.info(f"Auto-confirm enabled for all accounts, bypassing guard modal")
            guard_result = type(guard_result)(
                decision=GuardDecision.EXECUTE,
                annotations=guard_result.annotations
            )
        else:
            # Needs user confirmation
            try:
                webhook_log.processed = False
                webhook_log.response_status = 202
                webhook_log.response_body = json.dumps({"status": "pending_confirmation"})
                webhook_log.processing_time_ms = processing_time_ms
                db.commit()
            except:
                pass

            # Persist signal for UI confirmation flow
            try:
                existing_signal = db.query(SignalORM).filter(
                    SignalORM.signal_id == signal_entity.id.value
                ).first()
                if not existing_signal:
                    db_signal = SignalORM(
                        signal_id=signal_entity.id.value,
                        user_id=first_account.user_id,
                        source=ModelsSignalSource.TRADINGVIEW,
                        symbol=symbol,
                        action=action_str,
                        volume=float(quantity),
                        price=None,
                        stop_loss=float(sl_price) if sl_price else None,
                        take_profit=float(tp_price) if tp_price else None,
                        comment=raw_payload.get("comment"),
                        status="pending_confirmation",
                        target_accounts=[a.id for a in accounts],
                        raw_payload=raw_payload,
                        signal_data={
                            "guard_decision": "warn",
                            "guard_reason": guard_result.annotations.get("history_tag", "momentum_warning"),
                            "annotations": guard_result.annotations,
                            "modal_data": guard_result.modal_data,
                            "routing_strategy": routing_strategy,
                        },
                        strategy_id=raw_payload.get("strategy_id"),
                    )
                    db.add(db_signal)
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist pending confirmation signal: {e}")

            return ExecuteResponse(
                success=False,
                signal_id=signal_entity.id.value,
                status="pending_confirmation",
                webhook_id=webhook_id,
                routing_strategy=routing_strategy,
                routing_reason=routing_reason,
                total_accounts=len(accounts),
                account_id=first_account.id,
                broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
                guard_decision="warn",
                guard_reason=guard_result.annotations.get("history_tag", "momentum_warning"),
                modal_data=guard_result.modal_data,
                processing_time_ms=processing_time_ms
            )

    if guard_result.decision == GuardDecision.PAUSE_NEW_ENTRIES:
        # Paused - don't execute new entries
        if action != SignalAction.CLOSE:
            guard_reason = guard_result.annotations.get("history_tag") or "paused_new_entries"
            try:
                webhook_log.processed = False
                webhook_log.response_status = 200
                webhook_log.processing_time_ms = processing_time_ms
                webhook_log.response_body = json.dumps({
                    "signal_id": signal_entity.id.value,
                    "status": "paused",
                    "guard_decision": "pause",
                    "guard_reason": guard_reason,
                    "total_accounts": len(accounts),
                    "successful": 0,
                    "failed": len(accounts),
                })
                db.commit()

                # Create ExecutionLog entries for each account showing the pause
                for account in accounts:
                    try:
                        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)
                        models_broker = ModelsBrokerType(broker_str.lower())
                        exec_log = ExecutionLog(
                            signal_id=signal_entity.id.value,
                            account_id=account.id,
                            broker=models_broker,
                            action=action_str.upper(),
                            symbol=symbol,
                            volume=float(quantity),
                            status="failed",
                            error_message=f"Paused: {guard_reason}",
                            execution_time_ms=processing_time_ms,
                        )
                        db.add(exec_log)
                    except Exception as e:
                        logger.warning(f"Failed to create pause ExecutionLog: {e}")
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to update webhook_log for PAUSE: {e}")

            # Update WebhookConfig stats for PAUSE
            try:
                webhook_config = db.query(WebhookConfig).filter(
                    WebhookConfig.webhook_key == webhook_key
                ).first()
                if webhook_config:
                    webhook_config.total_signals = (webhook_config.total_signals or 0) + 1
                    webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
                    webhook_config.last_signal_at = datetime.utcnow()
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to update WebhookConfig stats for PAUSE: {e}")
                db.rollback()

            return ExecuteResponse(
                success=False,
                signal_id=signal_entity.id.value,
                status="paused",
                webhook_id=webhook_id,
                routing_strategy=routing_strategy,
                routing_reason=routing_reason,
                total_accounts=len(accounts),
                account_id=first_account.id,
                broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
                guard_decision="pause",
                guard_reason=guard_reason,
                modal_data=guard_result.modal_data,
                processing_time_ms=processing_time_ms
            )

    # === EXECUTE ON ALL TARGET ACCOUNTS ===
    # Guard passed - execute the signal on all routed accounts using account-specific executors
    account_results: List[AccountExecutionResult] = []
    all_errors: List[str] = []
    successful_count = 0
    failed_count = 0

    # Import the account-specific executor creation
    from app.services.signal_processor import _create_account_executor
    from app.models.pydantic_schemas import OrderRequest

    # Initialize counter service for max_daily_trades enforcement
    counter_repo = get_daily_counter_repository()
    counter_service = DailyCounterService(counter_repo)

    # === PRE-AGGREGATE POSITIONS FOR MULTI-ACCOUNT BROKERS ===
    # For ProjectX/TopStep, we need to check position limits ACROSS ALL sub-accounts,
    # not per sub-account. Otherwise, max_positions_per_symbol=3 would allow 3*N positions
    # where N is the number of enabled broker sub-accounts.
    #
    # This section pre-fetches positions from ALL enabled sub-accounts and stores aggregated
    # counts that we use in the position check section below.

    # Helper to normalize symbol for position matching (same as below, extracted for pre-aggregation)
    import re
    def _normalize_symbol_for_aggregation(sym: str) -> str:
        """Normalize symbol for matching (strip suffixes, contract codes)."""
        if not sym:
            return ""
        s = sym.upper().strip()
        # Handle ProjectX CON.F.US.XXX.YYY format (e.g., CON.F.US.MYM.H26 -> MYM)
        if s.startswith('CON.'):
            parts = s.split('.')
            if len(parts) >= 4:
                s = parts[3]  # e.g., "MYM" from "CON.F.US.MYM.H26"
        # Strip common suffixes
        for suffix in ['.PRO', '.RAW', '.STD', '.I', '.S', '_SB', '.SB']:
            if s.endswith(suffix):
                s = s[:-len(suffix)]
        # Strip futures contract month/year codes (e.g., H5, Z24, H25)
        futures_pattern = re.compile(r'^([A-Z]+[A-Z0-9]*?)([FGHJKMNQUVXZ])(\d{1,4})$')
        match = futures_pattern.match(s)
        if match:
            s = match.group(1)
        # Strip trailing "1!" format from TradingView
        if s.endswith('1!'):
            s = s[:-2]
        return s

    # Dictionary to store aggregated positions per TradingAccount
    # Format: {account_id: {"total": int, "by_symbol": {normalized_symbol: count}}}
    aggregated_positions: Dict[int, Dict[str, Any]] = {}

    for account in accounts:
        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)

        # Only pre-aggregate for ProjectX/TopStep with multiple enabled broker accounts
        if broker_str in ("projectx", "topstep") and account.enabled_broker_account_ids and len(account.enabled_broker_account_ids) > 1:
            logger.info(f"Account {account.id} ({broker_str}): Pre-aggregating positions across {len(account.enabled_broker_account_ids)} sub-accounts...")

            all_positions = []
            symbol_counts: Dict[str, int] = {}

            for broker_acct_id in account.enabled_broker_account_ids:
                try:
                    # Create executor for this specific sub-account
                    executor, needs_cleanup = await _create_account_executor(account, db, broker_acct_id)
                    if not executor:
                        logger.warning(f"Account {account.id}: Could not create executor for sub-account {broker_acct_id}")
                        continue

                    # Ensure connected
                    is_conn_attr = getattr(executor, 'is_connected', None)
                    is_connected = is_conn_attr() if callable(is_conn_attr) else bool(is_conn_attr)
                    if not is_connected:
                        try:
                            await executor.initialize()
                        except Exception as init_err:
                            logger.warning(f"Executor init warning for sub-account {broker_acct_id}: {init_err}")

                    # Fetch positions with timeout
                    try:
                        positions = await asyncio.wait_for(
                            executor.get_positions(),
                            timeout=10.0
                        )
                        if positions:
                            logger.info(f"Account {account.id}, sub-account {broker_acct_id}: Found {len(positions)} positions")
                            all_positions.extend(positions)
                    except asyncio.TimeoutError:
                        logger.error(f"Account {account.id}, sub-account {broker_acct_id}: get_positions() timed out")
                    except Exception as e:
                        logger.error(f"Account {account.id}, sub-account {broker_acct_id}: get_positions() failed: {e}")

                    # Cleanup executor
                    if needs_cleanup and hasattr(executor, 'disconnect'):
                        try:
                            await executor.disconnect()
                        except:
                            pass

                except Exception as e:
                    logger.error(f"Account {account.id}: Error fetching positions for sub-account {broker_acct_id}: {e}")

            # Count positions by normalized symbol
            for p in all_positions:
                if isinstance(p, dict):
                    pos_symbol = p.get('symbol', '')
                else:
                    pos_symbol = getattr(p, 'symbol', '')
                normalized = _normalize_symbol_for_aggregation(pos_symbol)
                if normalized:
                    symbol_counts[normalized] = symbol_counts.get(normalized, 0) + 1

            aggregated_positions[account.id] = {
                "total": len(all_positions),
                "by_symbol": symbol_counts
            }
            logger.info(f"Account {account.id}: Aggregated {len(all_positions)} total positions across all sub-accounts. By symbol: {symbol_counts}")

    # === EXPAND MULTI-ACCOUNT BROKERS ===
    # For ProjectX/TopStep, a single TradingAccount can have multiple enabled_broker_account_ids
    # We need to execute on ALL enabled broker accounts, not just the default
    execution_targets: List[tuple] = []  # List of (account, broker_account_id) tuples
    for account in accounts:
        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)

        # For ProjectX/TopStep with multiple enabled broker accounts
        if broker_str in ("projectx", "topstep") and account.enabled_broker_account_ids:
            normalized_targets = []
            invalid_targets = []
            for raw_target in account.enabled_broker_account_ids:
                normalized_target = _normalize_execution_target_broker_account_id(raw_target)
                if normalized_target:
                    normalized_targets.append(normalized_target)
                else:
                    invalid_targets.append(raw_target)

            if invalid_targets:
                logger.warning(
                    "Skipping invalid broker subaccounts for account %s (%s): %s",
                    account.id,
                    broker_str,
                    invalid_targets,
                )

            if normalized_targets:
                for broker_acct_id in normalized_targets:
                    execution_targets.append((account, broker_acct_id))
                    logger.info(
                        "Expanded execution target: parent_account=%s broker=%s subaccount=%s",
                        account.id,
                        broker_str,
                        broker_acct_id,
                    )
                continue

            logger.warning(
                "No valid broker subaccounts found for account %s (%s); falling back to parent target",
                account.id,
                broker_str,
            )

        # Single execution target (default behavior)
        execution_targets.append((account, None))

    total_execution_targets = len(execution_targets)
    logger.info(f"Execution targets: {total_execution_targets} (expanded from {len(accounts)} accounts)")

    # Track which accounts have passed cooldown check for this signal
    # This prevents cooldown from blocking sub-accounts within the same signal
    cooldown_checked_accounts: set = set()

    for account, target_broker_account_id in execution_targets:
        account_start = datetime.utcnow()
        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)
        target_label = _execution_target_label(account.id, broker_str, target_broker_account_id)
        target_key = _execution_target_key(account.id, target_broker_account_id)

        # === RISK MANAGEMENT ENFORCEMENT (only for non-close actions) ===
        risk_mgmt_enabled = getattr(account, 'risk_management_enabled', True)
        if risk_mgmt_enabled is None:
            risk_mgmt_enabled = True
        if action_str != "close" and risk_mgmt_enabled:
            rejection_reason = None

            try:
                # Get daily counters for this account
                counters = await counter_service.get_counters(account.id)

                # 1. MAX DAILY TRADES CHECK
                if account.max_daily_trades and counters.trades_executed >= account.max_daily_trades:
                    rejection_reason = f"Max daily trades exceeded ({counters.trades_executed}/{account.max_daily_trades})"

                # 2. TRADE COOLDOWN CHECK
                # Skip cooldown for sub-accounts if this account already passed cooldown in this signal
                # This allows all ProjectX/TopStep sub-accounts to execute together
                if not rejection_reason and account.trade_cooldown_seconds and counters.last_trade_at:
                    if account.id not in cooldown_checked_accounts:
                        # Use local time for comparison (DB stores local time as naive datetime)
                        now_local = datetime.now()
                        last_trade = counters.last_trade_at
                        # Strip timezone info if present to compare naive datetimes
                        if last_trade.tzinfo is not None:
                            last_trade = last_trade.replace(tzinfo=None)
                        elapsed = (now_local - last_trade).total_seconds()
                        if elapsed < account.trade_cooldown_seconds:
                            remaining = int(account.trade_cooldown_seconds - elapsed)
                            rejection_reason = f"Trade cooldown active ({remaining}s remaining of {account.trade_cooldown_seconds}s)"
                        else:
                            # Cooldown passed - mark this account as checked for this signal
                            cooldown_checked_accounts.add(account.id)
                    # If already in cooldown_checked_accounts, skip the cooldown check (allow execution)

                # 2.5 MAX DAILY LOSS CHECK ($ and %)
                if not rejection_reason and (account.max_daily_loss or account.max_daily_loss_pct):
                    try:
                        today = date_type.today()
                        daily_pnl = db.query(DailyPnL).filter(
                            DailyPnL.account_id == account.id,
                            DailyPnL.date == today
                        ).first()

                        if daily_pnl and daily_pnl.total_pnl is not None:
                            # total_pnl is negative when losing money
                            current_loss = abs(min(0, daily_pnl.total_pnl))  # Convert to positive loss value

                            # Check absolute $ loss limit
                            if account.max_daily_loss and current_loss >= account.max_daily_loss:
                                rejection_reason = f"Max daily loss exceeded (${current_loss:.2f} >= ${account.max_daily_loss:.2f})"
                                logger.warning(f"Account {account.id}: Daily loss limit hit - halting trades")

                            # Check percentage loss limit
                            elif account.max_daily_loss_pct and daily_pnl.starting_balance and daily_pnl.starting_balance > 0:
                                loss_pct = (current_loss / daily_pnl.starting_balance) * 100
                                if loss_pct >= account.max_daily_loss_pct:
                                    rejection_reason = f"Max daily loss % exceeded ({loss_pct:.2f}% >= {account.max_daily_loss_pct:.2f}%)"
                                    logger.warning(f"Account {account.id}: Daily loss % limit hit - halting trades")
                    except Exception as daily_loss_err:
                        logger.debug(f"Could not check daily loss for account {account.id}: {daily_loss_err}")

                # 2.55 MAX DAILY PROFIT CHECK ($ and %) - profit target halt
                if not rejection_reason and (account.max_daily_profit or account.max_daily_profit_pct):
                    try:
                        today = date_type.today()
                        daily_pnl = db.query(DailyPnL).filter(
                            DailyPnL.account_id == account.id,
                            DailyPnL.date == today
                        ).first()

                        if daily_pnl and daily_pnl.total_pnl is not None:
                            # total_pnl is positive when making profit
                            current_profit = max(0, daily_pnl.total_pnl)  # Only consider positive PnL

                            # Check absolute $ profit target
                            if account.max_daily_profit and current_profit >= account.max_daily_profit:
                                rejection_reason = f"Daily profit target reached (${current_profit:.2f} >= ${account.max_daily_profit:.2f}) - trading halted"
                                logger.info(f"Account {account.id}: Daily profit target hit - halting trades to protect gains")

                            # Check percentage profit target
                            elif account.max_daily_profit_pct and daily_pnl.starting_balance and daily_pnl.starting_balance > 0:
                                profit_pct = (current_profit / daily_pnl.starting_balance) * 100
                                if profit_pct >= account.max_daily_profit_pct:
                                    rejection_reason = f"Daily profit target % reached ({profit_pct:.2f}% >= {account.max_daily_profit_pct:.2f}%) - trading halted"
                                    logger.info(f"Account {account.id}: Daily profit target % hit - halting trades to protect gains")
                    except Exception as daily_profit_err:
                        logger.debug(f"Could not check daily profit for account {account.id}: {daily_profit_err}")

                # 2.6 MAX DRAWDOWN CHECK
                if not rejection_reason and account.max_drawdown_pct:
                    try:
                        # Get latest equity snapshot for drawdown calculation
                        equity_snapshot = db.query(AccountEquityHistory).filter(
                            AccountEquityHistory.account_id == account.id
                        ).order_by(AccountEquityHistory.timestamp.desc()).first()

                        if equity_snapshot and equity_snapshot.drawdown_pct is not None:
                            if equity_snapshot.drawdown_pct >= account.max_drawdown_pct:
                                rejection_reason = f"Max drawdown exceeded ({equity_snapshot.drawdown_pct:.2f}% >= {account.max_drawdown_pct:.2f}%)"
                                logger.warning(f"Account {account.id}: Max drawdown limit hit - halting trades")
                    except Exception as drawdown_err:
                        logger.debug(f"Could not check drawdown for account {account.id}: {drawdown_err}")

                # 3. MAX OPEN POSITIONS CHECK (requires executor to get live positions)
                # Note: We'll check this after executor initialization below

            except Exception as e:
                logger.warning(f"Failed to check risk counters for account {account.id}: {e}")

            # If rejected by counter-based checks, skip this account
            if rejection_reason:
                logger.warning(f"Account {account.id}: {rejection_reason}")

                # Log the rejection
                models_broker = ModelsBrokerType(broker_str.lower())
                execution_log = ExecutionLog(
                    account_id=account.id,
                    signal_id=signal_entity.id.value,
                    broker=models_broker,
                    symbol=symbol,
                    action=action_str,
                    volume=quantity,
                    status="rejected",
                    error_message=rejection_reason,
                    execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000),
                )
                db.add(execution_log)
                db.commit()

                # Add to results
                account_results.append(AccountExecutionResult(
                    account_id=account.id,
                    broker=broker_str,
                    success=False,
                    status="rejected",
                    error=rejection_reason,
                    target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                    target_label=target_label,
                ))
                failed_count += 1
                all_errors.append(rejection_reason)
                continue  # Skip to next account

        # Resolve symbol for this specific broker (symbol mapping)
        # Do this early so it's available for both execution and logging
        mapped_symbol = resolve_symbol_for_broker(
            db=db,
            user_id=account.user_id,
            source_symbol=symbol,
            broker_type=broker_str
        )

        # === DUPLICATE TRADE DEDUPLICATION ===
        if action_str != "close":
            try:
                dedup_window_start = datetime.utcnow() - timedelta(seconds=5)
                recent_executions = db.query(ExecutionLog).filter(
                    ExecutionLog.account_id == account.id,
                    ExecutionLog.symbol == mapped_symbol,
                    ExecutionLog.action.in_([action_str.upper(), action_str.lower()]),
                    ExecutionLog.created_at >= dedup_window_start
                ).all()
                duplicate_execution = None
                for recent_execution in recent_executions:
                    broker_response = recent_execution.broker_response or {}
                    recent_target = None
                    if isinstance(broker_response, dict):
                        recent_target = broker_response.get("target_broker_account_id")
                    if _execution_target_key(account.id, recent_target) == target_key:
                        duplicate_execution = recent_execution
                        break
                if duplicate_execution:
                    dedup_reason = f"Duplicate trade detected within 5 seconds for {target_label}"
                    logger.warning("%s: %s %s", target_label, dedup_reason, mapped_symbol)
                    account_results.append(AccountExecutionResult(
                        account_id=account.id,
                        broker=broker_str,
                        success=False,
                        status="duplicate",
                        error=dedup_reason,
                        target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                        target_label=target_label,
                    ))
                    failed_count += 1
                    all_errors.append(f"{target_label}: {dedup_reason}")
                    continue
            except Exception as dedup_err:
                logger.warning("Deduplication check failed for %s: %s", target_label, dedup_err)

        # Initialize SL/TP/trailing_stop variables (before try block for exception handler access)
        account_sl_price = sl_price
        account_tp_price = tp_price
        account_trailing_stop = trailing_stop
        entry_price = None
        order_quantity = quantity  # Will be adjusted for futures brokers in the else block

        try:
            capability_error = _is_obviously_unsupported_for_broker(mapped_symbol, broker_str)
            if capability_error:
                logger.warning("Capability gate rejected %s symbol=%s mapped_symbol=%s reason=%s", target_label, symbol, mapped_symbol, capability_error)
                raise Exception(capability_error)

            # Create account-specific executor with credentials
            # Pass target_broker_account_id for multi-account brokers like ProjectX
            executor, needs_cleanup = await _create_account_executor(account, db, target_broker_account_id)

            if not executor:
                raise Exception(f"Could not create executor for {broker_str}")

            # Ensure executor is initialized
            # Note: is_connected is a method in most executors, so call it if it's callable
            is_conn_attr = getattr(executor, 'is_connected', None)
            is_connected = is_conn_attr() if callable(is_conn_attr) else bool(is_conn_attr)
            if not is_connected:
                try:
                    logger.debug(f"Account {account.id}: Executor not connected, calling initialize()")
                    await executor.initialize()
                except Exception as init_err:
                    logger.warning(f"Executor init warning for account {account.id}: {init_err}")

            # === POSITION-BASED RISK CHECKS (only for non-close actions) ===
            if action_str != "close":
                position_rejection = None
                try:
                    # Get current open positions from broker with timeout
                    logger.info(f"Account {account.id} ({broker_str}): Starting position check...")
                    try:
                        current_positions = await asyncio.wait_for(
                            executor.get_positions(),
                            timeout=10.0  # 10 second timeout for position check
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"Account {account.id} ({broker_str}): get_positions() TIMED OUT after 10s")
                        current_positions = []
                    total_positions = len(current_positions) if current_positions else 0

                    # DEBUG: Log positions returned by broker for troubleshooting
                    logger.info(f"Account {account.id} ({broker_str}): get_positions() returned {total_positions} positions")
                    if current_positions and total_positions > 0:
                        for idx, p in enumerate(current_positions[:5]):  # Log first 5
                            p_symbol = getattr(p, 'symbol', None) or (p.get('symbol') if isinstance(p, dict) else 'UNKNOWN')
                            p_side = getattr(p, 'side', None) or (p.get('side') if isinstance(p, dict) else '?')
                            logger.debug(f"  Position[{idx}]: symbol={p_symbol}, side={p_side}")

                    # SYNC: Reconcile database positions with broker (clean up stale positions)
                    try:
                        sync_result = await sync_positions_before_check(
                            db, account.id, current_positions, force=False
                        )
                        if sync_result.get('stale_closed', 0) > 0:
                            logger.info(
                                f"Account {account.id}: Position sync cleaned up {sync_result['stale_closed']} "
                                f"stale DB positions (broker has {total_positions})"
                            )
                    except Exception as sync_err:
                        logger.warning(f"Account {account.id}: Position sync failed (non-fatal): {sync_err}")

                    # Helper to get attribute from dict or object
                    def get_pos_attr(obj, key, default=''):
                        if isinstance(obj, dict):
                            return obj.get(key, default)
                        return getattr(obj, key, default)

                    # Helper to normalize symbol for position matching
                    def normalize_symbol_for_match(sym: str) -> str:
                        """Normalize symbol for matching (strip suffixes, contract codes)."""
                        if not sym:
                            return ""
                        import re
                        s = sym.upper().strip()
                        # Handle ProjectX CON.F.US.XXX.YYY format (e.g., CON.F.US.MYM.H26 -> MYM)
                        if s.startswith('CON.'):
                            parts = s.split('.')
                            if len(parts) >= 4:
                                s = parts[3]  # e.g., "MYM" from "CON.F.US.MYM.H26"
                        # Strip common suffixes
                        for suffix in ['.PRO', '.RAW', '.STD', '.I', '.S', '_SB', '.SB']:
                            if s.endswith(suffix):
                                s = s[:-len(suffix)]
                        # Strip futures contract month/year codes (e.g., H5, Z24, H25)
                        futures_pattern = re.compile(r'^([A-Z]+[A-Z0-9]*?)([FGHJKMNQUVXZ])(\d{1,4})$')
                        match = futures_pattern.match(s)
                        if match:
                            s = match.group(1)
                        # Strip trailing "1!" format from TradingView
                        if s.endswith('1!'):
                            s = s[:-2]
                        return s

                    # Normalize our target symbols for matching
                    normalized_signal_symbol = normalize_symbol_for_match(symbol)
                    normalized_mapped_symbol = normalize_symbol_for_match(mapped_symbol)

                    # 3. MAX OPEN POSITIONS CHECK (with race condition prevention)
                    # For ProjectX with multiple sub-accounts, use pre-aggregated counts
                    use_aggregated = account.id in aggregated_positions
                    if use_aggregated:
                        agg_data = aggregated_positions[account.id]
                        agg_total = agg_data["total"]
                        agg_by_symbol = agg_data["by_symbol"]
                        logger.info(f"Account {account.id}: Using AGGREGATED position counts - total={agg_total}, by_symbol={agg_by_symbol}")
                    else:
                        agg_total = total_positions
                        agg_by_symbol = {}

                    if account.max_open_positions:
                        # Add pending orders that haven't been confirmed yet
                        pending_total_count = _pending_total_tracker.get_pending_count(account.id)
                        # Use aggregated total for multi-account brokers
                        effective_total = agg_total if use_aggregated else total_positions
                        total_with_pending = effective_total + pending_total_count

                        if total_with_pending >= account.max_open_positions:
                            # Enhanced logging: Show actual broker positions for debugging
                            broker_symbols = []
                            for p in (current_positions or [])[:10]:  # First 10
                                p_sym = getattr(p, 'symbol', None) or (p.get('symbol') if isinstance(p, dict) else '?')
                                broker_symbols.append(p_sym)
                            logger.warning(
                                f"Account {account.id}: MAX POSITIONS REJECTION - "
                                f"total_with_pending={total_with_pending}, max={account.max_open_positions}, "
                                f"broker_returned={total_positions}, pending_tracker={pending_total_count}, "
                                f"broker_symbols={broker_symbols}"
                            )
                            position_rejection = f"Max open positions exceeded ({total_with_pending}/{account.max_open_positions}, aggregated={effective_total}, pending={pending_total_count})"
                        else:
                            # Reserve a slot by incrementing pending counter BEFORE placing order
                            _pending_total_tracker.increment(account.id)
                            logger.info(f"Account {account.id}: Total position check passed ({effective_total} aggregated + {pending_total_count + 1} pending / {account.max_open_positions} max)")

                    # 4. MAX POSITIONS PER SYMBOL CHECK (with race condition prevention)
                    if not position_rejection and account.max_positions_per_symbol:
                        # For ProjectX with multiple sub-accounts, use pre-aggregated symbol counts
                        if use_aggregated:
                            # Use pre-aggregated counts - check both signal and mapped symbol
                            broker_position_count = max(
                                agg_by_symbol.get(normalized_signal_symbol, 0),
                                agg_by_symbol.get(normalized_mapped_symbol, 0)
                            )
                            logger.info(f"Account {account.id}: Using AGGREGATED symbol count for {symbol}: {broker_position_count} (signal_norm={normalized_signal_symbol}, mapped_norm={normalized_mapped_symbol})")
                        else:
                            # Count existing positions matching this symbol using normalized comparison
                            symbol_positions = []
                            logger.debug(f"Account {account.id}: Checking symbol limit - signal={symbol}, mapped={mapped_symbol}, normalized_signal={normalized_signal_symbol}, normalized_mapped={normalized_mapped_symbol}")
                            for p in (current_positions or []):
                                pos_symbol = get_pos_attr(p, 'symbol', '') or ''
                                normalized_pos_symbol = normalize_symbol_for_match(pos_symbol)
                                logger.debug(f"  Comparing: pos_symbol={pos_symbol} -> normalized={normalized_pos_symbol} vs signal={normalized_signal_symbol}")
                                # Match if normalized symbols are equal (not substring!)
                                if normalized_pos_symbol == normalized_signal_symbol or normalized_pos_symbol == normalized_mapped_symbol:
                                    symbol_positions.append(p)
                                    logger.debug(f"  -> MATCHED!")
                            broker_position_count = len(symbol_positions)
                            logger.info(f"Account {account.id}: Symbol check for {symbol}: found {broker_position_count} matching positions out of {total_positions} total")

                        # Add pending orders that haven't been confirmed yet (race condition prevention)
                        # Use normalized_mapped_symbol as key so MYM1! and MYMH5 share the same counter
                        pending_count = _pending_tracker.get_pending_count(account.id, normalized_mapped_symbol)
                        total_symbol_positions = broker_position_count + pending_count

                        if total_symbol_positions >= account.max_positions_per_symbol:
                            position_rejection = f"Max positions for {symbol} exceeded ({total_symbol_positions}/{account.max_positions_per_symbol}, aggregated={broker_position_count}, pending={pending_count})"
                        else:
                            # Reserve a slot by incrementing pending counter BEFORE placing order
                            _pending_tracker.increment(account.id, normalized_mapped_symbol)
                            logger.info(f"Account {account.id}: Symbol position check passed for {mapped_symbol} ({broker_position_count} aggregated + {pending_count + 1} pending / {account.max_positions_per_symbol} max)")

                except Exception as pos_err:
                    logger.error(f"Failed to check positions for account {account.id}: {pos_err} — rejecting as fail-safe")
                    position_rejection = f"Position check failed (cannot verify limits): {pos_err}"

                # If rejected by position checks, skip this account
                if position_rejection:
                    logger.warning(f"Account {account.id}: {position_rejection}")

                    # Cleanup executor
                    if needs_cleanup and hasattr(executor, 'disconnect'):
                        try:
                            await executor.disconnect()
                        except:
                            pass

                    models_broker = ModelsBrokerType(broker_str.lower())
                    execution_log = ExecutionLog(
                        account_id=account.id,
                        signal_id=signal_entity.id.value,
                        broker=models_broker,
                        symbol=symbol,
                        action=action_str,
                        volume=quantity,
                        status="rejected",
                        error_message=position_rejection,
                        execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000),
                    )
                    db.add(execution_log)
                    db.commit()

                    account_results.append(AccountExecutionResult(
                        account_id=account.id,
                        broker=broker_str,
                        success=False,
                        status="rejected",
                        error=position_rejection,
                        target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                        target_label=target_label,
                    ))
                    failed_count += 1
                    all_errors.append(position_rejection)
                    continue  # Skip to next account

            # Handle close action separately - need to find and close positions
            if action_str == "close":
                # Helper to get attribute from dict or object
                def get_attr(obj, key, default=''):
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    return getattr(obj, key, default)

                # Helper to normalize symbol for matching (strip suffixes like .pro, .i, etc)
                def normalize_for_match(sym: str) -> str:
                    if not sym:
                        return ""
                    import re
                    s = sym.upper().strip()
                    # Strip common suffixes
                    for suffix in ['.PRO', '.RAW', '.STD', '.I', '.S', '_SB', '.SB']:
                        if s.endswith(suffix):
                            s = s[:-len(suffix)]
                    # Strip futures contract month/year codes (e.g., H5, Z24, H25, M2025)
                    # Futures months: F(Jan), G(Feb), H(Mar), J(Apr), K(May), M(Jun),
                    #                 N(Jul), Q(Aug), U(Sep), V(Oct), X(Nov), Z(Dec)
                    # Pattern: base symbol + month letter + 1-4 digit year
                    futures_pattern = re.compile(r'^([A-Z]+[A-Z0-9]*?)([FGHJKMNQUVXZ])(\d{1,4})$')
                    match = futures_pattern.match(s)
                    if match:
                        s = match.group(1)  # Return just the base symbol
                    # Also handle trailing "1!" format from TradingView (e.g., MNQ1!, ES1!)
                    if s.endswith('1!'):
                        s = s[:-2]
                    return s

                # Get positions and close matching ones (check both original and mapped symbol)
                try:
                    positions = await executor.get_positions()

                    # Normalize both search symbols
                    norm_symbol = normalize_for_match(symbol)
                    norm_mapped = normalize_for_match(mapped_symbol)

                    # Log for debugging close matching
                    logger.info(f"Close matching: symbol={symbol}, mapped={mapped_symbol}, positions={len(positions or [])}")
                    for p in (positions or []):
                        pos_sym = get_attr(p, 'symbol', '')
                        logger.debug(f"  Position: id={get_attr(p, 'id', '')}, symbol={pos_sym}")

                    matching_positions = []
                    for p in (positions or []):
                        pos_sym = get_attr(p, 'symbol', '') or ''
                        norm_pos = normalize_for_match(pos_sym)

                        # Check various matching conditions
                        if (norm_symbol and norm_symbol in norm_pos) or \
                           (norm_symbol and norm_pos in norm_symbol) or \
                           (norm_mapped and norm_mapped in norm_pos) or \
                           (norm_mapped and norm_pos in norm_mapped) or \
                           (norm_symbol == norm_pos) or \
                           (norm_mapped == norm_pos):
                            matching_positions.append(p)
                            logger.info(f"  MATCHED: {pos_sym} (normalized: {norm_pos})")

                    if not matching_positions:
                        # No positions to close - treat as SUCCESS since position likely
                        # already closed via TP/SL on broker side (expected behavior)
                        logger.info(f"No matching positions to close for {symbol} - position likely already closed via TP/SL")
                        order_result = type('Result', (), {
                            'success': True,
                            'order_id': 'already_closed',
                            'error': None,
                            'message': 'Position already closed (likely via TP/SL)',
                            'closed_positions': []
                        })()
                    else:
                        # Close each matching position
                        closed = 0
                        close_errors = []
                        closed_positions_info = []  # Track closed positions for P&L
                        for pos in matching_positions:
                            pos_id = get_attr(pos, 'id') or get_attr(pos, 'position_id') or get_attr(pos, 'contract_id')
                            if pos_id:
                                # Capture position info BEFORE closing
                                pos_entry_price = float(get_attr(pos, 'entry_price', 0) or get_attr(pos, 'averagePrice', 0) or get_attr(pos, 'avgPrice', 0) or 0)
                                pos_volume = float(get_attr(pos, 'volume', 0) or get_attr(pos, 'qty', 0) or get_attr(pos, 'quantity', 0) or get_attr(pos, 'size', 0) or 0)
                                pos_side = str(get_attr(pos, 'side', '') or get_attr(pos, 'direction', '') or '').lower()
                                pos_unrealized_pnl = float(get_attr(pos, 'unrealized_pnl', 0) or get_attr(pos, 'unrealizedPnl', 0) or get_attr(pos, 'pnl', 0) or 0)
                                pos_current_price = float(get_attr(pos, 'currentPrice', 0) or get_attr(pos, 'lastPrice', 0) or get_attr(pos, 'price', 0) or 0)

                                # Use explicit_close_quantity if provided (partial close), otherwise None (full close)
                                close_qty = float(explicit_close_quantity) if explicit_close_quantity else None
                                close_result = await executor.close_position(str(pos_id), close_qty)
                                if close_result.success if hasattr(close_result, 'success') else close_result.get('success'):
                                    closed += 1
                                    # Get realized P&L from close result if available
                                    realized_pnl = None
                                    if hasattr(close_result, 'pnl'):
                                        realized_pnl = close_result.pnl
                                    elif isinstance(close_result, dict) and 'pnl' in close_result:
                                        realized_pnl = close_result['pnl']

                                    # Fallback to unrealized P&L if realized not available
                                    if realized_pnl is None and pos_unrealized_pnl:
                                        realized_pnl = pos_unrealized_pnl

                                    closed_positions_info.append({
                                        'position_id': str(pos_id),
                                        'entry_price': pos_entry_price,
                                        'exit_price': pos_current_price,
                                        'volume': pos_volume,
                                        'side': pos_side,
                                        'pnl': realized_pnl
                                    })
                                else:
                                    err = close_result.error if hasattr(close_result, 'error') else close_result.get('error')
                                    if err:
                                        close_errors.append(str(err))

                        order_result = type('Result', (), {
                            'success': closed > 0,
                            'order_id': f'closed_{closed}',
                            'error': '; '.join(close_errors) if close_errors and closed == 0 else None,
                            'closed_positions': closed_positions_info
                        })()
                except Exception as close_err:
                    logger.error(f"Error during close: {close_err}")
                    order_result = type('Result', (), {
                        'success': False,
                        'order_id': None,
                        'error': str(close_err)
                    })()
            else:
                # Build order request - support market, limit, and trailing stop
                effective_order_type = f"{order_type_payload}_{action_str}"  # e.g., "market_buy", "limit_sell"

                # === Calculate SL/TP from account risk settings if not in payload ===
                # Get entry price for SL/TP calculation
                # Use limit_price if limit order, otherwise try price from payload
                entry_price = limit_price or raw_payload.get("price") or raw_payload.get("entry_price")

                # Try to get current price from executor if we have settings that need entry price
                if entry_price is None and (
                    (account_sl_price is None and (account.default_stop_loss or hasattr(account, 'symbol_settings'))) or
                    (account_tp_price is None and (account.default_take_profit or hasattr(account, 'symbol_settings'))) or
                    (account_trailing_stop is None and account.trailing_stop_pips)
                ):
                    try:
                        # Try to get current market price from executor
                        if hasattr(executor, 'get_quote'):
                            quote = await executor.get_quote(mapped_symbol)
                            if quote:
                                # Use bid for sell, ask for buy
                                if action_str == "buy":
                                    entry_price = quote.get('ask') or quote.get('price')
                                else:
                                    entry_price = quote.get('bid') or quote.get('price')
                    except Exception as quote_err:
                        logger.debug(f"Could not get quote for SL/TP calculation: {quote_err}")

                # === SYMBOL-SPECIFIC SETTINGS LOOKUP ===
                # Check if there are symbol-specific SL/TP settings for this account
                symbol_sl = None
                symbol_tp = None
                symbol_sl_type = None
                symbol_tp_type = None
                try:
                    from app.models.database_models import SymbolSettings
                    symbol_upper = mapped_symbol.upper()
                    # Try multiple symbol formats for matching (XAUUSD, XAUUSD.i, XAU/USD, etc.)
                    sym_setting = db.query(SymbolSettings).filter(
                        SymbolSettings.account_id == account.id,
                        SymbolSettings.symbol == symbol_upper
                    ).first()

                    # If not found, try partial match
                    if not sym_setting:
                        all_settings = db.query(SymbolSettings).filter(
                            SymbolSettings.account_id == account.id
                        ).all()
                        for ss in all_settings:
                            ss_symbol = (ss.symbol or "").upper()
                            if ss_symbol in symbol_upper or symbol_upper in ss_symbol:
                                sym_setting = ss
                                break

                    if sym_setting:
                        symbol_sl = sym_setting.default_stop_loss
                        symbol_tp = sym_setting.default_take_profit
                        symbol_sl_type = sym_setting.sl_type
                        symbol_tp_type = sym_setting.tp_type
                        logger.info(f"Account {account.id}: Found symbol-specific settings for {symbol_upper}: SL={symbol_sl} {symbol_sl_type}, TP={symbol_tp} {symbol_tp_type}")
                except Exception as sym_err:
                    # Table might not exist yet, or other error - use account defaults
                    logger.debug(f"Could not query symbol settings (will use account defaults): {sym_err}")

                # Determine effective SL/TP values (symbol-specific > account default)
                effective_sl_value = symbol_sl if symbol_sl is not None else account.default_stop_loss
                effective_sl_type = symbol_sl_type if symbol_sl_type else (account.sl_type or "pips")
                effective_tp_value = symbol_tp if symbol_tp is not None else account.default_take_profit
                effective_tp_type = symbol_tp_type if symbol_tp_type else (account.tp_type or "pips")

                # Calculate SL from account/symbol settings if not in payload
                if account_sl_price is None and effective_sl_value and entry_price:
                    try:
                        is_buy = action_str == "buy"
                        sl_unit_mode = RiskUnitMode(effective_sl_type)

                        if sl_unit_mode == RiskUnitMode.PRICE:
                            # Already an absolute price
                            account_sl_price = effective_sl_value
                        else:
                            # Convert pips/points/percent to absolute price
                            # Use symbol-specific tick size/digits for accurate conversion
                            account_sl_price = RiskUnitConverter.convert_risk_unit_to_price(
                                value=effective_sl_value,
                                mode=sl_unit_mode,
                                entry_price=float(entry_price),
                                is_buy=is_buy,
                                is_stop_loss=True,
                                digits=RiskUnitConverter.get_digits_for_symbol(mapped_symbol, broker_str),
                                tick_size=RiskUnitConverter.get_tick_size_for_symbol(mapped_symbol, broker_str)
                            )
                        # Enhanced logging with direction validation
                        sl_direction = "below" if account_sl_price < entry_price else "above"
                        expected_sl_direction = "below" if is_buy else "above"
                        sl_ok = "✓" if sl_direction == expected_sl_direction else "✗ WRONG DIRECTION"
                        logger.info(f"Account {account.id}: Calculated SL {account_sl_price:.5f} from {effective_sl_value} {effective_sl_type} | action={action_str.upper()}, entry={entry_price:.5f}, SL is {sl_direction} entry {sl_ok}")
                    except Exception as sl_err:
                        logger.warning(f"Failed to calculate SL for account {account.id}: {sl_err}")

                # Calculate TP from account/symbol settings if not in payload
                if account_tp_price is None and effective_tp_value and entry_price:
                    try:
                        is_buy = action_str == "buy"
                        tp_unit_mode = RiskUnitMode(effective_tp_type)

                        if tp_unit_mode == RiskUnitMode.PRICE:
                            # Already an absolute price
                            account_tp_price = effective_tp_value
                        else:
                            # Convert pips/points/percent to absolute price
                            # Use symbol-specific tick size/digits for accurate conversion
                            account_tp_price = RiskUnitConverter.convert_risk_unit_to_price(
                                value=effective_tp_value,
                                mode=tp_unit_mode,
                                entry_price=float(entry_price),
                                is_buy=is_buy,
                                is_stop_loss=False,
                                digits=RiskUnitConverter.get_digits_for_symbol(mapped_symbol, broker_str),
                                tick_size=RiskUnitConverter.get_tick_size_for_symbol(mapped_symbol, broker_str)
                            )
                        # Enhanced logging with direction validation
                        tp_direction = "above" if account_tp_price > entry_price else "below"
                        expected_tp_direction = "above" if is_buy else "below"
                        tp_ok = "✓" if tp_direction == expected_tp_direction else "✗ WRONG DIRECTION"
                        logger.info(f"Account {account.id}: Calculated TP {account_tp_price:.5f} from {effective_tp_value} {effective_tp_type} | action={action_str.upper()}, entry={entry_price:.5f}, TP is {tp_direction} entry {tp_ok}")
                    except Exception as tp_err:
                        logger.warning(f"Failed to calculate TP for account {account.id}: {tp_err}")

                # Apply trailing stop from account settings if not in payload
                if account_trailing_stop is None and account.trailing_stop_pips:
                    account_trailing_stop = account.trailing_stop_pips
                    logger.info(f"Account {account.id}: Using trailing stop {account_trailing_stop} pips from settings")

                # === Position sizing enforcement ===
                # Account profile overrides webhook quantity based on position_sizing_mode
                order_quantity = quantity
                sizing_mode = getattr(account, 'position_sizing_mode', 'fixed') or 'fixed'

                if sizing_mode == 'fixed' and account.fixed_lot_size:
                    # Always use account's fixed lot size
                    order_quantity = account.fixed_lot_size
                    logger.info(f"Account {account.id}: Using fixed lot size {order_quantity} from profile")
                elif sizing_mode == 'percent_balance' and account.percent_of_balance and account.balance:
                    # Calculate lot size as % of balance (simplified: balance * pct / 100000 for forex)
                    order_quantity = round(account.balance * (account.percent_of_balance / 100) / 100000, 2)
                    if order_quantity < 0.01:
                        order_quantity = 0.01
                    logger.info(f"Account {account.id}: Calculated {order_quantity} lots from {account.percent_of_balance}% of balance ${account.balance}")
                elif sizing_mode == 'percent_equity' and account.percent_of_equity and account.equity:
                    order_quantity = round(account.equity * (account.percent_of_equity / 100) / 100000, 2)
                    if order_quantity < 0.01:
                        order_quantity = 0.01
                    logger.info(f"Account {account.id}: Calculated {order_quantity} lots from {account.percent_of_equity}% of equity ${account.equity}")

                # === Broker-specific quantity normalization ===
                # Futures brokers (projectx, topstep, tradovate) use whole contracts (1, 2, 3...)
                # Forex brokers (mt4, mt5, tradelocker) use lot sizes (0.01, 0.1, 1.0...)
                if broker_str.lower() in ("projectx", "topstep", "tradovate"):
                    # For futures: ensure minimum 1 contract, round to integer
                    order_quantity = max(1, int(order_quantity))
                    logger.info(f"Account {account.id}: Normalized to {order_quantity} contracts (futures broker)")

                # === MAX POSITION SIZE ENFORCEMENT ===
                # Cap order quantity to account's max_position_size if set
                if account.max_position_size and order_quantity > account.max_position_size:
                    logger.warning(f"Account {account.id}: Capping order quantity from {order_quantity} to max_position_size {account.max_position_size}")
                    order_quantity = account.max_position_size

                # Re-normalize for futures after capping (ensure at least 1 contract)
                if broker_str.lower() in ("projectx", "topstep", "tradovate"):
                    order_quantity = max(1, int(order_quantity))

                # === MIN RISK/REWARD RATIO ENFORCEMENT ===
                min_rr = getattr(account, 'min_risk_reward_ratio', None)
                if min_rr and min_rr > 0 and account_sl_price and account_tp_price and entry_price:
                    try:
                        sl_dist = abs(float(entry_price) - float(account_sl_price))
                        tp_dist = abs(float(account_tp_price) - float(entry_price))
                        if sl_dist > 0:
                            rr_ratio = tp_dist / sl_dist
                            if rr_ratio < min_rr:
                                rr_rejection = (
                                    f"Risk/reward ratio too low: {rr_ratio:.2f} < {min_rr:.2f} "
                                    f"(SL dist={sl_dist:.5f}, TP dist={tp_dist:.5f})"
                                )
                                logger.warning(f"Account {account.id}: {rr_rejection}")
                                # Cleanup executor before skipping
                                if needs_cleanup and hasattr(executor, 'disconnect'):
                                    try:
                                        await executor.disconnect()
                                    except Exception:
                                        pass
                                models_broker = ModelsBrokerType(broker_str.lower())
                                execution_log = ExecutionLog(
                                    account_id=account.id,
                                    signal_id=signal_entity.id.value,
                                    broker=models_broker,
                                    symbol=symbol,
                                    action=action_str,
                                    volume=order_quantity,
                                    status="rejected",
                                    error_message=rr_rejection,
                                    execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000),
                                )
                                db.add(execution_log)
                                db.commit()
                                account_results.append(AccountExecutionResult(
                                    account_id=account.id,
                                    broker=broker_str,
                                    success=False,
                                    status="rejected",
                                    error=rr_rejection,
                                    target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                                    target_label=target_label,
                                ))
                                failed_count += 1
                                all_errors.append(rr_rejection)
                                continue
                            else:
                                logger.info(f"Account {account.id}: R:R check passed ({rr_ratio:.2f} >= {min_rr:.2f})")
                    except Exception as rr_err:
                        logger.warning(f"Account {account.id}: Could not evaluate R:R ratio: {rr_err}")

                order_request = OrderRequest(
                    account_id=account.id,
                    symbol=mapped_symbol,  # Use broker-specific symbol
                    order_type=effective_order_type,
                    quantity=order_quantity,
                    price=limit_price,  # For limit orders
                    stop_loss=account_sl_price,
                    take_profit=account_tp_price,
                    trailing_stop=account_trailing_stop,  # For trailing stop orders
                    comment=raw_payload.get("comment"),  # Trade comment for MT4/MT5
                )

                # Execute the order directly
                order_result = await executor.place_order(order_request)
            execution_success = order_result.success if hasattr(order_result, 'success') else order_result.get('success', False)
            execution_error = order_result.error if hasattr(order_result, 'error') else order_result.get('error')
            order_id = order_result.order_id if hasattr(order_result, 'order_id') else order_result.get('order_id')

            # Ensure entry price is captured for logging/journals
            if action_str != "close" and entry_price is None:
                try:
                    if isinstance(order_result, dict):
                        entry_price = order_result.get("price") or order_result.get("entry_price")
                    else:
                        entry_price = getattr(order_result, "price", None) or getattr(order_result, "entry_price", None)
                    if entry_price is None and hasattr(executor, 'get_quote'):
                        quote = await executor.get_quote(mapped_symbol)
                        if quote:
                            if action_str == "buy":
                                entry_price = quote.get('ask') or quote.get('price')
                            else:
                                entry_price = quote.get('bid') or quote.get('price')
                except Exception as entry_err:
                    logger.debug(f"Failed to fetch entry price for {mapped_symbol}: {entry_err}")

            # Decrement pending position counters after order completes (success or failure)
            # This releases the "reservations" made during position checks
            if action_str != "close":
                if account.max_open_positions:
                    _pending_total_tracker.decrement(account.id)
                if account.max_positions_per_symbol:
                    _pending_tracker.decrement(account.id, normalized_mapped_symbol)

            # Cleanup executor if needed
            if needs_cleanup and hasattr(executor, 'disconnect'):
                try:
                    await executor.disconnect()
                except:
                    pass

            # Build result similar to use_case response
            class UseCaseResult:
                def __init__(self, success, error=None, order_id=None):
                    self.status = type('Status', (), {'value': 'executed' if success else 'failed'})()
                    self.executions = 1 if success else 0
                    self.errors = [error] if error and not success else []
                    self.signal_id = order_id

            use_case_result = UseCaseResult(execution_success, execution_error, order_id)

            # Log execution result
            log_event(
                "account_execution_result",
                webhook_id=webhook_id,
                signal_id=signal_uuid,
                account_id=account.id,
                target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                broker=broker_str,
                success=execution_success,
                status=use_case_result.status.value,
                executions=use_case_result.executions,
                errors=use_case_result.errors
            )

            # Persist execution log for this account (use mapped_symbol to show what was actually sent)
            # order_quantity is the actual quantity sent to the broker (adjusted for futures)
            try:
                models_broker = ModelsBrokerType(broker_str.lower())

                # For close actions, extract P&L info from closed positions
                close_entry_price = None
                close_exit_price = None
                close_pnl = None
                close_position_id = None

                if action_str == "close" and hasattr(order_result, 'closed_positions') and order_result.closed_positions:
                    # Sum up P&L from all closed positions
                    total_pnl = 0
                    first_entry = None
                    first_exit = None
                    for cp in order_result.closed_positions:
                        if cp.get('pnl') is not None:
                            total_pnl += cp['pnl']
                        if first_entry is None and cp.get('entry_price'):
                            first_entry = cp['entry_price']
                        if first_exit is None and cp.get('exit_price'):
                            first_exit = cp['exit_price']
                        if close_position_id is None and cp.get('position_id'):
                            close_position_id = cp['position_id']

                    close_entry_price = first_entry
                    close_exit_price = first_exit
                    # Record P&L even if 0 (it's a valid outcome, just breakeven)
                    close_pnl = total_pnl

                    # Update the original ENTRY execution log with exit data
                    try:
                        from sqlalchemy import or_
                        import re

                        # Build symbol variants for matching futures contracts
                        base_symbol = mapped_symbol.upper().replace('.', '')
                        futures_match = re.match(r'^([A-Z]+)', base_symbol)
                        symbol_base = futures_match.group(1) if futures_match else base_symbol

                        symbol_patterns = [
                            f"%{symbol_base}%",
                            f"%{mapped_symbol}%",
                            f"%{symbol}%",
                        ]

                        entry_exec_to_update = db.query(ExecutionLog).filter(
                            ExecutionLog.account_id == account.id,
                            or_(*[ExecutionLog.symbol.ilike(p) for p in symbol_patterns]),
                            ExecutionLog.action.in_(['BUY', 'SELL', 'buy', 'sell']),
                            ExecutionLog.status == 'success',
                            ExecutionLog.exit_price.is_(None)  # Not yet closed
                        ).order_by(ExecutionLog.created_at.desc()).first()

                        if entry_exec_to_update:
                            entry_exec_to_update.exit_price = close_exit_price
                            entry_exec_to_update.pnl = close_pnl
                            entry_exec_to_update.closed_at = datetime.utcnow()
                            db.commit()
                            pnl_display = f"{close_pnl:.2f}" if close_pnl is not None else "Unknown"
                            logger.info(f"📊 Updated entry execution {entry_exec_to_update.id} ({entry_exec_to_update.symbol}) with exit: PnL={pnl_display}")
                    except Exception as update_err:
                        logger.debug(f"Could not update entry execution: {update_err}")

                exec_log = ExecutionLog(
                    signal_id=signal_uuid,
                    account_id=account.id,
                    broker=models_broker,
                    action=action_str.upper(),
                    symbol=mapped_symbol,  # Use the broker-specific mapped symbol
                    volume=order_quantity,
                    price=None,
                    status="success" if execution_success else "failed",
                    broker_response={"executions": use_case_result.executions, "original_symbol": symbol, "target_broker_account_id": _normalize_execution_target_broker_account_id(target_broker_account_id)} if execution_success else {"target_broker_account_id": _normalize_execution_target_broker_account_id(target_broker_account_id)},
                    error_message="; ".join(use_case_result.errors) if use_case_result.errors else None,
                    execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000),
                    # Enhanced risk management tracking (migration 027)
                    stop_loss=float(account_sl_price) if account_sl_price else None,
                    take_profit=float(account_tp_price) if account_tp_price else None,
                    trailing_stop=float(account_trailing_stop) if account_trailing_stop else None,
                    # Entry price: from signal for BUY/SELL, from closed position for CLOSE
                    entry_price=close_entry_price if action_str == "close" else (float(entry_price) if entry_price else None),
                    exit_price=close_exit_price if action_str == "close" else None,
                    pnl=close_pnl if action_str == "close" else None,
                    closed_at=datetime.utcnow() if action_str == "close" and execution_success else None,
                    position_id=close_position_id if action_str == "close" else None,
                    order_id=str(order_id) if order_id else None,
                    # SmartFlow ML tracking - links execution to signal for outcome learning
                    smartflow_signal_log_id=smartflow_signal_log_id,
                )
                db.add(exec_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to persist execution log for account {account.id}: {e}")
                db.rollback()

            if execution_success:
                successful_count += 1
            if compat_positions_enabled():
                if action_str == "close":
                    record_close(account.id, symbol=symbol)
                else:
                    record_open(account.id, {
                        "id": f"compat-{webhook_id}",
                        "symbol": symbol,
                        "side": "Long" if action_str == "buy" else "Short",
                        "volume": float(order_quantity or 0),
                        "unrealized_pnl": 0.0,
                    })

            # === SMARTFLOW ML OUTCOME TRACKING ===
            # Track outcomes for ALL executed SmartFlow signals (buy, sell, close)
            # ML learns from: entries (to track execution success) and exits (for P&L)
            if execution_success:
                try:
                    from app.services.smartflow_service import smartflow_service
                    from app.services.smartflow_ml_service import SmartFlowMLService

                    ml_service = SmartFlowMLService(db)

                    if action_str == "close":
                        # CLOSE action: Find the ENTRY signal to record P&L against
                        # We need the original buy/sell signal, not a close signal
                        # Record even if P&L is None/0 - the trade still closed

                        # First try: Find entry execution_log for this symbol/account
                        entry_signal_log_id = None
                        entry_exec = None
                        try:
                            from sqlalchemy import or_

                            # Build symbol variants for matching futures contracts
                            base_symbol = mapped_symbol.upper().replace('.', '')
                            # Extract base (e.g., MES from MESH6, MNQ from MNQM6)
                            import re
                            futures_match = re.match(r'^([A-Z]+)', base_symbol)
                            symbol_base = futures_match.group(1) if futures_match else base_symbol

                            # Build list of patterns to match
                            symbol_patterns = [
                                f"%{symbol_base}%",  # MES matches MESH6, MES
                                f"%{mapped_symbol}%",  # Exact mapped symbol
                                f"%{symbol}%",  # Original symbol from webhook
                            ]

                            # Query with any matching pattern
                            entry_exec = db.query(ExecutionLog).filter(
                                ExecutionLog.account_id == account.id,
                                or_(*[ExecutionLog.symbol.ilike(p) for p in symbol_patterns]),
                                ExecutionLog.action.in_(['BUY', 'SELL', 'buy', 'sell']),
                                ExecutionLog.status == 'success',
                                ExecutionLog.smartflow_signal_log_id.isnot(None),
                                ExecutionLog.exit_price.is_(None)  # Not yet closed
                            ).order_by(ExecutionLog.created_at.desc()).first()

                            if entry_exec:
                                entry_signal_log_id = entry_exec.smartflow_signal_log_id
                                logger.info(f"📈 Found entry signal {entry_signal_log_id} from execution {entry_exec.id} ({entry_exec.symbol})")
                        except Exception as lookup_err:
                            logger.debug(f"Entry execution lookup failed: {lookup_err}")

                        # Fallback: Find most recent ENTRY (buy/sell) signal for this ticker
                        if not entry_signal_log_id:
                            entry_signal_log_id = smartflow_service.get_recent_entry_signal_for_ticker(symbol)

                        if entry_signal_log_id:
                            outcome_result = await ml_service.record_signal_outcome(
                                signal_log_id=entry_signal_log_id,
                                trade_executed=True,
                                entry_price=close_entry_price,
                                exit_price=close_exit_price,
                                pnl=close_pnl
                            )
                            pnl_str = f"{close_pnl:.2f}" if close_pnl is not None else "Unknown"
                            logger.info(f"📈 SmartFlow CLOSE outcome: signal={entry_signal_log_id} PnL={pnl_str} Winner={outcome_result.get('is_winner')}")
                        else:
                            logger.warning(f"⚠️ No entry signal found for {symbol} to record P&L outcome")
                    else:
                        # BUY/SELL action: record execution (entry signal)
                        # This lets ML learn which signals actually got executed
                        signal_log_id = smartflow_service.get_recent_signal_for_ticker(symbol)
                        if signal_log_id:
                            outcome_result = await ml_service.record_signal_outcome(
                                signal_log_id=signal_log_id,
                                trade_executed=True,
                                entry_price=float(entry_price) if entry_price else None,
                                exit_price=None,
                                pnl=None  # No P&L yet - this is an entry
                            )
                            logger.info(f"📈 SmartFlow {action_str.upper()} executed: signal={signal_log_id} entry={entry_price}")
                except Exception as e:
                    logger.debug(f"SmartFlow outcome tracking skipped: {e}")

            # === TRADE JOURNAL ENTRY FOR ANALYTICS ===
            # Create journal entries for time analysis, strategy tracking, etc.
            if execution_success:
                try:
                    analytics_service = TradeAnalyticsService(db)
                    strategy_name = raw_payload.get("strategy") or raw_payload.get("strategy_name")

                    if action_str.lower() in ["buy", "sell"]:
                        # Create journal entry for new position
                        analytics_service.create_journal_entry(
                            user_id=user_id,
                            account_id=account.id,
                            symbol=mapped_symbol,
                            side=action_str,
                            quantity=float(order_quantity) if order_quantity else 1.0,
                            entry_price=float(entry_price) if entry_price else 0.0,
                            entry_time=datetime.utcnow(),
                            execution_log_id=exec_log.id if exec_log else None,
                            stop_loss=float(account_sl_price) if account_sl_price else None,
                            take_profit=float(account_tp_price) if account_tp_price else None,
                            strategy_name=strategy_name,
                            broker_trade_id=str(order_id) if order_id else None,
                            webhook_payload=raw_payload
                        )
                        logger.info(f"📊 Created trade journal entry for {action_str.upper()} {mapped_symbol}")

                    elif action_str.lower() == "close" and close_pnl is not None:
                        # Close existing journal entry or create a closed one
                        analytics_service.close_journal_entry(
                            account_id=account.id,
                            symbol=mapped_symbol,
                            exit_price=close_exit_price,
                            exit_time=datetime.utcnow(),
                            gross_pnl=close_pnl,
                            execution_log_id=exec_log.id if exec_log else None
                        )
                        logger.info(f"📊 Closed trade journal entry for {mapped_symbol} PnL=${close_pnl:.2f}")

                except Exception as journal_err:
                    logger.warning(f"Trade journal update failed: {journal_err}")

            # Increment daily trade counter (only for non-close actions)
            if execution_success and action_str != "close":
                try:
                    await counter_service.increment_trades(account.id, symbol)
                    logger.debug(f"Incremented trade counter for account {account.id}, symbol {symbol}")
                except Exception as e:
                    logger.warning(f"Failed to increment trade counter for account {account.id}: {e}")

            # Record result based on execution success
            if execution_success:
                account_results.append(AccountExecutionResult(
                    account_id=account.id,
                    broker=broker_str,
                    success=True,
                    status="executed",
                    execution_id=use_case_result.signal_id,
                    target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                    target_label=target_label,
                ))
            else:
                failed_count += 1
                error_msg = "; ".join(use_case_result.errors) if use_case_result.errors else "Unknown error"
                all_errors.append(f"Account {account.id}: {error_msg}")
                account_results.append(AccountExecutionResult(
                    account_id=account.id,
                    broker=broker_str,
                    success=False,
                    status="failed",
                    error=error_msg,
                    target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                    target_label=target_label,
                ))

        except Exception as e:
            logger.exception("Execution error for %s: %s", target_label, e)
            failed_count += 1
            error_msg = str(e)
            all_errors.append(f"Account {account.id}: {error_msg}")

            # Persist failed execution log (use mapped_symbol to show what was attempted)
            try:
                db.rollback()
                models_broker = ModelsBrokerType(broker_str.lower())
                exec_log = ExecutionLog(
                    signal_id=signal_uuid,
                    account_id=account.id,
                    broker=models_broker,
                    action=action_str.upper(),
                    symbol=mapped_symbol,  # Use the broker-specific mapped symbol
                    volume=order_quantity,
                    status="failed",
                    error_message=error_msg,
                    execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000),
                    # Enhanced risk management tracking (migration 027)
                    stop_loss=float(account_sl_price) if account_sl_price else None,
                    take_profit=float(account_tp_price) if account_tp_price else None,
                    trailing_stop=float(account_trailing_stop) if account_trailing_stop else None,
                    entry_price=float(entry_price) if entry_price else None,
                )
                db.add(exec_log)
                db.commit()
            except Exception as log_err:
                logger.error(f"Failed to persist error log: {log_err}")
                db.rollback()

            account_results.append(AccountExecutionResult(
                account_id=account.id,
                broker=broker_str,
                success=False,
                status="failed",
                error=error_msg,
                target_broker_account_id=_normalize_execution_target_broker_account_id(target_broker_account_id),
                target_label=target_label,
            ))

    # Determine overall status
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    if successful_count == total_execution_targets:
        overall_status = "executed"
        overall_success = True
    elif successful_count > 0:
        overall_status = "partial"
        overall_success = True  # At least one succeeded
    else:
        overall_status = "failed"
        overall_success = False

    # === UPDATE SIGNAL STATUS IN DATABASE ===
    try:
        signal_to_update = db.query(SignalORM).filter(
            SignalORM.signal_id == signal_uuid
        ).first()
        if signal_to_update:
            signal_to_update.status = overall_status
            signal_to_update.updated_at = datetime.utcnow()
            # Store execution results in signal_data
            signal_to_update.signal_data = {
                **(signal_to_update.signal_data or {}),
                "execution_results": {
                    "total_accounts": len(accounts),
                    "total_execution_targets": total_execution_targets,
                    "successful": successful_count,
                    "failed": failed_count,
                    "errors": all_errors,
                    "processing_time_ms": processing_time_ms,
                }
            }
            db.commit()
            logger.debug(f"Updated signal {signal_uuid} status to {overall_status}")
    except Exception as e:
        logger.error(f"Failed to update signal status: {e}")
        db.rollback()

    # Update webhook log
    try:
        webhook_log.processed = overall_success
        webhook_log.response_status = 200
        webhook_log.processing_time_ms = processing_time_ms
        webhook_log.response_body = json.dumps({
            "signal_id": signal_uuid,
            "status": overall_status,
            "total_accounts": len(accounts),
            "total_execution_targets": total_execution_targets,
            "successful": successful_count,
            "failed": failed_count,
            "errors": all_errors[:3] if all_errors else [],  # Limit errors stored
        })
        db.commit()
    except:
        pass

    # Update WebhookConfig stats
    try:
        webhook_config = db.query(WebhookConfig).filter(
            WebhookConfig.webhook_key == webhook_key
        ).first()
        if webhook_config:
            webhook_config.total_signals = (webhook_config.total_signals or 0) + 1
            webhook_config.last_signal_at = datetime.utcnow()
            if overall_success:
                webhook_config.successful_signals = (webhook_config.successful_signals or 0) + 1
            else:
                webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to update WebhookConfig stats: {e}")
        db.rollback()

    # Log overall result
    log_event(
        "multi_account_execution_complete",
        webhook_id=webhook_id,
        signal_id=signal_uuid,
        total_accounts=len(accounts),
        total_execution_targets=total_execution_targets,
        successful=successful_count,
        failed=failed_count,
        routing_strategy=routing_strategy
    )

    return ExecuteResponse(
        success=overall_success,
        signal_id=signal_uuid,
        status=overall_status,
        webhook_id=webhook_id,
        routing_strategy=routing_strategy,
        routing_reason=routing_reason,
        total_accounts=len(accounts),
        total_execution_targets=total_execution_targets,
        successful_accounts=successful_count,
        failed_accounts=failed_count,
        successful_targets=successful_count,
        failed_targets=failed_count,
        account_results=account_results,
        # Legacy single-account fields (first account)
        account_id=first_account.id,
        broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
        errors=all_errors,
        guard_decision="execute",
        processing_time_ms=processing_time_ms
    )
