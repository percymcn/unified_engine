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
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.projectx_sdk_service import ProjectXSDKService, SDK_AVAILABLE
from app.services.contract_resolver import get_contract_resolver
from app.routers.auth import get_current_user
from app.models.schemas import User
from app.db.database import get_async_session
from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository as AccountRepository
from app.infrastructure.repositories.credential_repository import CredentialRepository
from app.domain.value_objects import AccountId

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

async def get_sdk_service(
    account_id: str,
    user: User,
    session: AsyncSession
) -> ProjectXSDKService:
    """
    Get SDK service for a user's account.

    Fetches credentials from database - NOT from environment variables.
    """
    # Use async session for repository
    account_repo = AccountRepository(session)
    cred_repo = CredentialRepository(session)

    # Get account from database
    account = await account_repo.get_by_id(AccountId(account_id))

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != user.id:
        raise HTTPException(status_code=403, detail="Account does not belong to user")

    # Check broker type - support both projectx and topstep
    broker_str = str(account.broker.value) if hasattr(account.broker, 'value') else str(account.broker)
    if broker_str not in ("projectx", "topstep"):
        raise HTTPException(status_code=400, detail="Account is not a ProjectX/TopStep account")

    # Try to get credentials from credential repository first
    username = None
    api_key = None
    account_name = None

    # Check if account has credential_id reference
    if hasattr(account, 'credential_id') and account.credential_id:
        cred_data = await cred_repo.get_decrypted_data(account.credential_id)
        if cred_data:
            username = cred_data.get('username')
            api_key = cred_data.get('api_key')
            account_name = cred_data.get('account_name') or cred_data.get('account_id')

    # Fallback: Look up credentials by user_id and service (broker type)
    if not username or not api_key:
        cred_data = await cred_repo.get_by_user_and_service(user.id, broker_str.lower())
        if cred_data:
            username = cred_data.get('username')
            api_key = cred_data.get('api_key')
            account_name = cred_data.get('account_name') or cred_data.get('account_id')

    # Fallback to account fields if credentials not in credential repo
    if not username or not api_key:
        # Check broker_config for credentials
        broker_config = getattr(account, 'broker_config', None) or {}
        if isinstance(broker_config, dict):
            username = username or broker_config.get('username')
            api_key = api_key or broker_config.get('api_key') or broker_config.get('password')
            account_name = account_name or broker_config.get('account_name') or broker_config.get('account_id')

        # Last fallback to direct account fields
        if not username:
            username = getattr(account, 'login', None) or getattr(account, 'api_key', None)
        if not api_key:
            api_key = getattr(account, 'password', None) or getattr(account, 'api_secret', None)

    # Get account name/ID for SDK
    if not account_name:
        account_name = getattr(account, 'account_number', None) or account_id

    if not username or not api_key:
        raise HTTPException(
            status_code=400,
            detail="Account credentials not configured. Please update your account with valid ProjectX credentials."
        )

    logger.info(f"Creating SDK service for account {account_name} (user: {user.id})")

    return ProjectXSDKService(
        username=username,
        api_key=api_key,
        account_name=account_name
    )


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


@router.post("/symbols/refresh")
async def refresh_symbols_from_sdk(
    account_id: str = Query(..., description="Account ID to use for SDK connection"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Refresh symbol cache by fetching all available instruments from ProjectX SDK.

    Searches for all tradeable base symbols and caches their active contracts.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    from app.cache.redis_client import redis_client
    import json

    try:
        svc = await get_sdk_service(account_id, current_user, session)
        connected = await svc.connect()

        if not connected:
            raise HTTPException(status_code=503, detail="Failed to connect to ProjectX")

        try:
            resolver = get_contract_resolver()
            all_instruments = []
            base_symbols = list(resolver.TRADEABLE_SYMBOLS.keys())

            # Search for each base symbol
            for base_symbol in base_symbols:
                try:
                    instruments = await svc.search_instruments(base_symbol)
                    for inst in instruments:
                        inst['base_symbol'] = base_symbol
                        inst['tick_size'] = resolver.TRADEABLE_SYMBOLS[base_symbol]['tick_size']
                        inst['tick_value'] = resolver.TRADEABLE_SYMBOLS[base_symbol]['tick_value']
                    all_instruments.extend(instruments)
                except Exception as e:
                    logger.warning(f"Failed to fetch instruments for {base_symbol}: {e}")

            # Cache the results in Redis
            await redis_client.set(
                "projectx:instruments",
                json.dumps(all_instruments),
                expire=3600 * 6  # 6 hours cache
            )

            # Also cache by symbol for quick lookup
            for inst in all_instruments:
                symbol = inst.get('symbol', inst.get('base_symbol', ''))
                if symbol:
                    await redis_client.set(
                        f"projectx:instrument:{symbol}",
                        json.dumps(inst),
                        expire=3600 * 6
                    )

            return {
                "success": True,
                "instruments_found": len(all_instruments),
                "base_symbols_searched": len(base_symbols),
                "cached_until": "6 hours",
                "instruments": all_instruments[:20]  # Return first 20 as sample
            }

        finally:
            await svc.disconnect()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols/cached")
async def get_cached_symbols() -> Dict[str, Any]:
    """
    Get cached symbols from Redis (fetched via SDK).

    Returns all instruments that were previously fetched from ProjectX.
    """
    from app.cache.redis_client import redis_client
    import json

    try:
        cached = await redis_client.get("projectx:instruments")
        if cached:
            instruments = json.loads(cached)
            return {
                "success": True,
                "cached": True,
                "count": len(instruments),
                "instruments": instruments
            }
        else:
            # Return static symbols as fallback
            resolver = get_contract_resolver()
            symbols = [
                {"symbol": sym, "name": info['name'], "tick_size": info['tick_size'], "tick_value": info['tick_value']}
                for sym, info in resolver.TRADEABLE_SYMBOLS.items()
            ]
            return {
                "success": True,
                "cached": False,
                "count": len(symbols),
                "instruments": symbols,
                "message": "No cached data - returning static symbols. Call POST /symbols/refresh to fetch from SDK."
            }
    except Exception as e:
        logger.error(f"Error getting cached symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
) -> ChartDataResponse:
    """
    Get chart data with OHLCV bars and optional technical indicators.

    Supports multiple timeframes and automatic contract resolution.
    Credentials are fetched from database, not environment.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    # Validate parameters
    if interval not in [1, 5, 15, 30, 60]:
        raise HTTPException(status_code=400, detail="Invalid interval. Use 1, 5, 15, 30, or 60")
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 30")

    try:
        svc = await get_sdk_service(account_id, current_user, session)
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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
) -> QuoteData:
    """
    Get real-time quote for a symbol.
    Credentials are fetched from database, not environment.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    try:
        svc = await get_sdk_service(account_id, current_user, session)
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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Get technical indicators for a symbol.

    Returns: RSI, MACD, Bollinger Bands, ATR, EMA, SMA, Stochastic, ADX, CCI, Williams %R
    Credentials are fetched from database, not environment.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    try:
        svc = await get_sdk_service(account_id, current_user, session)
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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Force refresh of contract mappings (for rollover).

    Call this when contracts roll to new month.
    Credentials are fetched from database, not environment.
    """
    if not SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="SDK not available")

    try:
        svc = await get_sdk_service(account_id, current_user, session)
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
