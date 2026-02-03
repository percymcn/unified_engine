"""
Contracts Router

API endpoints for futures contract management and expiration tracking.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.routers.auth import get_current_user
from app.db.database import get_db
from app.domain.services.contract_tracker import ContractTracker, ExpiringPosition
from app.domain.services.futures_contract_service import FuturesContractService
from app.models.models import FuturesContract as FuturesContractModel
from app.models.models import User, UserContractPosition
from app.services.contract_resolver import ContractResolver, get_contract_resolver

logger = logging.getLogger(__name__)

router = APIRouter()


# Response models
class ContractResponse(BaseModel):
    """Response model for a futures contract."""
    id: int
    symbol_root: str
    contract_code: str
    month_code: str
    year: int
    expiration_date: str
    last_trading_day: str
    rollover_date: str
    is_active: bool
    next_contract: Optional[str] = None

    class Config:
        from_attributes = True


class ExpiringContractResponse(BaseModel):
    """Response model for an expiring contract with user context."""
    contract_code: str
    symbol_root: str
    expiration_date: str
    rollover_date: str
    next_contract: Optional[str] = None
    days_until_expiration: int
    days_until_rollover: int
    account_id: int


class ParsedContractResponse(BaseModel):
    """Response model for parsed contract code."""
    root: str
    month_code: str
    month: int
    year: int
    full_year: int


class ContractBuildResponse(BaseModel):
    """Response model for building contract from code."""
    symbol_root: str
    contract_code: str
    month_code: str
    year: int
    expiration_date: str
    last_trading_day: str
    rollover_date: str
    next_contract: Optional[str] = None


@router.get("/expiring", response_model=List[ExpiringContractResponse])
async def get_expiring_contracts(
    days: int = Query(7, ge=1, le=30, description="Days to look ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get contracts expiring within N days for the current user.

    Returns contracts the user is trading that will expire soon,
    with rollover suggestions.
    """
    try:
        tracker = ContractTracker(db)
        expiring = await tracker.get_expiring_positions(current_user.id, days)

        return [
            ExpiringContractResponse(
                contract_code=pos.contract_code,
                symbol_root=pos.symbol_root,
                expiration_date=pos.expiration_date.isoformat(),
                rollover_date=pos.rollover_date.isoformat(),
                next_contract=pos.next_contract,
                days_until_expiration=pos.days_until_expiration,
                days_until_rollover=pos.days_until_rollover,
                account_id=pos.account_id
            )
            for pos in expiring
        ]

    except Exception as e:
        logger.error(f"Error getting expiring contracts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get expiring contracts")


@router.get("/all-expiring", response_model=List[ContractResponse])
async def get_all_expiring_contracts(
    days: int = Query(7, ge=1, le=30, description="Days to look ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all contracts expiring within N days (global view).

    Returns all tracked contracts that will expire soon, regardless
    of whether the user is trading them.
    """
    try:
        tracker = ContractTracker(db)
        contracts = await tracker.get_all_expiring_contracts(days)

        return [
            ContractResponse(
                id=c.id,
                symbol_root=c.symbol_root,
                contract_code=c.contract_code,
                month_code=c.month_code,
                year=c.year,
                expiration_date=c.expiration_date.date().isoformat() if hasattr(c.expiration_date, 'date') else str(c.expiration_date),
                last_trading_day=c.last_trading_day.date().isoformat() if hasattr(c.last_trading_day, 'date') else str(c.last_trading_day),
                rollover_date=c.rollover_date.date().isoformat() if hasattr(c.rollover_date, 'date') else str(c.rollover_date),
                is_active=c.is_active,
                next_contract=c.next_contract
            )
            for c in contracts
        ]

    except Exception as e:
        logger.error(f"Error getting all expiring contracts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get expiring contracts")


@router.get("/parse/{code}", response_model=ParsedContractResponse)
async def parse_contract_code(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """
    Parse a futures contract code into components.

    Examples:
    - NQH25 -> {root: "NQ", month_code: "H", month: 3, year: 25, full_year: 2025}
    - ESM2025 -> {root: "ES", month_code: "M", month: 6, year: 25, full_year: 2025}
    """
    service = FuturesContractService()
    parsed = service.parse_contract_code(code)

    if not parsed:
        raise HTTPException(status_code=400, detail=f"Invalid contract code: {code}")

    return ParsedContractResponse(
        root=parsed.root,
        month_code=parsed.month_code,
        month=parsed.month,
        year=parsed.year,
        full_year=parsed.full_year
    )


@router.get("/build/{code}", response_model=ContractBuildResponse)
async def build_contract_info(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """
    Build full contract information from a contract code.

    Calculates expiration date, rollover date, and next contract.
    """
    service = FuturesContractService()
    contract = service.build_contract(code)

    if not contract:
        raise HTTPException(status_code=400, detail=f"Invalid contract code: {code}")

    return ContractBuildResponse(
        symbol_root=contract.symbol_root,
        contract_code=contract.contract_code,
        month_code=contract.month_code,
        year=contract.year,
        expiration_date=contract.expiration_date.isoformat(),
        last_trading_day=contract.last_trading_day.isoformat(),
        rollover_date=contract.rollover_date.isoformat(),
        next_contract=contract.next_contract
    )


@router.post("/track/{code}")
async def track_contract_position(
    code: str,
    account_id: int = Query(..., description="Account ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Track a futures contract position for the user.

    Call this when the user trades a futures contract to enable
    expiration notifications.
    """
    try:
        tracker = ContractTracker(db)
        position = await tracker.update_position(
            user_id=current_user.id,
            account_id=account_id,
            contract_code=code
        )

        if not position:
            raise HTTPException(status_code=400, detail=f"Failed to track contract: {code}")

        return {
            "message": f"Now tracking {code} for account {account_id}",
            "contract_code": code,
            "account_id": account_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking contract: {e}")
        raise HTTPException(status_code=500, detail="Failed to track contract")


@router.delete("/track/{code}")
async def untrack_contract_position(
    code: str,
    account_id: int = Query(..., description="Account ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stop tracking a futures contract position.
    """
    try:
        position = db.query(UserContractPosition).filter(
            UserContractPosition.user_id == current_user.id,
            UserContractPosition.account_id == account_id,
            UserContractPosition.contract_code == code.upper()
        ).first()

        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        db.delete(position)
        db.commit()

        return {"message": f"Stopped tracking {code} for account {account_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error untracking contract: {e}")
        raise HTTPException(status_code=500, detail="Failed to untrack contract")


@router.get("/next/{code}")
async def get_next_contract(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the next contract code in sequence.

    For quarterly contracts (ES, NQ, YM, RTY), returns next quarterly (H->M->U->Z).
    For monthly contracts (CL, GC), returns next month.
    """
    service = FuturesContractService()
    next_code = service.get_next_contract_code(code)

    if not next_code:
        raise HTTPException(status_code=400, detail=f"Could not determine next contract for: {code}")

    # Build full info for next contract
    next_contract = service.build_contract(next_code)

    return {
        "current_contract": code.upper(),
        "next_contract": next_code,
        "next_expiration_date": next_contract.expiration_date.isoformat() if next_contract else None,
        "next_rollover_date": next_contract.rollover_date.isoformat() if next_contract else None
    }


# ==============================================================================
# ProjectX Contract Sync Endpoints
# ==============================================================================

class ProjectXContractResponse(BaseModel):
    """Response model for a ProjectX contract from cache."""
    base_symbol: str
    contract_id: str
    symbol: str
    description: str
    tick_size: float
    tick_value: float
    is_active: bool
    expiry_month: str
    expiry_year: int


@router.get("/projectx/cached")
async def get_projectx_cached_contracts(
    current_user: User = Depends(get_current_user)
):
    """
    Get all cached ProjectX contracts.

    Returns the currently cached contracts from the ContractResolver.
    These are auto-synced from ProjectX and used for symbol mapping.
    """
    resolver = get_contract_resolver()
    cached = resolver.get_cached_contracts()

    return {
        "count": len(cached),
        "contracts": [
            {
                "base_symbol": c.base_symbol,
                "contract_id": c.contract_id,
                "symbol": c.symbol,
                "description": c.description,
                "tick_size": c.tick_size,
                "tick_value": c.tick_value,
                "is_active": c.is_active,
                "expiry_month": c.expiry_month,
                "expiry_year": c.expiry_year,
                "last_updated": c.last_updated.isoformat(),
            }
            for c in cached.values()
        ],
        "tradeable_symbols": resolver.get_all_tradeable_symbols(),
    }


@router.post("/projectx/sync")
async def sync_projectx_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger ProjectX contract sync.

    Fetches the latest active contracts from ProjectX API and updates the cache.
    This handles rollover automatically by getting the current front-month contract.

    Requires valid ProjectX credentials in the Credential table for the user.
    """
    from app.services.signal_processor import _load_account_credentials
    from app.models.database_models import TradingAccount

    # Find user's ProjectX account to get credentials
    account = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.broker.in_(["PROJECTX", "projectx"])
    ).first()

    if not account:
        raise HTTPException(
            status_code=404,
            detail="No ProjectX account found. Add a ProjectX account first."
        )

    # Load credentials
    credentials = _load_account_credentials(db, account)
    username = credentials.get("username")
    api_key = credentials.get("api_key")

    if not username or not api_key:
        raise HTTPException(
            status_code=400,
            detail="ProjectX credentials not configured. Add username and API key in account settings."
        )

    # Sync contracts
    resolver = get_contract_resolver()
    try:
        count = await resolver.sync_contracts_from_projectx(username, api_key)
        return {
            "message": f"Synced {count} contracts from ProjectX",
            "count": count,
            "contracts": [
                {"base_symbol": c.base_symbol, "symbol": c.symbol, "contract_id": c.contract_id}
                for c in resolver.get_cached_contracts().values()
            ]
        }
    except Exception as e:
        logger.error(f"Error syncing ProjectX contracts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync contracts: {str(e)}")


@router.get("/projectx/resolve/{symbol}")
async def resolve_projectx_symbol(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Resolve a TradingView symbol to ProjectX contract.

    Examples:
    - ES1! -> ES (base) -> ESM6 (active contract)
    - SPX500USD -> MES (base) -> MESM6 (active contract)
    - XAUUSD -> MGC (base) -> MGCM6 (active contract)
    """
    resolver = get_contract_resolver()

    # Normalize to base symbol
    base_symbol = ContractResolver.normalize_symbol(symbol)

    # Check cache for active contract
    contract = resolver._cache.get(base_symbol.upper())

    return {
        "input_symbol": symbol,
        "base_symbol": base_symbol,
        "is_mapped": base_symbol != symbol.upper(),
        "cached_contract": {
            "contract_id": contract.contract_id,
            "symbol": contract.symbol,
            "description": contract.description,
            "is_active": contract.is_active,
            "expiry_month": contract.expiry_month,
            "expiry_year": contract.expiry_year,
        } if contract else None,
        "tradeable": base_symbol in resolver.TRADEABLE_SYMBOLS,
    }


@router.get("/projectx/mappings")
async def get_projectx_symbol_mappings(
    current_user: User = Depends(get_current_user)
):
    """
    Get all TradingView to ProjectX symbol mappings.

    Returns the full mapping table used to convert TradingView symbols
    (like ES1!, SPX500USD, XAUUSD) to ProjectX base symbols.
    """
    return {
        "mappings": ContractResolver.TRADINGVIEW_SYMBOL_MAP,
        "tradeable_symbols": ContractResolver.TRADEABLE_SYMBOLS,
    }
