"""
ProjectX/TopStep Broker API Router

Exposes all ProjectX SDK features through REST API endpoints.
Follows broker-agnostic patterns consistent with other brokers.
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from app.models.database_models import TradingAccount, BrokerType as DBBrokerType
from app.core.encryption import decrypt
from app.brokers.projectx_executor import ProjectXExecutor
from app.domain.enums import BrokerType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brokers/projectx", tags=["projectx"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ProjectXAccountResponse(BaseModel):
    """Normalized account response"""
    id: str
    broker: str = "projectx"
    account_type: str
    currency: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float = 0.0
    leverage: int = 100
    is_active: bool = True
    is_live: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None  # Provider-specific fields


class ProjectXPositionResponse(BaseModel):
    """Normalized position response"""
    id: str
    broker: str = "projectx"
    account_id: str
    symbol: str
    side: str  # "buy" or "sell"
    size: float
    entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: float
    realized_pnl: float = 0.0
    margin: float = 0.0
    magic_number: int = 0
    comment: str = ""
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    is_active: bool = True
    raw: Optional[Dict[str, Any]] = None


class ProjectXOrderResponse(BaseModel):
    """Normalized order response"""
    id: str
    broker: str = "projectx"
    account_id: Optional[str] = None
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit", "stop"
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    timestamp: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class ProjectXOrderCreate(BaseModel):
    """Order creation request"""
    account_id: int = Field(..., description="Database account ID")
    symbol: str = Field(..., description="Instrument symbol (e.g., MNQ, MES)")
    side: str = Field(..., description="buy or sell")
    order_type: str = Field(..., description="market or limit")
    quantity: float = Field(..., gt=0, description="Number of contracts")
    price: Optional[float] = Field(None, description="Limit price (required for limit orders)")
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class ProjectXBracketOrderCreate(BaseModel):
    """Bracket order (OCO) creation request"""
    account_id: int
    symbol: str
    side: str
    quantity: float
    entry_price: Optional[float] = None  # None = market entry
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class ProjectXOrderModify(BaseModel):
    """Order modification request"""
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class ProjectXQuoteResponse(BaseModel):
    """Market quote response"""
    symbol: str
    bid: float
    ask: float
    last: Optional[float] = None
    volume: Optional[int] = None
    time: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class ProjectXOrderBookResponse(BaseModel):
    """Level 2 orderbook response"""
    symbol: str
    bids: List[Dict[str, float]] = Field(..., description="List of {price, size} bid levels")
    asks: List[Dict[str, float]] = Field(..., description="List of {price, size} ask levels")
    best_bid: float
    best_ask: float
    spread: float
    raw: Optional[Dict[str, Any]] = None


class ProjectXSessionStatsResponse(BaseModel):
    """Session statistics response"""
    session_type: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float
    raw: Optional[Dict[str, Any]] = None


class ProjectXPerformanceStatsResponse(BaseModel):
    """Performance statistics response"""
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    volatility: float
    raw: Optional[Dict[str, Any]] = None


class ProjectXTechnicalIndicatorsRequest(BaseModel):
    """Technical indicators calculation request"""
    symbol: str
    days: int = Field(30, ge=1, le=365)
    interval: int = Field(5, ge=1, description="Candle interval in minutes")
    indicators: Optional[List[str]] = Field(None, description="List of indicators to calculate. If None, calculates all.")


class ProjectXTechnicalIndicatorsResponse(BaseModel):
    """Technical indicators response"""
    symbol: str
    indicators: Dict[str, Any] = Field(..., description="Dict of indicator name to calculated values")
    raw: Optional[Dict[str, Any]] = None


class ProjectXPositionHistoryResponse(BaseModel):
    """Position history response"""
    positions: List[Dict[str, Any]]
    total: int
    raw: Optional[Dict[str, Any]] = None


class ProjectXPortfolioMetricsResponse(BaseModel):
    """Portfolio metrics response"""
    total_pnl: float
    win_rate: float
    total_positions: int
    winning_positions: int
    losing_positions: int
    raw: Optional[Dict[str, Any]] = None


class ProjectXRiskAnalysisResponse(BaseModel):
    """Risk analysis response"""
    max_position_size: float
    current_risk: float
    risk_per_trade: float
    max_drawdown: float
    raw: Optional[Dict[str, Any]] = None


class ProjectXStreamSubscribeRequest(BaseModel):
    """Stream subscription request"""
    symbol: str
    account_id: int


class ProjectXStreamSubscribeResponse(BaseModel):
    """Stream subscription response"""
    success: bool
    symbol: str
    subscribed: bool
    message: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

async def get_projectx_executor(
    account_id: int,
    current_user: User,
    db: Session
) -> ProjectXExecutor:
    """
    Get ProjectX executor with credentials from stored account.
    
    Args:
        account_id: Database account ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Initialized ProjectXExecutor
        
    Raises:
        HTTPException: If account not found, wrong user, or missing credentials
    """
    # Get account from database
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id,
        TradingAccount.broker == DBBrokerType.PROJECTX,
        TradingAccount.is_active == True
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProjectX account {account_id} not found or not accessible"
        )
    
    # Decrypt credentials
    # ProjectX credentials: username and api_key
    # They may be stored in TradingAccount.api_key/api_secret or in credential_repo
    username = None
    api_key = None
    
    try:
        # First, try to decrypt TradingAccount fields
        if account.api_key:
            try:
                decrypted_key = decrypt(account.api_key)
                # Check if it looks like username (email) or api_key (long token)
                if "@" in decrypted_key or len(decrypted_key) < 30:
                    username = decrypted_key
                else:
                    api_key = decrypted_key
            except Exception as e:
                logger.debug(f"Failed to decrypt api_key: {e}")
        
        if account.api_secret:
            try:
                decrypted_secret = decrypt(account.api_secret)
                if not username:
                    username = decrypted_secret
                elif not api_key:
                    api_key = decrypted_secret
            except Exception as e:
                logger.debug(f"Failed to decrypt api_secret: {e}")
        
        # Check metadata
        if (not username or not api_key) and account.metadata:
            import json
            try:
                metadata = json.loads(account.metadata) if isinstance(account.metadata, str) else account.metadata
                username = username or metadata.get("username")
                api_key = api_key or metadata.get("api_key")
            except Exception as e:
                logger.debug(f"Failed to parse metadata: {e}")
        
        # If still missing, try credential repository
        if not username or not api_key:
            try:
                from app.infrastructure.repositories.credential_repository import CredentialRepository
                from app.db.database import get_async_session
                async_session = next(get_async_session())
                cred_repo = CredentialRepository(async_session)
                
                # Get credentials for this account
                all_creds = await cred_repo.get_by_service("projectx")
                for cred in all_creds:
                    cred_data = cred.get("credential_data", {})
                    if cred_data.get("account_id") == account.account_number:
                        username = username or cred_data.get("username")
                        api_key = api_key or cred_data.get("api_key")
                        break
            except Exception as e:
                logger.debug(f"Failed to get credentials from repository: {e}")
        
        if not username or not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ProjectX account {account_id} missing credentials. Please update account credentials. Expected 'username' and 'api_key'."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve credentials for account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve account credentials. Please check account configuration."
        )
    except Exception as e:
        logger.error(f"Failed to decrypt credentials for account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt account credentials. Please check account configuration."
        )
    
    # Create executor
    executor = ProjectXExecutor(
        account_id=str(account.account_number),
        username=username,
        api_key=api_key,
        use_sdk=True
    )
    
    # Initialize
    success = await executor.initialize()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to ProjectX/TopStep. Please check your credentials and try again."
        )
    
    return executor


# ============================================================================
# Account Endpoints
# ============================================================================

@router.get("/accounts", response_model=List[ProjectXAccountResponse])
async def get_accounts(
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all ProjectX accounts from broker."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        accounts = await executor.get_accounts()
        return [
            ProjectXAccountResponse(
                id=str(acc.id),
                broker="projectx",
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


@router.get("/accounts/{account_id}", response_model=ProjectXAccountResponse)
async def get_account_info(
    account_id: int = Path(..., description="Database account ID"),
    broker_account_id: Optional[str] = Query(None, description="Broker account ID (optional)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get specific ProjectX account information."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        broker_acc_id = broker_account_id or str(account_id)
        account = await executor.get_account_info(broker_acc_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return ProjectXAccountResponse(
            id=str(account.id),
            broker="projectx",
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

@router.get("/positions", response_model=List[ProjectXPositionResponse])
async def get_positions(
    account_id: int = Query(..., description="Database account ID"),
    broker_account_id: Optional[str] = Query(None, description="Broker account ID filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all open positions."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        positions = await executor.get_positions(broker_account_id)
        return [
            ProjectXPositionResponse(
                id=str(pos.id),
                broker="projectx",
                account_id=str(pos.account_id),
                symbol=pos.symbol,
                side=pos.side,
                size=float(pos.size),
                entry_price=float(pos.entry_price),
                current_price=float(pos.current_price) if pos.current_price else None,
                unrealized_pnl=float(pos.unrealized_pnl),
                realized_pnl=float(getattr(pos, 'realized_pnl', 0)),
                margin=float(getattr(pos, 'margin', 0)),
                magic_number=getattr(pos, 'magic_number', 0),
                comment=getattr(pos, 'comment', ''),
                open_time=pos.open_time.isoformat() if hasattr(pos, 'open_time') and pos.open_time else None,
                close_time=pos.close_time.isoformat() if hasattr(pos, 'close_time') and pos.close_time else None,
                is_active=getattr(pos, 'is_active', True),
            )
            for pos in positions
        ]
    finally:
        await executor.disconnect()


@router.get("/positions/history", response_model=ProjectXPositionHistoryResponse)
async def get_position_history(
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get position history (closed positions)."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        history = await executor.get_position_history(symbol, days=days)
        return ProjectXPositionHistoryResponse(
            positions=history,
            total=len(history)
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Order Endpoints
# ============================================================================

@router.get("/orders", response_model=List[ProjectXOrderResponse])
async def get_orders(
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all pending orders."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        orders = await executor.get_orders()
        return [
            ProjectXOrderResponse(
                id=str(order.get("id", "")),
                broker="projectx",
                account_id=str(order.get("account_id", "")),
                symbol=order.get("symbol", ""),
                side=order.get("side", ""),
                order_type=order.get("order_type", ""),
                quantity=float(order.get("quantity", 0)),
                price=float(order.get("price", 0)) if order.get("price") else None,
                stop_loss=float(order.get("stop_loss", 0)) if order.get("stop_loss") else None,
                take_profit=float(order.get("take_profit", 0)) if order.get("take_profit") else None,
                status=order.get("status", "pending"),
                filled_quantity=float(order.get("filled_quantity", 0)),
                filled_price=float(order.get("filled_price", 0)) if order.get("filled_price") else None,
                timestamp=order.get("timestamp", datetime.now().isoformat()),
                raw=order,
            )
            for order in orders
        ]
    finally:
        await executor.disconnect()


@router.post("/orders", response_model=ProjectXOrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
    order_data: ProjectXOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place a new order."""
    executor = await get_projectx_executor(order_data.account_id, current_user, db)
    try:
        from app.models.pydantic_schemas import OrderRequest
        
        order_req = OrderRequest(
            account_id=str(order_data.account_id),
            symbol=order_data.symbol,
            order_type=order_data.order_type,
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
        
        return ProjectXOrderResponse(
            id=result.order_id,
            broker="projectx",
            account_id=str(order_data.account_id),
            symbol=order_data.symbol,
            side="buy" if "buy" in order_data.side.lower() else "sell",
            order_type=order_data.order_type,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
            status=result.status,
            filled_quantity=result.filled_quantity,
            filled_price=result.filled_price,
            timestamp=result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
        )
    finally:
        await executor.disconnect()


@router.patch("/orders/{order_id}", response_model=ProjectXOrderResponse)
async def modify_order(
    order_id: str = Path(..., description="Broker order ID"),
    account_id: int = Query(..., description="Database account ID"),
    modifications: ProjectXOrderModify = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Modify an existing order."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        mods = {}
        if modifications.price is not None:
            mods["price"] = modifications.price
        if modifications.stop_loss is not None:
            mods["stop_loss"] = modifications.stop_loss
        if modifications.take_profit is not None:
            mods["take_profit"] = modifications.take_profit
        
        result = await executor.modify_order(order_id, mods)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Order modification failed"
            )
        
        return ProjectXOrderResponse(
            id=order_id,
            broker="projectx",
            account_id=str(account_id),
            symbol="",  # Not returned by modify_order
            side="",
            order_type="",
            quantity=0,
            status=result.status,
            timestamp=result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
        )
    finally:
        await executor.disconnect()


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: str = Path(..., description="Broker order ID"),
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an order."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        result = await executor.cancel_order(order_id)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Order cancellation failed"
            )
    finally:
        await executor.disconnect()


@router.delete("/orders", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_all_orders(
    account_id: int = Query(..., description="Database account ID"),
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel all orders (optionally filtered by symbol)."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        # Get all orders first
        orders = await executor.get_orders()
        
        # Filter by symbol if provided
        if symbol:
            orders = [o for o in orders if o.get("symbol", "").upper() == symbol.upper()]
        
        # Cancel each order
        for order in orders:
            order_id = str(order.get("id", ""))
            if order_id:
                await executor.cancel_order(order_id)
    finally:
        await executor.disconnect()


@router.post("/orders/bracket", response_model=ProjectXOrderResponse, status_code=status.HTTP_201_CREATED)
async def place_bracket_order(
    order_data: ProjectXBracketOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place bracket order (OCO) with stop loss and take profit."""
    executor = await get_projectx_executor(order_data.account_id, current_user, db)
    try:
        result = await executor.place_bracket_order(
            instrument=order_data.symbol,
            side=order_data.side,
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
        
        return ProjectXOrderResponse(
            id=result.order_id,
            broker="projectx",
            account_id=str(order_data.account_id),
            symbol=order_data.symbol,
            side=order_data.side,
            order_type="bracket",
            quantity=order_data.quantity,
            price=order_data.entry_price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
            status=result.status,
            timestamp=result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Market Data Endpoints
# ============================================================================

@router.get("/market/quote", response_model=ProjectXQuoteResponse)
async def get_quote(
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get real-time quote for symbol."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        quote = await executor.get_quote(symbol)
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quote not available for {symbol}"
            )
        
        return ProjectXQuoteResponse(
            symbol=symbol,
            bid=float(quote.get("bid", 0)),
            ask=float(quote.get("ask", 0)),
            last=float(quote.get("last", 0)) if quote.get("last") else None,
            volume=int(quote.get("volume", 0)) if quote.get("volume") else None,
            time=quote.get("time", datetime.now().isoformat()),
            raw=quote,
        )
    finally:
        await executor.disconnect()


@router.get("/market/orderbook", response_model=ProjectXOrderBookResponse)
async def get_orderbook(
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    depth: int = Query(10, ge=1, le=50, description="Number of price levels"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Level 2 orderbook (market depth)."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        orderbook = await executor.get_orderbook(symbol, depth=depth)
        if not orderbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orderbook not available for {symbol}"
            )
        
        return ProjectXOrderBookResponse(
            symbol=symbol,
            bids=orderbook.get("bids", []),
            asks=orderbook.get("asks", []),
            best_bid=float(orderbook.get("best_bid", 0)),
            best_ask=float(orderbook.get("best_ask", 0)),
            spread=float(orderbook.get("spread", 0)),
            raw=orderbook,
        )
    finally:
        await executor.disconnect()


@router.get("/market/history")
async def get_market_history(
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    days: int = Query(1, ge=1, le=365, description="Number of days"),
    interval: int = Query(5, ge=1, description="Candle interval in minutes"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get historical market data (OHLCV)."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        from app.services.projectx_sdk_service import ProjectXSDKService
        
        # Get SDK service to access get_market_data
        if not executor.is_using_sdk:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Market history requires SDK mode"
            )
        
        # Access SDK service directly for market data
        market_data = await executor._sdk_service.get_market_data(
            instrument=symbol,
            days=days,
            interval=interval
        )
        
        return {
            "symbol": symbol,
            "data": market_data,
            "days": days,
            "interval": interval,
        }
    finally:
        await executor.disconnect()


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats/session", response_model=ProjectXSessionStatsResponse)
async def get_session_statistics(
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    session_type: Optional[str] = Query(None, description="Optional session type filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get session statistics and analytics."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        stats = await executor.get_session_statistics(symbol, session_type)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session statistics not available"
            )
        
        return ProjectXSessionStatsResponse(
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


@router.get("/stats/performance", response_model=ProjectXPerformanceStatsResponse)
async def get_performance_stats(
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get performance statistics (Sharpe ratio, max drawdown, etc.)."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        stats = await executor.get_performance_stats(symbol)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Performance statistics not available"
            )
        
        return ProjectXPerformanceStatsResponse(
            sharpe_ratio=stats.get("sharpe_ratio", 0.0),
            max_drawdown=stats.get("max_drawdown", 0.0),
            total_return=stats.get("total_return", 0.0),
            volatility=stats.get("volatility", 0.0),
            raw=stats,
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Technical Indicators Endpoint
# ============================================================================

@router.post("/indicators", response_model=ProjectXTechnicalIndicatorsResponse)
async def calculate_technical_indicators(
    request: ProjectXTechnicalIndicatorsRequest,
    account_id: int = Query(..., description="Database account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate technical indicators for symbol."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        indicators = await executor.calculate_technical_indicators(
            symbol=request.symbol,
            days=request.days,
            interval=request.interval,
        )
        
        # Filter indicators if specific list provided
        if request.indicators:
            filtered = {k: v for k, v in indicators.items() if k in request.indicators}
            indicators = filtered
        
        return ProjectXTechnicalIndicatorsResponse(
            symbol=request.symbol,
            indicators=indicators,
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Portfolio & Risk Endpoints
# ============================================================================

@router.get("/portfolio/metrics", response_model=ProjectXPortfolioMetricsResponse)
async def get_portfolio_metrics(
    account_id: int = Query(..., description="Database account ID"),
    instruments: Optional[str] = Query(None, description="Comma-separated list of instruments"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get portfolio metrics across multiple instruments."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        inst_list = [i.strip() for i in instruments.split(",")] if instruments else None
        metrics = await executor.get_portfolio_metrics(inst_list)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio metrics not available"
            )
        
        return ProjectXPortfolioMetricsResponse(
            total_pnl=metrics.get("total_pnl", 0.0),
            win_rate=metrics.get("win_rate", 0.0),
            total_positions=metrics.get("total_positions", 0),
            winning_positions=metrics.get("winning_positions", 0),
            losing_positions=metrics.get("losing_positions", 0),
            raw=metrics,
        )
    finally:
        await executor.disconnect()


@router.get("/risk/analysis", response_model=ProjectXRiskAnalysisResponse)
async def get_risk_analysis(
    account_id: int = Query(..., description="Database account ID"),
    symbol: str = Query(..., description="Instrument symbol"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get risk analysis for positions."""
    executor = await get_projectx_executor(account_id, current_user, db)
    try:
        risk = await executor.get_risk_analysis(symbol)
        if not risk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk analysis not available"
            )
        
        return ProjectXRiskAnalysisResponse(
            max_position_size=risk.get("max_position_size", 0.0),
            current_risk=risk.get("current_risk", 0.0),
            risk_per_trade=risk.get("risk_per_trade", 0.0),
            max_drawdown=risk.get("max_drawdown", 0.0),
            raw=risk,
        )
    finally:
        await executor.disconnect()


# ============================================================================
# Streaming Endpoints
# ============================================================================

@router.post("/stream/subscribe", response_model=ProjectXStreamSubscribeResponse)
async def subscribe_stream(
    request: ProjectXStreamSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Subscribe to real-time market data stream."""
    executor = await get_projectx_executor(request.account_id, current_user, db)
    try:
        result = await executor.subscribe_realtime_data(request.symbol)
        
        return ProjectXStreamSubscribeResponse(
            success=result.get("success", False),
            symbol=request.symbol,
            subscribed=result.get("subscribed", False),
            message=result.get("error"),
        )
    finally:
        # Don't disconnect - keep connection for streaming
        pass
