"""
Risk Management API Router

Provides endpoints for:
- Querying rejected signals
- Getting daily risk statistics
- Managing risk limits
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.models.models import User
from app.models.database_models import (
    RejectedSignal,
    RejectedSignalReason,
    TradingAccount,
)
from app.routers.auth import get_current_user
from app.domain.services import (
    DailyCounterService,
    RiskEnforcementService,
    AccountRiskSettings,
    PositionSizingService,
    PositionSizingConfig,
    PositionSizingMode,
    SymbolSpecsService,
)
from app.infrastructure.repositories import (
    get_daily_counter_repository,
)
from app.infrastructure.adapters.position_counter_adapter import PositionCounterAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


# Global Risk Settings Schemas

class GlobalRiskSettings(BaseModel):
    """User's global risk settings that apply as defaults to all accounts"""
    default_max_daily_trades: Optional[int] = None
    default_max_open_positions: Optional[int] = None
    default_max_daily_loss: Optional[float] = None
    default_max_daily_loss_pct: Optional[float] = None
    default_max_daily_profit: Optional[float] = None
    default_max_daily_profit_pct: Optional[float] = None
    default_max_drawdown_pct: Optional[float] = None
    default_trade_cooldown_seconds: Optional[int] = None
    default_position_sizing_mode: Optional[str] = None
    default_fixed_lot_size: Optional[float] = None
    default_risk_percent_per_trade: Optional[float] = None
    risk_management_enabled: bool = True


# Global Risk Settings Endpoints

@router.get("/settings")
async def get_risk_settings(
    current_user: User = Depends(get_current_user)
) -> GlobalRiskSettings:
    """
    Get user's global risk settings.

    These settings serve as defaults for all trading accounts.
    Individual accounts can override these settings.
    """
    return GlobalRiskSettings(
        default_max_daily_trades=current_user.default_max_daily_trades,
        default_max_open_positions=current_user.default_max_open_positions,
        default_max_daily_loss=current_user.default_max_daily_loss,
        default_max_daily_loss_pct=current_user.default_max_daily_loss_pct,
        default_max_daily_profit=current_user.default_max_daily_profit,
        default_max_daily_profit_pct=current_user.default_max_daily_profit_pct,
        default_max_drawdown_pct=current_user.default_max_drawdown_pct,
        default_trade_cooldown_seconds=current_user.default_trade_cooldown_seconds,
        default_position_sizing_mode=current_user.default_position_sizing_mode,
        default_fixed_lot_size=current_user.default_fixed_lot_size,
        default_risk_percent_per_trade=current_user.default_risk_percent_per_trade,
        risk_management_enabled=current_user.risk_management_enabled if current_user.risk_management_enabled is not None else True
    )


@router.put("/settings")
async def update_risk_settings(
    settings: GlobalRiskSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's global risk settings.

    All fields are optional. Only provided fields will be updated.
    These settings apply as defaults to all trading accounts.
    """
    user = db.query(User).filter(User.id == current_user.id).first()

    # Update non-None values
    for field, value in settings.dict().items():
        if hasattr(user, field):
            setattr(user, field, value)

    db.commit()
    return {"message": "Risk settings updated successfully"}


@router.get("/dashboard-summary")
async def get_risk_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get risk usage summary for dashboard.

    Returns usage vs limits for all active accounts:
    - Daily trades executed vs limit
    - Open positions vs limit
    - Current drawdown vs limit
    - Halted accounts
    """
    from app.domain.services import DrawdownService
    from app.infrastructure.repositories import DailyPnLRepository, EquityHistoryRepository

    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    summary = {
        "total_accounts": len(accounts),
        "accounts_at_limit": 0,
        "accounts_halted": 0,
        "accounts": []
    }

    counter_repo = get_daily_counter_repository()
    counter_service = DailyCounterService(counter_repo)

    # Initialize drawdown service
    pnl_repo = DailyPnLRepository(db)
    equity_repo = EquityHistoryRepository(db)
    drawdown_service = DrawdownService(equity_repo)

    for account in accounts:
        counters = await counter_service.get_counters(account.id)
        drawdown = await drawdown_service.get_current_state(account.id)

        # Calculate usage percentages
        trades_usage = 0
        if account.max_daily_trades:
            trades_usage = (counters.trades_executed / account.max_daily_trades) * 100

        positions_usage = 0
        if account.max_open_positions:
            # TODO: Calculate from positions table
            positions_usage = 0

        drawdown_usage = 0
        if account.max_drawdown_pct and drawdown:
            drawdown_usage = (drawdown.drawdown_pct / account.max_drawdown_pct) * 100

        # Check if daily loss limit hit (from daily_pnl table)
        is_halted = False
        if drawdown and getattr(drawdown, "daily_loss_halted", False):
            is_halted = True

        account_summary = {
            "account_id": account.id,
            "account_name": account.account_name or account.account_number,
            "broker": account.broker.value,
            "daily_trades": {
                "current": counters.trades_executed,
                "limit": account.max_daily_trades,
                "usage_pct": min(100, trades_usage)
            },
            "open_positions": {
                "current": 0,  # TODO: Query positions table
                "limit": account.max_open_positions,
                "usage_pct": min(100, positions_usage)
            },
            "drawdown": {
                "current": drawdown.drawdown_pct if drawdown else 0,
                "limit": account.max_drawdown_pct,
                "usage_pct": min(100, drawdown_usage)
            },
            "is_at_limit": trades_usage >= 100 or positions_usage >= 100 or drawdown_usage >= 100,
            "is_halted": is_halted
        }

        summary["accounts"].append(account_summary)

        if account_summary["is_at_limit"]:
            summary["accounts_at_limit"] += 1
        if account_summary["is_halted"]:
            summary["accounts_halted"] += 1

    return summary


@router.get("/rejected-signals")
async def get_rejected_signals(
    limit: int = Query(50, le=100, ge=1, description="Number of signals to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    account_id: Optional[int] = Query(None, description="Filter by account ID"),
    reason: Optional[str] = Query(None, description="Filter by rejection reason"),
    start_date: Optional[date] = Query(None, description="Filter signals from this date"),
    end_date: Optional[date] = Query(None, description="Filter signals until this date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get rejected signals for the current user.

    Returns a paginated list of signals that were blocked by risk management,
    along with the reason for rejection.

    **Query Parameters:**
    - `limit`: Maximum number of signals to return (1-100, default 50)
    - `offset`: Pagination offset (default 0)
    - `account_id`: Filter by specific account
    - `reason`: Filter by rejection reason (daily_limit, concurrent_limit, symbol_limit, cooldown, etc.)
    - `start_date`: Include signals from this date onwards
    - `end_date`: Include signals until this date
    """
    query = db.query(RejectedSignal).filter(
        RejectedSignal.user_id == current_user.id
    )

    # Apply filters
    if account_id:
        # Verify user owns this account
        account = db.query(TradingAccount).filter(
            TradingAccount.id == account_id,
            TradingAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        query = query.filter(RejectedSignal.account_id == account_id)

    if reason:
        try:
            reason_enum = RejectedSignalReason(reason)
            query = query.filter(RejectedSignal.reason == reason_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid reason. Valid reasons: {[r.value for r in RejectedSignalReason]}"
            )

    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(RejectedSignal.created_at >= start_datetime)

    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(RejectedSignal.created_at <= end_datetime)

    # Get total count before pagination
    total = query.count()

    # Apply pagination and ordering
    signals = query.order_by(RejectedSignal.created_at.desc())\
        .offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "signals": [
            {
                "id": s.id,
                "account_id": s.account_id,
                "symbol": s.symbol,
                "action": s.action,
                "quantity": s.quantity,
                "source": s.source,
                "reason": s.reason.value if isinstance(s.reason, RejectedSignalReason) else s.reason,
                "reason_detail": s.reason_detail,
                "limit_value": s.limit_value,
                "current_value": s.current_value,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signals
        ]
    }


@router.get("/rejected-signals/summary")
async def get_rejected_signals_summary(
    days: int = Query(7, le=30, ge=1, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get summary of rejected signals by reason over the past N days.

    Returns counts grouped by rejection reason for analysis.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get counts by reason
    results = db.query(
        RejectedSignal.reason,
        func.count(RejectedSignal.id).label("count")
    ).filter(
        RejectedSignal.user_id == current_user.id,
        RejectedSignal.created_at >= start_date
    ).group_by(RejectedSignal.reason).all()

    # Build summary dict
    summary = {
        "period_days": days,
        "start_date": start_date.date().isoformat(),
        "end_date": date.today().isoformat(),
        "total_rejected": sum(r.count for r in results),
        "by_reason": {
            r.reason.value if isinstance(r.reason, RejectedSignalReason) else r.reason: r.count
            for r in results
        }
    }

    return summary


@router.get("/daily-stats/{account_id}")
async def get_daily_stats(
    account_id: int,
    target_date: Optional[date] = Query(None, description="Date to get stats for (default: today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get daily risk statistics for an account.

    Returns:
    - Signals received today
    - Trades executed today
    - Trades by symbol
    - Time since last trade
    - Current limits vs usage

    **Path Parameters:**
    - `account_id`: Trading account ID

    **Query Parameters:**
    - `target_date`: Date to get stats for (defaults to today)
    """
    # Verify user owns this account
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Get daily counters
    counter_repo = get_daily_counter_repository()
    counter_service = DailyCounterService(counter_repo)

    stats_date = target_date or date.today()
    counters = await counter_service.get_counters(account_id, stats_date)

    # Calculate cooldown status
    cooldown_remaining = None
    if account.trade_cooldown_seconds and counters.last_trade_at:
        elapsed = (datetime.utcnow() - counters.last_trade_at).total_seconds()
        remaining = account.trade_cooldown_seconds - elapsed
        if remaining > 0:
            cooldown_remaining = int(remaining)

    return {
        "account_id": account_id,
        "account_name": account.account_name,
        "date": stats_date.isoformat(),
        "counters": {
            "signals_received": counters.signals_received,
            "trades_executed": counters.trades_executed,
            "trades_by_symbol": counters.trades_by_symbol,
            "last_trade_at": counters.last_trade_at.isoformat() if counters.last_trade_at else None,
        },
        "limits": {
            "max_daily_trades": account.max_daily_trades,
            "max_open_positions": account.max_open_positions,
            "max_positions_per_symbol": account.max_positions_per_symbol,
            "trade_cooldown_seconds": account.trade_cooldown_seconds,
        },
        "status": {
            "daily_trades_remaining": (
                (account.max_daily_trades - counters.trades_executed)
                if account.max_daily_trades else None
            ),
            "cooldown_remaining_seconds": cooldown_remaining,
            "at_daily_limit": (
                counters.trades_executed >= account.max_daily_trades
                if account.max_daily_trades else False
            ),
            "in_cooldown": cooldown_remaining is not None and cooldown_remaining > 0,
        }
    }


@router.get("/daily-stats")
async def get_all_daily_stats(
    target_date: Optional[date] = Query(None, description="Date to get stats for (default: today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get daily risk statistics for all user accounts.

    Returns aggregated stats across all accounts.
    """
    # Get all user's trading accounts
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    if not accounts:
        return {
            "date": (target_date or date.today()).isoformat(),
            "accounts": [],
            "totals": {
                "total_signals": 0,
                "total_trades": 0,
                "accounts_at_limit": 0,
                "accounts_in_cooldown": 0,
            }
        }

    counter_repo = get_daily_counter_repository()
    counter_service = DailyCounterService(counter_repo)
    stats_date = target_date or date.today()

    account_stats = []
    totals = {
        "total_signals": 0,
        "total_trades": 0,
        "accounts_at_limit": 0,
        "accounts_in_cooldown": 0,
    }

    for account in accounts:
        counters = await counter_service.get_counters(account.id, stats_date)

        # Calculate status
        at_limit = (
            counters.trades_executed >= account.max_daily_trades
            if account.max_daily_trades else False
        )

        in_cooldown = False
        if account.trade_cooldown_seconds and counters.last_trade_at:
            elapsed = (datetime.utcnow() - counters.last_trade_at).total_seconds()
            in_cooldown = elapsed < account.trade_cooldown_seconds

        account_stats.append({
            "account_id": account.id,
            "account_name": account.account_name,
            "broker": account.broker.value if account.broker else None,
            "signals_received": counters.signals_received,
            "trades_executed": counters.trades_executed,
            "at_daily_limit": at_limit,
            "in_cooldown": in_cooldown,
        })

        totals["total_signals"] += counters.signals_received
        totals["total_trades"] += counters.trades_executed
        if at_limit:
            totals["accounts_at_limit"] += 1
        if in_cooldown:
            totals["accounts_in_cooldown"] += 1

    return {
        "date": stats_date.isoformat(),
        "accounts": account_stats,
        "totals": totals,
    }


@router.post("/evaluate")
async def evaluate_risk(
    account_id: int,
    symbol: str,
    action: str = "buy",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Evaluate if a hypothetical signal would be blocked by risk limits.

    Useful for testing risk configuration without actually sending a signal.

    **Request Body:**
    - `account_id`: Target account ID
    - `symbol`: Trading symbol (e.g., "US30", "EURUSD")
    - `action`: Signal action (buy, sell, close)

    **Returns:**
    - `passed`: Whether the signal would be allowed
    - `violations`: List of risk violations if blocked
    """
    # Verify user owns this account
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Build risk settings from account
    settings = AccountRiskSettings.from_account(account)

    # Get services
    counter_repo = get_daily_counter_repository()
    counter_service = DailyCounterService(counter_repo)
    position_counter = PositionCounterAdapter(session=db)

    # Create risk enforcement service
    risk_service = RiskEnforcementService(
        counter_service=counter_service,
        position_counter=position_counter,
    )

    # Evaluate
    evaluation = await risk_service.evaluate(
        account_id=account_id,
        symbol=symbol,
        action=action,
        settings=settings,
    )

    return {
        "account_id": account_id,
        "symbol": symbol,
        "action": action,
        "passed": evaluation.passed,
        "result": evaluation.result.value,
        "violations": [
            {
                "reason": v.reason,
                "detail": v.detail,
                "limit_value": v.limit_value,
                "current_value": v.current_value,
            }
            for v in evaluation.violations
        ]
    }


@router.get("/reasons")
async def get_rejection_reasons():
    """
    Get list of all possible rejection reasons.

    Useful for UI dropdowns and filtering.
    """
    return {
        "reasons": [
            {
                "value": reason.value,
                "label": reason.value.replace("_", " ").title(),
                "description": _get_reason_description(reason),
            }
            for reason in RejectedSignalReason
        ]
    }


def _get_reason_description(reason: RejectedSignalReason) -> str:
    """Get human-readable description for rejection reason."""
    descriptions = {
        RejectedSignalReason.DAILY_LIMIT: "Maximum number of daily trades reached",
        RejectedSignalReason.CONCURRENT_LIMIT: "Maximum number of concurrent open positions reached",
        RejectedSignalReason.SYMBOL_LIMIT: "Maximum positions for this symbol reached",
        RejectedSignalReason.COOLDOWN: "Trade cooldown period is still active",
        RejectedSignalReason.DAILY_LOSS: "Maximum daily loss limit reached",
        RejectedSignalReason.DRAWDOWN: "Maximum drawdown limit reached",
        RejectedSignalReason.RISK_REWARD: "Signal did not meet risk/reward criteria",
        RejectedSignalReason.DISABLED: "Risk management or trading is disabled for this account",
    }
    return descriptions.get(reason, "Unknown rejection reason")


# Position Sizing Endpoints

class PositionSizeRequest(BaseModel):
    """Request to calculate position size"""
    account_id: int
    symbol: str
    stop_loss_pips: Optional[float] = None
    balance: Optional[float] = None  # Override for preview


@router.post("/calculate-position-size")
async def calculate_position_size(
    request: PositionSizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview position size calculation for an account.

    Useful for UI to show users what size would be used for a trade.

    **Request Body:**
    - `account_id`: Trading account ID
    - `symbol`: Trading symbol (e.g., "US30", "EURUSD", "ES")
    - `stop_loss_pips`: Optional stop loss distance in pips (required for risk-based mode)
    - `balance`: Optional balance override for "what if" scenarios

    **Returns:**
    - `calculated_size`: Raw calculated size before broker adjustments
    - `adjusted_size`: Final size adjusted to broker min/max/step
    - `mode_used`: Sizing mode used
    - `calculation_detail`: Human-readable explanation of calculation
    - `symbol_specs`: Broker specifications used
    """
    # Verify account ownership
    account = db.query(TradingAccount).filter(
        TradingAccount.id == request.account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(404, "Account not found")

    sizing_service = PositionSizingService()
    specs_service = SymbolSpecsService()

    # Build config
    config = PositionSizingConfig(
        mode=PositionSizingMode(account.position_sizing_mode or "fixed"),
        fixed_lot_size=account.fixed_lot_size or 0.01,
        percent_of_balance=account.percent_of_balance or 1.0,
        percent_of_equity=account.percent_of_equity or 1.0,
        risk_percent_per_trade=account.risk_percent_per_trade or 1.0,
        max_position_size=account.max_position_size
    )

    # Get specs
    specs = await specs_service.get_specs(request.symbol)

    # Calculate
    result = sizing_service.calculate_position_size(
        config=config,
        balance=request.balance or account.balance or 10000,
        equity=account.equity or account.balance or 10000,
        symbol_specs=specs,
        stop_loss_pips=request.stop_loss_pips
    )

    return {
        "calculated_size": result.calculated_size,
        "adjusted_size": result.adjusted_size,
        "mode_used": result.mode_used,
        "calculation_detail": result.calculation_detail,
        "symbol_specs": {
            "min_lot": specs.min_lot,
            "max_lot": specs.max_lot,
            "lot_step": specs.lot_step,
            "pip_value": specs.pip_value,
            "contract_size": specs.contract_size,
            "digits": specs.digits,
        }
    }
