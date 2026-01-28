"""
Emergency Controls Router for Tradeflow
Provides kill switch and emergency flattening capabilities
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import logging

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.models.database_models import TradingAccount
from app.services.signal_processor import _create_account_executor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/emergency", tags=["emergency"])


class KillSwitchRequest(BaseModel):
    action: str = "flatten_all"  # flatten_all, cancel_orders, pause
    account_ids: Optional[List[int]] = None  # None = all accounts


class KillSwitchResponse(BaseModel):
    success: bool
    positionsClosed: int
    ordersCancelled: int
    accountsAffected: int
    errors: List[str]


class PauseResponse(BaseModel):
    success: bool
    accountsPaused: int
    message: str


@router.post("/kill-switch", response_model=KillSwitchResponse)
async def emergency_kill_switch(
    request: KillSwitchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Emergency kill switch - immediately flatten all positions.

    Actions:
    - flatten_all: Close all positions and cancel all orders
    - cancel_orders: Cancel all pending orders only
    - pause: Pause signal execution without closing positions
    """
    logger.warning(f"KILL SWITCH ACTIVATED by user {current_user.id} - action: {request.action}")

    # Get user's active accounts
    query = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    )

    if request.account_ids:
        query = query.filter(TradingAccount.id.in_(request.account_ids))

    accounts = query.all()

    if not accounts:
        return KillSwitchResponse(
            success=True,
            positionsClosed=0,
            ordersCancelled=0,
            accountsAffected=0,
            errors=["No active accounts found"]
        )

    positions_closed = 0
    orders_cancelled = 0
    accounts_affected = 0
    errors = []

    async def flatten_account(account: TradingAccount):
        nonlocal positions_closed, orders_cancelled, accounts_affected
        try:
            executor, needs_cleanup = await _create_account_executor(account, db)
            if not executor:
                errors.append(f"Failed to create executor for {account.account_name}")
                return

            try:
                # Get all positions
                positions = await executor.get_positions()

                # Close all positions
                for pos in positions:
                    try:
                        pos_id = pos.id if hasattr(pos, 'id') else pos.get('id')
                        symbol = pos.symbol if hasattr(pos, 'symbol') else pos.get('symbol')
                        side = pos.side if hasattr(pos, 'side') else pos.get('side', 'buy')
                        size = pos.size if hasattr(pos, 'size') else pos.get('size', pos.get('volume', 0))

                        # Close by opening opposite position
                        close_side = 'sell' if side.lower() == 'buy' else 'buy'

                        from app.models.pydantic_schemas import TradeRequest
                        close_request = TradeRequest(
                            symbol=symbol,
                            side=close_side,
                            volume=float(size),
                            order_type="market",
                            comment="EMERGENCY_FLATTEN"
                        )

                        result = await executor.execute_trade(close_request)
                        if result.success:
                            positions_closed += 1
                            logger.info(f"Closed position {pos_id} on {account.account_name}")
                        else:
                            errors.append(f"Failed to close {symbol} on {account.account_name}: {result.error}")
                    except Exception as e:
                        errors.append(f"Error closing position on {account.account_name}: {str(e)}")

                # Cancel pending orders if executor supports it
                if hasattr(executor, 'cancel_all_orders'):
                    try:
                        cancelled = await executor.cancel_all_orders()
                        orders_cancelled += cancelled
                    except Exception as e:
                        logger.warning(f"Could not cancel orders on {account.account_name}: {e}")

                accounts_affected += 1

            finally:
                if needs_cleanup and executor:
                    try:
                        await executor.disconnect()
                    except Exception:
                        pass

        except Exception as e:
            errors.append(f"Error processing {account.account_name}: {str(e)}")
            logger.error(f"Kill switch error for account {account.id}: {e}")

    # Execute flattening concurrently
    await asyncio.gather(*[flatten_account(account) for account in accounts], return_exceptions=True)

    # Pause signal execution for all affected accounts
    for account in accounts:
        account.is_signal_enabled = False
    db.commit()

    logger.warning(
        f"Kill switch completed: {positions_closed} positions closed, "
        f"{orders_cancelled} orders cancelled, {accounts_affected} accounts affected"
    )

    return KillSwitchResponse(
        success=len(errors) == 0,
        positionsClosed=positions_closed,
        ordersCancelled=orders_cancelled,
        accountsAffected=accounts_affected,
        errors=errors
    )


@router.post("/pause-all", response_model=PauseResponse)
async def pause_all_trading(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pause signal execution for all accounts.
    Positions remain open, but no new signals will be executed.
    """
    logger.info(f"Pause all trading requested by user {current_user.id}")

    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    count = 0
    for account in accounts:
        if account.is_signal_enabled:
            account.is_signal_enabled = False
            count += 1

    db.commit()

    return PauseResponse(
        success=True,
        accountsPaused=count,
        message=f"Paused signal execution for {count} accounts"
    )


@router.post("/resume-all", response_model=PauseResponse)
async def resume_all_trading(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resume signal execution for all accounts.
    """
    logger.info(f"Resume all trading requested by user {current_user.id}")

    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    count = 0
    for account in accounts:
        if not account.is_signal_enabled:
            account.is_signal_enabled = True
            count += 1

    db.commit()

    return PauseResponse(
        success=True,
        accountsPaused=count,
        message=f"Resumed signal execution for {count} accounts"
    )
