"""
Signal Intelligence API Router

Provides endpoints for Signal Intelligence Layer features:
- Get/update momentum settings
- Get signal counters
- Reset counters
- Handle guard modal actions
- Get discard bin entries
- Flush discard bin
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.db.database import get_db
from app.models.models import User
from app.models.database_models import (
    MomentumSettings,
    SignalCounter,
    DiscardBin,
)
from app.routers.auth import get_current_user
from app.services.signal_intelligence_guard import SignalIntelligenceGuard
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signal-intelligence", tags=["signal-intelligence"])


# Request/Response Models

class MomentumSettingsUpdate(BaseModel):
    """Update momentum settings"""
    warn_at: Optional[int] = None
    auto_breakeven: Optional[bool] = None
    pause_on_chop: Optional[bool] = None
    max_exposure: Optional[float] = None
    auto_pause_on_exposure: Optional[bool] = None
    allow_hedge: Optional[bool] = None
    staleness_enabled: Optional[bool] = None
    staleness_seconds: Optional[int] = None
    force_old_signals: Optional[bool] = None
    discard_flush_interval: Optional[str] = None  # "1h", "24h", "30d"
    # Trading Session settings
    trading_session_enabled: Optional[bool] = None
    trading_session_start: Optional[str] = None  # HH:MM format
    trading_session_end: Optional[str] = None  # HH:MM format
    trading_session_timezone: Optional[str] = None  # IANA timezone
    trading_session_days: Optional[List[int]] = None  # Days of week: 1=Mon, 7=Sun


class MomentumSettingsResponse(BaseModel):
    """Momentum settings response"""
    user_id: int
    warn_at: int
    auto_breakeven: bool
    pause_on_chop: bool
    max_exposure: float
    auto_pause_on_exposure: bool
    allow_hedge: bool
    staleness_enabled: bool
    staleness_seconds: int
    force_old_signals: bool
    discard_flush_interval: str
    # Trading Session settings
    trading_session_enabled: bool = False
    trading_session_start: Optional[str] = "09:30"
    trading_session_end: Optional[str] = "16:00"
    trading_session_timezone: Optional[str] = "America/New_York"
    trading_session_days: Optional[List[int]] = [1, 2, 3, 4, 5]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SignalCounterResponse(BaseModel):
    """Signal counter response"""
    user_id: int
    session_key: str
    current_bias: str
    opposite_momentum: int
    last_signal_ts: Optional[datetime]
    last8_pattern: Optional[str]
    chop_mode: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class ResetCounterRequest(BaseModel):
    """Request to reset a counter"""
    session_key: str  # user_id:symbol:strategy_id


class ModalActionRequest(BaseModel):
    """Handle guard modal action"""
    signal_id: str
    action: str  # "breakeven", "close", "ignore", "hedge", "execute", "discard"
    session_key: Optional[str] = None


class DiscardBinEntry(BaseModel):
    """Discard bin entry response"""
    id: int
    user_id: int
    received_at: datetime
    reason: str
    age_ms: Optional[int]
    symbol: Optional[str]
    side: Optional[str]
    broker_target: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Endpoints

@router.get("/settings", response_model=MomentumSettingsResponse)
async def get_momentum_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's momentum settings"""
    guard = SignalIntelligenceGuard(db)
    settings = guard._get_momentum_settings(current_user.id)
    return settings


@router.put("/settings", response_model=MomentumSettingsResponse)
async def update_momentum_settings(
    settings_update: MomentumSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's momentum settings"""
    guard = SignalIntelligenceGuard(db)
    settings = guard._get_momentum_settings(current_user.id)

    # Update provided fields
    for field, value in settings_update.dict(exclude_unset=True).items():
        if hasattr(settings, field) and value is not None:
            setattr(settings, field, value)

    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)

    return settings


@router.get("/counters", response_model=List[SignalCounterResponse])
async def get_signal_counters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all signal counters for user"""
    counters = db.query(SignalCounter).filter(
        SignalCounter.user_id == current_user.id
    ).all()
    return counters


@router.get("/counters/{session_key}", response_model=SignalCounterResponse)
async def get_signal_counter(
    session_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific signal counter"""
    counter = db.query(SignalCounter).filter(
        SignalCounter.user_id == current_user.id,
        SignalCounter.session_key == session_key
    ).first()

    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )

    return counter


@router.post("/counters/reset")
async def reset_counter(
    request: ResetCounterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset a signal counter (called on manual close, TP hit, or ignore)"""
    guard = SignalIntelligenceGuard(db)
    guard.reset_counter(current_user.id, request.session_key)

    return {"message": "Counter reset successfully", "session_key": request.session_key}


@router.post("/modal-action")
async def handle_modal_action(
    request: ModalActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle guard modal action.

    Actions:
    - "breakeven": Move SL to entry (if auto_breakeven enabled)
    - "close": Close position
    - "ignore": Reset counter and continue
    - "hedge": Create reverse order at 0.5x size (if allow_hedge enabled)
    """
    guard = SignalIntelligenceGuard(db)

    if request.action == "ignore":
        # Reset counter
        if request.session_key:
            guard.reset_counter(current_user.id, request.session_key)
        return {"message": "Counter reset, signal will be processed", "action": "ignore"}

    elif request.action == "breakeven":
        # Move SL to entry price for open positions matching the session
        try:
            from app.models.models import Position
            from app.models.database_models import TradingAccount
            
            # Extract symbol from session_key (format: user_id:symbol:strategy_id)
            if request.session_key:
                parts = request.session_key.split(":")
                if len(parts) >= 2:
                    symbol = parts[1]
                    
                    # Get user's open positions for this symbol
                    accounts = db.query(TradingAccount).filter(
                        TradingAccount.user_id == current_user.id,
                        TradingAccount.is_active == True
                    ).all()
                    
                    account_ids = [a.id for a in accounts]
                    positions = db.query(Position).filter(
                        Position.account_id.in_(account_ids),
                        Position.symbol == symbol,
                        Position.status == "open"
                    ).all()
                    
                    modified_count = 0
                    for position in positions:
                        try:
                            # Get broker adapter
                            account = next((a for a in accounts if a.id == position.account_id), None)
                            if not account:
                                continue
                                
                            from app.dependencies import get_container
                            from fastapi import Request
                            # Create a minimal request-like object for container access
                            # In production, you'd pass the actual request
                            # For now, we'll use the container directly
                            from app.infrastructure.container import Container
                            container = Container()
                            await container.initialize()
                            
                            brokers = container.brokers()
                            broker_type = account.broker.value
                            broker_adapter = brokers.get(broker_type)
                            
                            if broker_adapter and hasattr(broker_adapter, 'modify_order'):
                                # Move SL to entry price
                                entry_price = position.entry_price or position.price
                                if entry_price:
                                    result = await broker_adapter.modify_order(
                                        order_id=str(position.order_id or position.id),
                                        modifications={"stop_loss": entry_price}
                                    )
                                    if result and getattr(result, 'success', False):
                                        modified_count += 1
                        except Exception as e:
                            logger.error(f"Failed to modify position {position.id} for breakeven: {e}")
                            continue
                    
                    # Reset counter after breakeven
                    if request.session_key:
                        guard.reset_counter(current_user.id, request.session_key)
                    
                    return {
                        "message": f"Breakeven applied to {modified_count} position(s)",
                        "action": "breakeven",
                        "modified_count": modified_count
                    }
        except Exception as e:
            logger.error(f"Breakeven action failed: {e}")
            return {"message": f"Breakeven action failed: {str(e)}", "action": "breakeven", "error": str(e)}

    elif request.action == "close":
        # Close positions matching the session
        try:
            from app.models.models import Position
            from app.models.database_models import TradingAccount
            
            if request.session_key:
                parts = request.session_key.split(":")
                if len(parts) >= 2:
                    symbol = parts[1]
                    
                    # Get user's open positions for this symbol
                    accounts = db.query(TradingAccount).filter(
                        TradingAccount.user_id == current_user.id,
                        TradingAccount.is_active == True
                    ).all()
                    
                    account_ids = [a.id for a in accounts]
                    positions = db.query(Position).filter(
                        Position.account_id.in_(account_ids),
                        Position.symbol == symbol,
                        Position.status == "open"
                    ).all()
                    
                    closed_count = 0
                    for position in positions:
                        try:
                            account = next((a for a in accounts if a.id == position.account_id), None)
                            if not account:
                                continue
                                
                            from app.infrastructure.container import Container
                            container = Container()
                            await container.initialize()
                            
                            brokers = container.brokers()
                            broker_type = account.broker.value
                            broker_adapter = brokers.get(broker_type)
                            
                            if broker_adapter and hasattr(broker_adapter, 'close_position'):
                                result = await broker_adapter.close_position(
                                    position_id=str(position.position_id or position.id),
                                    quantity=None  # Close full position
                                )
                                if result and getattr(result, 'success', False):
                                    closed_count += 1
                        except Exception as e:
                            logger.error(f"Failed to close position {position.id}: {e}")
                            continue
                    
                    # Reset counter after close
                    if request.session_key:
                        guard.reset_counter(current_user.id, request.session_key)
                    
                    return {
                        "message": f"Closed {closed_count} position(s)",
                        "action": "close",
                        "closed_count": closed_count
                    }
        except Exception as e:
            logger.error(f"Close action failed: {e}")
            return {"message": f"Close action failed: {str(e)}", "action": "close", "error": str(e)}

    elif request.action == "hedge":
        # Create reverse order at 0.5x size
        try:
            from app.models.models import Position
            from app.models.database_models import TradingAccount
            from app.domain.enums import SignalAction

            if request.session_key:
                parts = request.session_key.split(":")
                if len(parts) >= 2:
                    symbol = parts[1]

                    # Get user's open positions for this symbol
                    accounts = db.query(TradingAccount).filter(
                        TradingAccount.user_id == current_user.id,
                        TradingAccount.is_active == True
                    ).all()

                    account_ids = [a.id for a in accounts]
                    positions = db.query(Position).filter(
                        Position.account_id.in_(account_ids),
                        Position.symbol == symbol,
                        Position.status == "open"
                    ).all()

                    hedged_count = 0
                    for position in positions:
                        try:
                            account = next((a for a in accounts if a.id == position.account_id), None)
                            if not account:
                                continue

                            # Determine reverse side
                            reverse_side = "sell" if position.side.lower() == "buy" else "buy"
                            hedge_quantity = (position.quantity or 0.0) * 0.5  # 0.5x size

                            if hedge_quantity <= 0:
                                continue

                            from app.infrastructure.container import Container
                            container = Container()
                            await container.initialize()

                            brokers = container.brokers()
                            broker_type = account.broker.value
                            broker_adapter = brokers.get(broker_type)

                            if broker_adapter and hasattr(broker_adapter, 'place_order'):
                                from app.models.pydantic_schemas import OrderRequest
                                order_request = OrderRequest(
                                    account_id=account.account_number,
                                    symbol=symbol,
                                    order_type=f"market_{reverse_side}",
                                    quantity=hedge_quantity,
                                    price=None,  # Market order
                                    stop_loss=None,
                                    take_profit=None
                                )
                                result = await broker_adapter.place_order(order_request)
                                if result and getattr(result, 'success', False):
                                    hedged_count += 1
                        except Exception as e:
                            logger.error(f"Failed to hedge position {position.id}: {e}")
                            continue

                    return {
                        "message": f"Hedged {hedged_count} position(s)",
                        "action": "hedge",
                        "hedged_count": hedged_count
                    }
        except Exception as e:
            logger.error(f"Hedge action failed: {e}")
            return {"message": f"Hedge action failed: {str(e)}", "action": "hedge", "error": str(e)}

    elif request.action == "execute":
        # User confirmed execution despite guard warning
        # Mark signal for execution (remove from pending confirmation)
        from app.models.database_models import Signal as SignalORM
        signal = db.query(SignalORM).filter(
            SignalORM.signal_id == request.signal_id
        ).first()

        if signal:
            # Update signal status to allow execution
            signal.status = "confirmed"
            db.commit()
            logger.info(f"Signal {request.signal_id} confirmed for execution by user {current_user.id}")
            return {
                "message": "Signal confirmed for execution",
                "action": "execute",
                "signal_id": request.signal_id
            }
        else:
            return {
                "message": "Signal not found, may have already been processed",
                "action": "execute",
                "signal_id": request.signal_id
            }

    elif request.action == "discard":
        # User chose to discard signal
        from app.models.database_models import Signal as SignalORM
        signal = db.query(SignalORM).filter(
            SignalORM.signal_id == request.signal_id
        ).first()

        if signal:
            signal.status = "discarded"
            db.commit()
            logger.info(f"Signal {request.signal_id} discarded by user {current_user.id}")

            # Log to discard bin
            discard_entry = DiscardBin(
                user_id=current_user.id,
                received_at=datetime.utcnow(),
                reason="user_discarded",
                symbol=signal.symbol,
                side=signal.action
            )
            db.add(discard_entry)
            db.commit()

        return {
            "message": "Signal discarded",
            "action": "discard",
            "signal_id": request.signal_id
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {request.action}"
        )


@router.get("/discard-bin", response_model=List[DiscardBinEntry])
async def get_discard_bin(
    limit: int = 100,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get discard bin entries for user"""
    query = db.query(DiscardBin).filter(
        DiscardBin.user_id == current_user.id
    )

    if reason:
        query = query.filter(DiscardBin.reason == reason)

    entries = query.order_by(DiscardBin.received_at.desc()).limit(limit).all()
    return entries


@router.post("/discard-bin/flush")
async def flush_discard_bin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Flush old discard bin entries"""
    guard = SignalIntelligenceGuard(db)
    deleted_count = await guard.flush_discard_bin(current_user.id)

    return {
        "message": f"Flushed {deleted_count} discard bin entries",
        "deleted_count": deleted_count
    }
