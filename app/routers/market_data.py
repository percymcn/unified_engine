"""
Market Data Router

Provides API endpoints for market data, charts, and technical indicators
for the ProjectX/TopStep integration.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.services.projectx_sdk_service import ProjectXSDKService, SDK_AVAILABLE
from app.services.contract_resolver import get_contract_resolver
from app.routers.auth import get_current_user
from app.models.pydantic_schemas import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/market", tags=["market-data"])


# =============================================================================
# Response Models
# =============================================================================

class BarData(BaseModel):
    """OHLCV bar data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartDataResponse(BaseModel):
    """Chart data with optional indicators."""
    symbol: str
    interval: str
    bars: List[Dict[str, Any]]
    indicators: Optional[Dict[str, Any]] = None
    contract_info: Optional[Dict[str, Any]] = None


class SymbolInfo(BaseModel):
    """Tradeable symbol information."""
    symbol: str
    name: str
    tick_size: float
    tick_value: float
    contract_id: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True


class QuoteData(BaseModel):
    """Real-time quote data."""
    symbol: str
    bid: float
    ask: float
    last: Optional[float] = None
    volume: Optional[int] = None
    timestamp: datetime


class ContractInfoResponse(BaseModel):
    """Contract details including expiry."""
    contract_id: str
    symbol: str
    base_symbol: str
    description: str
    tick_size: float
    tick_value: float
    is_active: bool
    expiry_month: str
    expiry_year: int


# =============================================================================
# Helper Functions
# =============================================================================

async def get_sdk_service(account_id: str, user: User) -> ProjectXSDKService:
    """Get SDK service for a user's account."""
    # In production, fetch credentials from database
    # For now, we'll need the account to have stored credentials
    from app.infrastructure.repositories.account_repository import AccountRepository
    from app.core.database import get_db

    # Get database session
    db = next(get_db())
    try:
        repo = AccountRepository(db)
        account = await repo.get_by_id(account_id)

        if not account or account.user_id != user.id:
            raise HTTPException(status_code=404, detail="Account not found")

        if account.broker != "projectx":
            raise HTTPException(status_code=400, detail="Account is not a ProjectX account")

        # Get credentials from account
        username = account.login or account.api_key
        api_key = account.password or account.api_secret

        if not username or not api_key:
            raise HTTPException(status_code=400, detail="Account credentials not configured")

        return ProjectXSDKService(
            username=username,
            api_key=api_key,
            account_name=account.account_id
        )
    finally:
        db.close()


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/symbols", response_model=List[SymbolInfo])
async def get_tradeable_symbols():
    """
    Get all tradeable symbols on ProjectX/TopStep.

    Returns list of symbols with tick size, tick value, and name.
    No authentication required - public reference data.
    """
    resolver = get_contract_resolver()
    symbols = []

    for symbol, info in resolver.TRADEABLE_SYMBOLS.items():
        symbols.append(SymbolInfo(
            symbol=symbol,
            name=info['name'],
            tick_size=info['tick_size'],
            tick_value=info['tick_value'],
        ))

    return symbols


@router.get("/contract/{symbol}", response_model=ContractInfoResponse)
async def get_contract_info(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get active contract info for a symbol.

    Resolves base symbol to current front-month contract.
    Handles automatic rollover detection.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    # For contract info, we need to connect to the API
    # This is a simplified version - in production you'd use user's credentials
    raise HTTPException(
        status_code=501,
        detail="Contract resolution requires account connection. Use /chart endpoint with account_id."
    )


@router.get("/chart/{symbol}")
async def get_chart_data(
    symbol: str,
    account_id: str = Query(..., description="Account ID to use for data"),
    interval: int = Query(5, description="Bar interval in minutes (1, 5, 15, 30, 60)"),
    days: int = Query(1, description="Days of historical data (1-30)"),
    include_indicators: bool = Query(True, description="Include technical indicators"),
    current_user: User = Depends(get_current_user)
) -> ChartDataResponse:
    """
    Get chart data with OHLCV bars and optional technical indicators.

    Supports multiple timeframes and automatic contract resolution.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    # Validate parameters
    if interval not in [1, 5, 15, 30, 60]:
        raise HTTPException(status_code=400, detail="Invalid interval. Use 1, 5, 15, 30, or 60")
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 30")

    try:
        svc = await get_sdk_service(account_id, current_user)
        connected = await svc.connect()

        if not connected:
            raise HTTPException(status_code=503, detail="Failed to connect to ProjectX")

        try:
            # Get market data
            bars = await svc.get_market_data(symbol, days=days, interval=interval)

            # Get contract info
            contract_info = await svc.get_contract_info(symbol)

            # Get indicators if requested
            indicators = None
            if include_indicators and len(bars) >= 14:
                indicators = await svc.calculate_technical_indicators(
                    symbol, days=days, interval=interval
                )

            return ChartDataResponse(
                symbol=symbol,
                interval=f"{interval}m",
                bars=bars,
                indicators=indicators,
                contract_info=contract_info,
            )

        finally:
            await svc.disconnect()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    account_id: str = Query(..., description="Account ID to use"),
    current_user: User = Depends(get_current_user)
) -> QuoteData:
    """
    Get real-time quote for a symbol.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    try:
        svc = await get_sdk_service(account_id, current_user)
        connected = await svc.connect()

        if not connected:
            raise HTTPException(status_code=503, detail="Failed to connect to ProjectX")

        try:
            # Get latest bar for quote data
            bars = await svc.get_market_data(symbol, days=1, interval=1)

            if not bars:
                raise HTTPException(status_code=404, detail="No quote data available")

            latest = bars[-1]
            return QuoteData(
                symbol=symbol,
                bid=latest.get('close', 0),
                ask=latest.get('close', 0),
                last=latest.get('close', 0),
                volume=latest.get('volume', 0),
                timestamp=datetime.now(),
            )

        finally:
            await svc.disconnect()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{symbol}")
async def get_indicators(
    symbol: str,
    account_id: str = Query(..., description="Account ID to use"),
    days: int = Query(5, description="Days of data for calculation"),
    interval: int = Query(5, description="Bar interval in minutes"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get technical indicators for a symbol.

    Returns: RSI, MACD, Bollinger Bands, ATR, EMA, SMA, Stochastic, ADX, CCI, Williams %R
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    try:
        svc = await get_sdk_service(account_id, current_user)
        connected = await svc.connect()

        if not connected:
            raise HTTPException(status_code=503, detail="Failed to connect to ProjectX")

        try:
            indicators = await svc.calculate_technical_indicators(
                symbol, days=days, interval=interval
            )

            return {
                "symbol": symbol,
                "interval": f"{interval}m",
                "indicators": indicators,
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            await svc.disconnect()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-contracts")
async def refresh_contracts(
    account_id: str = Query(..., description="Account ID to use"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Force refresh of contract mappings (for rollover).

    Call this when contracts roll to new month.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    try:
        svc = await get_sdk_service(account_id, current_user)
        connected = await svc.connect()

        if not connected:
            raise HTTPException(status_code=503, detail="Failed to connect to ProjectX")

        try:
            count = await svc.check_and_refresh_contracts()

            return {
                "success": True,
                "contracts_refreshed": count,
                "message": f"Refreshed {count} contract mappings",
            }

        finally:
            await svc.disconnect()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing contracts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
