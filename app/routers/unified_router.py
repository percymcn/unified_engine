"""
Unified Router
Consolidates all broker endpoints into a single unified API
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from app.services.signal_processor import signal_processor
from app.models.pydantic_schemas import (
    Account, Position, SignalRequest, SignalResponse,
    OrderRequest, OrderResponse, TradeRequest, TradeResponse,
    WebhookRequest
)
from app.models.schemas import (
    Order, Trade, Signal
)
from app.models.pydantic_schemas import (
    HealthResponse
)
from app.db.database import get_db
from app.routers.auth import get_current_user, verify_api_key
from app.models.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/unified", tags=["unified"])

class UnifiedRouter:
    """Unified router for all broker operations"""
    
    def __init__(self):
        self.brokers = signal_processor.brokers
        self.supported_brokers = list(self.brokers.keys())
    
    async def get_broker_instance(self, broker_name: str):
        """Get broker instance by name"""
        if broker_name not in self.brokers:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported broker: {broker_name}. Supported: {self.supported_brokers}"
            )
        
        broker = self.brokers[broker_name]
        if not broker.is_connected:
            raise HTTPException(
                status_code=503,
                detail=f"Broker {broker_name} is not connected"
            )
        
        return broker
    
    async def aggregate_broker_data(self, func_name: str, *args, **kwargs) -> List[Any]:
        """Aggregate data from all connected brokers"""
        results = []
        
        for broker_name, broker in self.brokers.items():
            if not broker.is_connected:
                continue
            
            try:
                func = getattr(broker, func_name)
                broker_results = await func(*args, **kwargs)
                
                # Add broker info to each result
                for result in broker_results:
                    if hasattr(result, '__dict__'):
                        result.broker = broker_name
                    elif isinstance(result, dict):
                        result['broker'] = broker_name
                
                results.extend(broker_results)
                
            except Exception as e:
                logger.error(f"Error getting {func_name} from {broker_name}: {e}")
                continue
        
        return results

# Global unified router instance
unified_router = UnifiedRouter()

# Health and Status Endpoints
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Unified health check across all brokers"""
    try:
        broker_status = {}
        overall_healthy = True
        
        for broker_name, broker in unified_router.brokers.items():
            is_healthy = broker.is_connected
            broker_status[broker_name] = {
                "connected": is_healthy,
                "status": "healthy" if is_healthy else "unhealthy"
            }
            if not is_healthy:
                overall_healthy = False
        
        return HealthResponse(
            status="healthy" if overall_healthy else "degraded",
            timestamp=datetime.now(),
            brokers=broker_status,
            uptime=datetime.now().isoformat()  # Would track actual uptime
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@router.get("/status")
async def get_system_status(api_key: str = Depends(verify_api_key)):
    """Get detailed system status"""
    try:
        return {
            "system": "unified_trading_engine",
            "version": "2.0.0",
            "supported_brokers": unified_router.supported_brokers,
            "broker_connections": {
                name: broker.is_connected 
                for name, broker in unified_router.brokers.items()
            },
            "signal_processor": {
                "status": "active",
                "queue_size": signal_processor.signal_queue.qsize()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")

# Account Endpoints
@router.get("/accounts", response_model=List[Account])
async def get_all_accounts(
    broker: Optional[str] = Query(None, description="Filter by broker"),
    current_user: User = Depends(get_current_user)
):
    """Get all accounts from all brokers or specific broker"""
    try:
        if broker:
            broker_instance = await unified_router.get_broker_instance(broker)
            accounts = await broker_instance.get_accounts()
            for account in accounts:
                account.broker = broker
            return accounts
        else:
            return await unified_router.aggregate_broker_data("get_accounts")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get accounts")

@router.get("/accounts/{account_id}", response_model=Account)
async def get_account(
    account_id: str = Path(..., description="Account ID"),
    broker: str = Query(..., description="Broker name"),
    current_user: User = Depends(get_current_user)
):
    """Get specific account details"""
    try:
        broker_instance = await unified_router.get_broker_instance(broker)
        account = await broker_instance.get_account_info(account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account.broker = broker
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get account")

# Position Endpoints
@router.get("/positions", response_model=List[Position])
async def get_all_positions(
    broker: Optional[str] = Query(None, description="Filter by broker"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    current_user: User = Depends(get_current_user)
):
    """Get all positions from all brokers or specific broker"""
    try:
        if broker:
            broker_instance = await unified_router.get_broker_instance(broker)
            positions = await broker_instance.get_positions(account_id)
            for position in positions:
                position.broker = broker
            return positions
        else:
            return await unified_router.aggregate_broker_data("get_positions", account_id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get positions")

@router.get("/positions/{position_id}", response_model=Position)
async def get_position(
    position_id: str = Path(..., description="Position ID"),
    broker: str = Query(..., description="Broker name"),
    current_user: User = Depends(get_current_user)
):
    """Get specific position details"""
    try:
        # Get all positions and filter by ID
        broker_instance = await unified_router.get_broker_instance(broker)
        positions = await broker_instance.get_positions()
        
        position = next((p for p in positions if p.id == position_id), None)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        position.broker = broker
        return position
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position {position_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get position")

@router.delete("/positions/{position_id}")
async def close_position(
    position_id: str = Path(..., description="Position ID"),
    broker: str = Query(..., description="Broker name"),
    quantity: Optional[float] = Query(None, description="Quantity to close (optional)"),
    current_user: User = Depends(get_current_user)
):
    """Close position"""
    try:
        broker_instance = await unified_router.get_broker_instance(broker)
        result = await broker_instance.close_position(position_id, quantity)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position {position_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to close position")

# Order Endpoints
@router.post("/orders", response_model=OrderResponse)
async def place_order(
    order_request: OrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Place order across any broker"""
    try:
        broker_instance = await unified_router.get_broker_instance(order_request.broker)
        result = await broker_instance.place_order(order_request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail="Failed to place order")

@router.get("/orders", response_model=List[Order])
async def get_orders(
    broker: Optional[str] = Query(None, description="Filter by broker"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    current_user: User = Depends(get_current_user)
):
    """Get orders from all brokers or specific broker"""
    try:
        # TODO: Implement order retrieval in broker executors
        # This is a placeholder for now
        return []
        
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orders")

@router.put("/orders/{order_id}")
async def modify_order(
    order_id: str = Path(..., description="Order ID"),
    broker: str = Query(..., description="Broker name"),
    modifications: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user)
):
    """Modify existing order"""
    try:
        broker_instance = await unified_router.get_broker_instance(broker)
        result = await broker_instance.modify_order(order_id, modifications or {})
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error modifying order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to modify order")

@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str = Path(..., description="Order ID"),
    broker: str = Query(..., description="Broker name"),
    current_user: User = Depends(get_current_user)
):
    """Cancel order"""
    try:
        broker_instance = await unified_router.get_broker_instance(broker)
        result = await broker_instance.cancel_order(order_id)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")

# Signal Endpoints
@router.post("/signals", response_model=SignalResponse)
async def create_signal(
    signal_request: SignalRequest,
    current_user: User = Depends(get_current_user)
):
    """Create and execute trading signal"""
    try:
        result = await signal_processor.process_signal(signal_request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating signal: {e}")
        raise HTTPException(status_code=500, detail="Failed to create signal")

@router.get("/signals")
async def get_signals(
    limit: int = Query(100, description="Number of signals to return"),
    broker: Optional[str] = Query(None, description="Filter by broker"),
    current_user: User = Depends(get_current_user)
):
    """Get signal history"""
    try:
        signals = await signal_processor.get_signal_history(limit)
        
        if broker:
            signals = [s for s in signals if s.get("broker") == broker]
        
        return signals
        
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(status_code=500, detail="Failed to get signals")

# Trade Endpoints
@router.get("/trades", response_model=List[Trade])
async def get_trades(
    broker: Optional[str] = Query(None, description="Filter by broker"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    limit: int = Query(100, description="Number of trades to return"),
    current_user: User = Depends(get_current_user)
):
    """Get trade history"""
    try:
        # TODO: Implement trade retrieval in broker executors
        # This is a placeholder for now
        return []
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trades")

# Symbols and Instruments
@router.get("/symbols")
async def get_symbols(
    broker: Optional[str] = Query(None, description="Filter by broker"),
    current_user: User = Depends(get_current_user)
):
    """Get available symbols from all brokers or specific broker"""
    try:
        if broker:
            broker_instance = await unified_router.get_broker_instance(broker)
            symbols = await broker_instance.get_symbols()
            return {broker: symbols}
        else:
            all_symbols = {}
            for broker_name in unified_router.supported_brokers:
                try:
                    broker_instance = unified_router.brokers[broker_name]
                    if broker_instance.is_connected:
                        symbols = await broker_instance.get_symbols()
                        all_symbols[broker_name] = symbols
                except Exception as e:
                    logger.error(f"Error getting symbols from {broker_name}: {e}")
                    all_symbols[broker_name] = []
            
            return all_symbols
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail="Failed to get symbols")

# Broker-specific Endpoints
@router.get("/brokers")
async def get_brokers(current_user: User = Depends(get_current_user)):
    """Get list of supported brokers and their status"""
    try:
        broker_info = {}
        for broker_name, broker in unified_router.brokers.items():
            broker_info[broker_name] = {
                "connected": broker.is_connected,
                "type": broker_name,
                "supported": True
            }
        
        return broker_info
        
    except Exception as e:
        logger.error(f"Error getting broker info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get broker info")

@router.get("/brokers/{broker_name}/status")
async def get_broker_status(
    broker_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed status for specific broker"""
    try:
        broker_instance = await unified_router.get_broker_instance(broker_name)
        
        # Get basic status info
        status = {
            "broker": broker_name,
            "connected": broker_instance.is_connected,
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to get additional info
        try:
            accounts = await broker_instance.get_accounts()
            status["accounts_count"] = len(accounts)
            
            positions = await broker_instance.get_positions()
            status["open_positions"] = len(positions)
            
            symbols = await broker_instance.get_symbols()
            status["available_symbols"] = len(symbols)
            
        except Exception as e:
            logger.error(f"Error getting additional broker info: {e}")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting broker status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get broker status")