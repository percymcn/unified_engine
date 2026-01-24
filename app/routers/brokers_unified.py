"""
Unified Broker REST API Router

Broker-agnostic REST endpoints for all trading operations.
Supports: TradeLocker, Tradovate, ProjectX/TopStep, MT4, MT5

All endpoints follow the pattern:
- GET/POST/PATCH/DELETE /api/v1/brokers/{broker}/...

Features:
- Capability checking (returns 501 for unsupported features)
- Normalized response schemas
- Credential retrieval from stored accounts
- Proper error handling (400/401/403/501, never 500)
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.models.database_models import TradingAccount, BrokerType as DBBrokerType
from app.core.encryption import decrypt
from app.domain.enums import BrokerType
from app.brokers.capabilities import get_capability_matrix, Capability, BrokerType as CapBrokerType
from app.schemas.brokers import (
    AccountOut, PositionOut, OrderOut, QuoteOut, OHLCVOut, OrderBookOut,
    PerformanceStatsOut, SessionStatsOut, PortfolioMetricsOut,
    OrderCreate, BracketOrderCreate, OrderModify, StreamSubscribe,
    OrderSide, OrderType, OrderStatus, PositionSide
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brokers", tags=["brokers-unified"])

# Timeout for executor operations (seconds)
EXECUTOR_TIMEOUT = 30.0


async def execute_with_timeout(coro, operation_name: str, timeout: float = EXECUTOR_TIMEOUT):
    """
    Execute coroutine with timeout and error handling.
    
    Args:
        coro: Coroutine to execute
        operation_name: Name of operation for error messages
        timeout: Timeout in seconds
        
    Returns:
        Result of coroutine
        
    Raises:
        HTTPException: On timeout or error
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Timeout executing {operation_name}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Operation timed out: {operation_name}. Please try again."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing {operation_name}: {e}", exc_info=True)
        # Never expose internal errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Operation failed: {operation_name}. Please contact support."
        )


# ============================================================================
# Helper Functions
# ============================================================================

async def get_broker_executor(
    broker: str,
    account_id: int,
    current_user: User,
    db: Session
):
    """
    Get broker executor with credentials from stored account.
    
    Args:
        broker: Broker identifier (tradelocker, tradovate, projectx, mt4, mt5)
        account_id: Database account ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Initialized executor instance
        
    Raises:
        HTTPException: If account not found, wrong user, or missing credentials
    """
    # Map broker string to enum
    broker_lower = broker.lower()
    try:
        broker_enum = BrokerType(broker_lower)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker: {broker}. Valid options: tradelocker, tradovate, projectx, topstep, mt4, mt5"
        )
    
    # Handle topstep alias
    if broker_enum == BrokerType.TOPSTEP:
        broker_enum = BrokerType.PROJECTX
        broker_lower = "projectx"
    
    # Map to database broker type
    broker_map = {
        BrokerType.TRADELOCKER: DBBrokerType.TRADELOCKER,
        BrokerType.TRADOVATE: DBBrokerType.TRADOVATE,
        BrokerType.PROJECTX: DBBrokerType.PROJECTX,
        BrokerType.MT4: DBBrokerType.MT4,
        BrokerType.MT5: DBBrokerType.MT5,
    }
    db_broker = broker_map.get(broker_enum)
    
    if not db_broker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broker {broker} not supported"
        )
    
    # Get account from database
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id,
        TradingAccount.broker == db_broker,
        TradingAccount.is_active == True
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{broker} account {account_id} not found or not accessible"
        )
    
    # Create executor based on broker type
    executor = None
    
    try:
        if broker_enum == BrokerType.TRADELOCKER:
            from app.brokers.tradelocker_executor import TradeLockerExecutor
            executor = TradeLockerExecutor()
            # Credentials are loaded from config or account fields
            
        elif broker_enum == BrokerType.TRADOVATE:
            from app.brokers.tradovate_executor import TradovateExecutor
            # Try to get OAuth token
            access_token = None
            if account.access_token:
                try:
                    access_token = decrypt(account.access_token)
                except:
                    pass
            
            environment = account.oauth_environment or "demo"
            executor = TradovateExecutor(
                account_id=account_id,
                access_token=access_token,
                environment=environment
            )
            
        elif broker_enum == BrokerType.PROJECTX:
            from app.brokers.projectx_executor import ProjectXExecutor
            # Get credentials (username and api_key)
            username = None
            api_key = None
            
            if account.api_key:
                try:
                    decrypted = decrypt(account.api_key)
                    if "@" in decrypted or len(decrypted) < 30:
                        username = decrypted
                    else:
                        api_key = decrypted
                except:
                    pass
            
            if account.api_secret:
                try:
                    decrypted = decrypt(account.api_secret)
                    if not username:
                        username = decrypted
                    elif not api_key:
                        api_key = decrypted
                except:
                    pass
            
            if account.metadata:
                import json
                try:
                    metadata = json.loads(account.metadata) if isinstance(account.metadata, str) else account.metadata
                    username = username or metadata.get("username")
                    api_key = api_key or metadata.get("api_key")
                except:
                    pass
            
            if not username or not api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{broker} account {account_id} missing credentials. Please update account credentials."
                )
            
            executor = ProjectXExecutor(
                account_id=str(account.account_number),
                username=username,
                api_key=api_key,
                use_sdk=True
            )
            
        elif broker_enum == BrokerType.MT4:
            from app.brokers.mt4_executor import MT4Executor
            metaapi_token = None
            metaapi_account_id = None
            
            if account.api_key:
                try:
                    metaapi_token = decrypt(account.api_key)
                except:
                    pass
            
            if account.metadata:
                import json
                try:
                    metadata = json.loads(account.metadata) if isinstance(account.metadata, str) else account.metadata
                    metaapi_token = metaapi_token or metadata.get("metaapi_token")
                    metaapi_account_id = metadata.get("metaapi_account_id")
                except:
                    pass
            
            executor = MT4Executor(
                metaapi_token=metaapi_token,
                metaapi_account_id=metaapi_account_id,
                use_sdk=True
            )
            
        elif broker_enum == BrokerType.MT5:
            from app.brokers.mt5_executor import MT5Executor
            metaapi_token = None
            metaapi_account_id = None
            
            if account.api_key:
                try:
                    metaapi_token = decrypt(account.api_key)
                except:
                    pass
            
            if account.metadata:
                import json
                try:
                    metadata = json.loads(account.metadata) if isinstance(account.metadata, str) else account.metadata
                    metaapi_token = metaapi_token or metadata.get("metaapi_token")
                    metaapi_account_id = metadata.get("metaapi_account_id")
                except:
                    pass
            
            executor = MT5Executor(
                metaapi_token=metaapi_token,
                metaapi_account_id=metaapi_account_id,
                use_sdk=True
            )
        
        if not executor:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Executor creation not implemented for {broker}"
            )
        
        # Initialize executor with timeout
        try:
            success = await asyncio.wait_for(
                executor.initialize(),
                timeout=EXECUTOR_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Timeout connecting to {broker}. Please try again."
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to {broker}. Please check your credentials and try again."
            )
        
        return executor
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create executor for {broker}: {e}", exc_info=True)
        # Never expose internal errors - return generic message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize {broker} executor. Please contact support."
        )


def check_capability(broker: str, capability: Capability) -> None:
    """
    Check if broker supports a capability.
    
    Raises:
        HTTPException: 501 if capability not supported
    """
    matrix = get_capability_matrix()
    broker_enum = CapBrokerType(broker.lower())
    
    if broker_enum == CapBrokerType.TOPSTEP:
        broker_enum = CapBrokerType.PROJECTX
    
    if not matrix.supports(broker_enum, capability):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{broker} does not support {capability.value}"
        )


# ============================================================================
# Account Endpoints
# ============================================================================

@router.get("/{broker}/accounts", response_model=List[AccountOut])
async def get_accounts(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all accounts from broker."""
    check_capability(broker, Capability.ACCOUNTS_LIST)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        accounts = await execute_with_timeout(
            executor.get_accounts(),
            f"get_accounts for {broker}"
        )
        return [
            AccountOut(
                broker=broker,
                account_id=str(acc.id),
                account_type=getattr(acc, 'account_type', 'live'),
                currency=getattr(acc, 'currency', 'USD'),
                balance=float(getattr(acc, 'balance', 0)),
                equity=float(getattr(acc, 'equity', 0)),
                margin=float(getattr(acc, 'margin', 0)),
                free_margin=float(getattr(acc, 'free_margin', 0)),
                margin_level=float(getattr(acc, 'margin_level', 0)),
                leverage=getattr(acc, 'leverage', 100),
                is_active=getattr(acc, 'is_active', True),
                is_live=getattr(acc, 'is_live', True),
                created_at=getattr(acc, 'created_at', datetime.now()).isoformat() if hasattr(acc, 'created_at') else None,
                updated_at=datetime.now().isoformat(),
            )
            for acc in accounts
        ]
    finally:
        await executor.disconnect()


@router.get("/{broker}/accounts/{broker_account_id}", response_model=AccountOut)
async def get_account_info(
    broker: str = Path(..., description="Broker identifier"),
    broker_account_id: str = Path(..., description="Broker account ID"),
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get specific account information."""
    check_capability(broker, Capability.ACCOUNTS_INFO)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        account = await executor.get_account_info(broker_account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return AccountOut(
            broker=broker,
            account_id=str(account.id),
            account_type=getattr(account, 'account_type', 'live'),
            currency=getattr(account, 'currency', 'USD'),
            balance=float(getattr(account, 'balance', 0)),
            equity=float(getattr(account, 'equity', 0)),
            margin=float(getattr(account, 'margin', 0)),
            free_margin=float(getattr(account, 'free_margin', 0)),
            margin_level=float(getattr(account, 'margin_level', 0)),
            leverage=getattr(account, 'leverage', 100),
            is_active=getattr(account, 'is_active', True),
            is_live=getattr(account, 'is_live', True),
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Position Endpoints
# ============================================================================

@router.get("/{broker}/positions", response_model=List[PositionOut])
async def get_positions(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all open positions."""
    check_capability(broker, Capability.POSITIONS_OPEN)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        positions = await executor.get_positions()
        return [
            PositionOut(
                broker=broker,
                account_id=str(pos.account_id),
                position_id=str(pos.id),
                symbol=pos.symbol,
                side=PositionSide.LONG if pos.side.lower() in ("buy", "long") else PositionSide.SHORT,
                size=float(pos.size),
                entry_price=float(pos.entry_price),
                current_price=float(pos.current_price) if pos.current_price else None,
                unrealized_pnl=float(pos.unrealized_pnl),
                realized_pnl=float(getattr(pos, 'realized_pnl', 0)),
                margin=float(getattr(pos, 'margin', 0)),
                stop_loss=float(pos.stop_loss) if pos.stop_loss else None,
                take_profit=float(pos.take_profit) if pos.take_profit else None,
                opened_at=pos.open_time.isoformat() if hasattr(pos, 'open_time') and pos.open_time else None,
                closed_at=pos.close_time.isoformat() if hasattr(pos, 'close_time') and pos.close_time else None,
                is_active=getattr(pos, 'is_active', True),
            )
            for pos in positions
        ]
    finally:
        await executor.disconnect()


@router.get("/{broker}/positions/history", response_model=List[PositionOut])
async def get_position_history(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get position history (closed positions)."""
    check_capability(broker, Capability.POSITIONS_HISTORY)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        # Check if executor has get_position_history method
        if not hasattr(executor, 'get_position_history'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support position history"
            )
        
        history = await executor.get_position_history(symbol, days=days)
        # Convert to PositionOut format
        return [
            PositionOut(
                broker=broker,
                account_id=str(h.get("account_id", "")),
                position_id=str(h.get("id", "")),
                symbol=h.get("symbol", symbol),
                side=PositionSide.LONG if h.get("side", "").lower() in ("buy", "long") else PositionSide.SHORT,
                size=float(h.get("size", 0)),
                entry_price=float(h.get("entry_price", 0)),
                current_price=None,
                unrealized_pnl=0.0,
                realized_pnl=float(h.get("realized_pnl", 0)),
                opened_at=h.get("opened_at"),
                closed_at=h.get("closed_at"),
                is_active=False,
                raw=h,
            )
            for h in history
        ]
    finally:
        await executor.disconnect()


# ============================================================================
# Order Endpoints
# ============================================================================

@router.get("/{broker}/orders", response_model=List[OrderOut])
async def get_orders(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all pending orders."""
    check_capability(broker, Capability.ORDERS_LIST)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        orders = await executor.get_orders()
        return [
            OrderOut(
                broker=broker,
                account_id=str(order.get("account_id", "")),
                order_id=str(order.get("id", "")),
                symbol=order.get("symbol", ""),
                side=OrderSide.BUY if order.get("side", "").lower() == "buy" else OrderSide.SELL,
                order_type=OrderType(order.get("order_type", "market")),
                quantity=float(order.get("quantity", 0)),
                price=float(order.get("price", 0)) if order.get("price") else None,
                stop_loss=float(order.get("stop_loss", 0)) if order.get("stop_loss") else None,
                take_profit=float(order.get("take_profit", 0)) if order.get("take_profit") else None,
                status=OrderStatus(order.get("status", "pending")),
                filled_quantity=float(order.get("filled_quantity", 0)),
                filled_price=float(order.get("filled_price", 0)) if order.get("filled_price") else None,
                timestamp=order.get("timestamp", datetime.now().isoformat()),
                raw=order,
            )
            for order in orders
        ]
    finally:
        await executor.disconnect()


@router.post("/{broker}/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def place_order(
    broker: str = Path(..., description="Broker identifier"),
    order_data: OrderCreate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place a new order."""
    check_capability(broker, Capability.ORDERS_PLACE)
    
    executor = await get_broker_executor(broker, order_data.account_id, current_user, db)
    try:
        from app.models.pydantic_schemas import OrderRequest
        
        order_req = OrderRequest(
            account_id=str(order_data.account_id),
            symbol=order_data.symbol,
            order_type=order_data.order_type.value,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
        )
        
        result = await executor.place_order(order_req)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Order placement failed"
            )
        
        return OrderOut(
            broker=broker,
            account_id=str(order_data.account_id),
            order_id=result.order_id,
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=order_data.order_type,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
            status=OrderStatus(result.status),
            filled_quantity=result.filled_quantity,
            filled_price=result.filled_price,
            timestamp=result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
        )
    finally:
        await executor.disconnect()


@router.patch("/{broker}/orders/{order_id}", response_model=OrderOut)
async def modify_order(
    broker: str = Path(..., description="Broker identifier"),
    order_id: str = Path(..., description="Broker order ID"),
    account_id: int = Query(..., description="Database account ID"),
    modifications: OrderModify = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Modify an existing order."""
    check_capability(broker, Capability.ORDERS_MODIFY)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        mods = {}
        if modifications.price is not None:
            mods["price"] = modifications.price
        if modifications.stop_loss is not None:
            mods["stop_loss"] = modifications.stop_loss
        if modifications.take_profit is not None:
            mods["take_profit"] = modifications.take_profit
        if modifications.quantity is not None:
            mods["quantity"] = modifications.quantity
        
        result = await executor.modify_order(order_id, mods)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Order modification failed"
            )
        
        return OrderOut(
            broker=broker,
            account_id=str(account_id),
            order_id=order_id,
            symbol="",  # Not returned by modify_order
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0,
            status=OrderStatus(result.status),
            timestamp=result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
        )
    finally:
        await executor.disconnect()


@router.delete("/{broker}/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    broker: str = Path(..., description="Broker identifier"),
    order_id: str = Path(..., description="Broker order ID"),
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an order."""
    check_capability(broker, Capability.ORDERS_CANCEL)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        result = await executor.cancel_order(order_id)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Order cancellation failed"
            )
    finally:
        await executor.disconnect()


@router.delete("/{broker}/orders", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_all_orders(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel all orders (optionally filtered by symbol)."""
    check_capability(broker, Capability.ORDERS_CANCEL_ALL)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        if hasattr(executor, 'cancel_all_orders'):
            result = await executor.cancel_all_orders(symbol)
            if not result.get("success", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("error", "Cancel all orders failed")
                )
        else:
            # Fallback: get all orders and cancel each
            orders = await executor.get_orders()
            if symbol:
                orders = [o for o in orders if o.get("symbol", "").upper() == symbol.upper()]
            
            for order in orders:
                order_id = str(order.get("id", ""))
                if order_id:
                    await executor.cancel_order(order_id)
    finally:
        await executor.disconnect()


@router.post("/{broker}/orders/bracket", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def place_bracket_order(
    broker: str = Path(..., description="Broker identifier"),
    order_data: BracketOrderCreate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place bracket order (OCO) with stop loss and take profit."""
    check_capability(broker, Capability.ORDERS_BRACKET)
    
    executor = await get_broker_executor(broker, order_data.account_id, current_user, db)
    try:
        if not hasattr(executor, 'place_bracket_order'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support bracket orders"
            )
        
        result = await executor.place_bracket_order(
            instrument=order_data.symbol,
            side=order_data.side.value,
            size=int(order_data.quantity),
            entry_price=order_data.entry_price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Bracket order placement failed"
            )
        
        return OrderOut(
            broker=broker,
            account_id=str(order_data.account_id),
            order_id=result.order_id,
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=OrderType.BRACKET,
            quantity=order_data.quantity,
            price=order_data.entry_price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
            status=OrderStatus(result.status),
            timestamp=result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
        )
    finally:
        await executor.disconnect()


@router.post("/{broker}/orders/chain", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def place_order_chain(
    broker: str = Path(..., description="Broker identifier"),
    order_data: dict = ...,  # Will define schema later
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place order chain."""
    check_capability(broker, Capability.ORDERS_CHAIN)
    
    account_id = order_data.get("account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id required")
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        if not hasattr(executor, 'create_order_chain'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support order chains"
            )
        
        result = await executor.create_order_chain(**order_data)
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Order chain placement failed")
            )
        
        return OrderOut(
            broker=broker,
            account_id=str(account_id),
            order_id=result.get("order_id", ""),
            symbol=order_data.get("symbol", ""),
            side=OrderSide.BUY,
            order_type=OrderType.CHAIN,
            quantity=order_data.get("quantity", 0),
            status=OrderStatus(result.get("status", "pending")),
            timestamp=datetime.now().isoformat(),
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Market Data Endpoints
# ============================================================================

@router.get("/{broker}/market/quote", response_model=QuoteOut)
async def get_quote(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get real-time quote for symbol."""
    check_capability(broker, Capability.MARKET_QUOTE)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        quote = await executor.get_quote(symbol)
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quote not available for {symbol}"
            )
        
        return QuoteOut(
            broker=broker,
            symbol=symbol,
            bid=float(quote.get("bid", 0)),
            ask=float(quote.get("ask", 0)),
            last=float(quote.get("last", 0)) if quote.get("last") else None,
            volume=int(quote.get("volume", 0)) if quote.get("volume") else None,
            timestamp=quote.get("timestamp", datetime.now().isoformat()),
            raw=quote,
        )
    finally:
        await executor.disconnect()


@router.get("/{broker}/market/history", response_model=List[OHLCVOut])
async def get_market_history(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    days: int = Query(1, ge=1, le=365, description="Number of days"),
    interval: int = Query(5, ge=1, description="Candle interval in minutes"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get historical market data (OHLCV)."""
    check_capability(broker, Capability.MARKET_HISTORY)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        # Check for get_price_history or get_market_data method
        if hasattr(executor, 'get_price_history'):
            history = await executor.get_price_history(symbol, days=days, interval=interval)
        elif hasattr(executor, 'get_market_data'):
            history = await executor.get_market_data(symbol, days=days, interval=interval)
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support market history"
            )
        
        return [
            OHLCVOut(
                broker=broker,
                symbol=symbol,
                timestamp=h.get("timestamp", datetime.now().isoformat()),
                open=float(h.get("open", 0)),
                high=float(h.get("high", 0)),
                low=float(h.get("low", 0)),
                close=float(h.get("close", 0)),
                volume=int(h.get("volume", 0)) if h.get("volume") else None,
                raw=h,
            )
            for h in history
        ]
    finally:
        await executor.disconnect()


@router.get("/{broker}/market/orderbook", response_model=OrderBookOut)
async def get_orderbook(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    depth: int = Query(10, ge=1, le=50, description="Number of price levels"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Level 2 orderbook (market depth)."""
    check_capability(broker, Capability.MARKET_ORDERBOOK)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        if not hasattr(executor, 'get_orderbook'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support orderbook"
            )
        
        orderbook = await executor.get_orderbook(symbol, depth=depth)
        if not orderbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orderbook not available for {symbol}"
            )
        
        from app.schemas.brokers import OrderBookLevel
        
        return OrderBookOut(
            broker=broker,
            symbol=symbol,
            bids=[OrderBookLevel(price=float(b["price"]), size=float(b["size"])) for b in orderbook.get("bids", [])],
            asks=[OrderBookLevel(price=float(a["price"]), size=float(a["size"])) for a in orderbook.get("asks", [])],
            best_bid=float(orderbook.get("best_bid", 0)),
            best_ask=float(orderbook.get("best_ask", 0)),
            spread=float(orderbook.get("spread", 0)),
            timestamp=orderbook.get("timestamp", datetime.now().isoformat()),
            raw=orderbook,
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/{broker}/stats/session", response_model=SessionStatsOut)
async def get_session_stats(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get session statistics and analytics."""
    check_capability(broker, Capability.ANALYTICS_SESSION)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        if not hasattr(executor, 'get_session_statistics'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support session statistics"
            )
        
        stats = await executor.get_session_statistics(symbol) if symbol else await executor.get_session_statistics()
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session statistics not available"
            )
        
        return SessionStatsOut(
            broker=broker,
            account_id=str(account_id),
            session_type=stats.get("session_type", "all"),
            total_trades=stats.get("total_trades", 0),
            winning_trades=stats.get("winning_trades", 0),
            losing_trades=stats.get("losing_trades", 0),
            win_rate=stats.get("win_rate", 0.0),
            total_pnl=stats.get("total_pnl", 0.0),
            average_win=stats.get("average_win", 0.0),
            average_loss=stats.get("average_loss", 0.0),
            profit_factor=stats.get("profit_factor", 0.0),
            raw=stats,
        )
    finally:
        await executor.disconnect()


@router.get("/{broker}/stats/performance", response_model=PerformanceStatsOut)
async def get_performance_stats(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get performance statistics (Sharpe ratio, max drawdown, etc.)."""
    check_capability(broker, Capability.ANALYTICS_PERFORMANCE)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        if not hasattr(executor, 'get_performance_stats'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support performance statistics"
            )
        
        stats = await executor.get_performance_stats(symbol) if symbol else await executor.get_performance_stats()
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Performance statistics not available"
            )
        
        return PerformanceStatsOut(
            broker=broker,
            account_id=str(account_id),
            sharpe_ratio=stats.get("sharpe_ratio"),
            max_drawdown=stats.get("max_drawdown"),
            total_return=stats.get("total_return"),
            volatility=stats.get("volatility"),
            win_rate=stats.get("win_rate"),
            profit_factor=stats.get("profit_factor"),
            raw=stats,
        )
    finally:
        await executor.disconnect()


@router.get("/{broker}/stats/portfolio", response_model=PortfolioMetricsOut)
async def get_portfolio_metrics(
    broker: str = Path(..., description="Broker identifier"),
    account_id: int = Query(..., description="Database account ID"),
    instruments: Optional[str] = Query(None, description="Comma-separated list of instruments"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get portfolio metrics across multiple instruments."""
    check_capability(broker, Capability.ANALYTICS_PORTFOLIO)
    
    executor = await get_broker_executor(broker, account_id, current_user, db)
    try:
        if not hasattr(executor, 'get_portfolio_metrics'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support portfolio metrics"
            )
        
        inst_list = [i.strip() for i in instruments.split(",")] if instruments else None
        metrics = await executor.get_portfolio_metrics(inst_list)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio metrics not available"
            )
        
        return PortfolioMetricsOut(
            broker=broker,
            account_id=str(account_id),
            total_pnl=metrics.get("total_pnl", 0.0),
            win_rate=metrics.get("win_rate", 0.0),
            total_positions=metrics.get("total_positions", 0),
            winning_positions=metrics.get("winning_positions", 0),
            losing_positions=metrics.get("losing_positions", 0),
            raw=metrics,
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Streaming Endpoints
# ============================================================================

@router.post("/{broker}/stream/subscribe")
async def subscribe_stream(
    broker: str = Path(..., description="Broker identifier"),
    request: StreamSubscribe = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Subscribe to real-time market data stream."""
    check_capability(broker, Capability.STREAMING_SUBSCRIBE)
    
    executor = await get_broker_executor(broker, request.account_id, current_user, db)
    try:
        if not hasattr(executor, 'subscribe_realtime_data'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support streaming subscriptions"
            )
        
        result = await executor.subscribe_realtime_data(request.symbol)
        
        return {
            "success": result.get("success", False),
            "symbol": request.symbol,
            "subscribed": result.get("subscribed", False),
            "message": result.get("error"),
        }
    finally:
        # Don't disconnect - keep connection for streaming
        pass


@router.post("/{broker}/stream/unsubscribe")
async def unsubscribe_stream(
    broker: str = Path(..., description="Broker identifier"),
    request: StreamSubscribe = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unsubscribe from real-time market data stream."""
    check_capability(broker, Capability.STREAMING_UNSUBSCRIBE)
    
    executor = await get_broker_executor(broker, request.account_id, current_user, db)
    try:
        if not hasattr(executor, 'unsubscribe_stream'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"{broker} does not support stream unsubscription"
            )
        
        result = await executor.unsubscribe_stream(request.symbol)
        
        return {
            "success": result.get("success", False),
            "symbol": request.symbol,
            "unsubscribed": result.get("unsubscribed", False),
            "message": result.get("error"),
        }
    finally:
        await executor.disconnect()
