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
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

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
from app.services.signal_intelligence_guard import SignalIntelligenceGuard, GuardDecision
from app.domain.entities.signal import Signal
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId
from app.domain.services.account_routing_service import AccountRoutingService
from app.domain.services.risk_unit_converter import RiskUnitConverter, RiskUnitMode
from app.domain.services.daily_counter_service import DailyCounterService
from app.infrastructure.repositories import get_daily_counter_repository
from app.services.compat_positions_cache import record_open, record_close, is_enabled as compat_positions_enabled
from app.models.database_models import DailyPnL, AccountEquityHistory
from datetime import date as date_type

logger = logging.getLogger(__name__)


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
    """Result for a single account execution"""
    account_id: int
    broker: str
    success: bool
    status: str
    error: Optional[str] = None
    execution_id: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Standard execution response with multi-account support"""
    success: bool
    signal_id: str
    status: str  # executed, partial, rejected, paused, failed
    webhook_id: str
    routing_strategy: str = "default_only"
    routing_reason: Optional[str] = None
    total_accounts: int = 0
    successful_accounts: int = 0
    failed_accounts: int = 0
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
                Position.status == "open"
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
    first_account = accounts[0]
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

    for account in accounts:
        account_start = datetime.utcnow()
        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)

        # === RISK MANAGEMENT ENFORCEMENT (only for non-close actions) ===
        if action_str != "close":
            rejection_reason = None

            try:
                # Get daily counters for this account
                counters = await counter_service.get_counters(account.id)

                # 1. MAX DAILY TRADES CHECK
                if account.max_daily_trades and counters.trades_executed >= account.max_daily_trades:
                    rejection_reason = f"Max daily trades exceeded ({counters.trades_executed}/{account.max_daily_trades})"

                # 2. TRADE COOLDOWN CHECK
                if not rejection_reason and account.trade_cooldown_seconds and counters.last_trade_at:
                    elapsed = (datetime.utcnow() - counters.last_trade_at).total_seconds()
                    if elapsed < account.trade_cooldown_seconds:
                        remaining = int(account.trade_cooldown_seconds - elapsed)
                        rejection_reason = f"Trade cooldown active ({remaining}s remaining of {account.trade_cooldown_seconds}s)"

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
                    executions=0,
                    errors=[rejection_reason]
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

        # Initialize SL/TP/trailing_stop variables (before try block for exception handler access)
        account_sl_price = sl_price
        account_tp_price = tp_price
        account_trailing_stop = trailing_stop
        entry_price = None
        order_quantity = quantity  # Will be adjusted for futures brokers in the else block

        try:
            # Create account-specific executor with credentials
            executor, needs_cleanup = await _create_account_executor(account, db)

            if not executor:
                raise Exception(f"Could not create executor for {broker_str}")

            # Ensure executor is initialized
            if not getattr(executor, 'is_connected', False):
                try:
                    await executor.initialize()
                except Exception as init_err:
                    logger.warning(f"Executor init warning for account {account.id}: {init_err}")

            # === POSITION-BASED RISK CHECKS (only for non-close actions) ===
            if action_str != "close":
                position_rejection = None
                try:
                    # Get current open positions from broker
                    current_positions = await executor.get_positions()
                    total_positions = len(current_positions) if current_positions else 0

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
                    if account.max_open_positions:
                        # Add pending orders that haven't been confirmed yet
                        pending_total_count = _pending_total_tracker.get_pending_count(account.id)
                        total_with_pending = total_positions + pending_total_count

                        if total_with_pending >= account.max_open_positions:
                            position_rejection = f"Max open positions exceeded ({total_with_pending}/{account.max_open_positions}, broker={total_positions}, pending={pending_total_count})"
                        else:
                            # Reserve a slot by incrementing pending counter BEFORE placing order
                            _pending_total_tracker.increment(account.id)
                            logger.info(f"Account {account.id}: Total position check passed ({total_positions} broker + {pending_total_count + 1} pending / {account.max_open_positions} max)")

                    # 4. MAX POSITIONS PER SYMBOL CHECK (with race condition prevention)
                    if not position_rejection and account.max_positions_per_symbol:
                        # Count existing positions matching this symbol using normalized comparison
                        symbol_positions = []
                        for p in (current_positions or []):
                            pos_symbol = get_pos_attr(p, 'symbol', '') or ''
                            normalized_pos_symbol = normalize_symbol_for_match(pos_symbol)
                            # Match if normalized symbols are equal (not substring!)
                            if normalized_pos_symbol == normalized_signal_symbol or normalized_pos_symbol == normalized_mapped_symbol:
                                symbol_positions.append(p)
                        broker_position_count = len(symbol_positions)

                        # Add pending orders that haven't been confirmed yet (race condition prevention)
                        pending_count = _pending_tracker.get_pending_count(account.id, mapped_symbol)
                        total_symbol_positions = broker_position_count + pending_count

                        if total_symbol_positions >= account.max_positions_per_symbol:
                            position_rejection = f"Max positions for {symbol} exceeded ({total_symbol_positions}/{account.max_positions_per_symbol}, broker={broker_position_count}, pending={pending_count})"
                        else:
                            # Reserve a slot by incrementing pending counter BEFORE placing order
                            _pending_tracker.increment(account.id, mapped_symbol)
                            logger.info(f"Account {account.id}: Symbol position check passed for {mapped_symbol} ({broker_position_count} broker + {pending_count + 1} pending / {account.max_positions_per_symbol} max)")

                except Exception as pos_err:
                    logger.warning(f"Failed to check positions for account {account.id}: {pos_err}")

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
                        executions=0,
                        errors=[position_rejection]
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
                        # No positions to close - mark as skipped, not success
                        order_result = type('Result', (), {
                            'success': False,
                            'order_id': 'no_positions',
                            'error': 'No matching positions to close'
                        })()
                    else:
                        # Close each matching position
                        closed = 0
                        close_errors = []
                        for pos in matching_positions:
                            pos_id = get_attr(pos, 'id') or get_attr(pos, 'position_id') or get_attr(pos, 'contract_id')
                            if pos_id:
                                # Use explicit_close_quantity if provided (partial close), otherwise None (full close)
                                close_qty = float(explicit_close_quantity) if explicit_close_quantity else None
                                close_result = await executor.close_position(str(pos_id), close_qty)
                                if close_result.success if hasattr(close_result, 'success') else close_result.get('success'):
                                    closed += 1
                                else:
                                    err = close_result.error if hasattr(close_result, 'error') else close_result.get('error')
                                    if err:
                                        close_errors.append(str(err))

                        order_result = type('Result', (), {
                            'success': closed > 0,
                            'order_id': f'closed_{closed}',
                            'error': '; '.join(close_errors) if close_errors and closed == 0 else None
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

            # Decrement pending position counters after order completes (success or failure)
            # This releases the "reservations" made during position checks
            if action_str != "close":
                if account.max_open_positions:
                    _pending_total_tracker.decrement(account.id)
                if account.max_positions_per_symbol:
                    _pending_tracker.decrement(account.id, mapped_symbol)

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
                exec_log = ExecutionLog(
                    signal_id=signal_uuid,
                    account_id=account.id,
                    broker=models_broker,
                    action=action_str.upper(),
                    symbol=mapped_symbol,  # Use the broker-specific mapped symbol
                    volume=order_quantity,
                    price=None,
                    status="success" if execution_success else "failed",
                    broker_response={"executions": use_case_result.executions, "original_symbol": symbol} if execution_success else None,
                    error_message="; ".join(use_case_result.errors) if use_case_result.errors else None,
                    execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000),
                    # Enhanced risk management tracking (migration 027)
                    stop_loss=float(account_sl_price) if account_sl_price else None,
                    take_profit=float(account_tp_price) if account_tp_price else None,
                    trailing_stop=float(account_trailing_stop) if account_trailing_stop else None,
                    entry_price=float(entry_price) if entry_price else None,
                    order_id=str(order_id) if order_id else None,
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
                    execution_id=use_case_result.signal_id
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
                    error=error_msg
                ))

        except Exception as e:
            logger.exception(f"Execution error for account {account.id}: {e}")
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
                error=error_msg
            ))

    # Determine overall status
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    if successful_count == len(accounts):
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
        successful_accounts=successful_count,
        failed_accounts=failed_count,
        account_results=account_results,
        # Legacy single-account fields (first account)
        account_id=first_account.id,
        broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
        errors=all_errors,
        guard_decision="execute",
        processing_time_ms=processing_time_ms
    )
