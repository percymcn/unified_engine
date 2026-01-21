from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.db.database import get_db
from app.models.models import Account, User
from app.models.schemas import Account as AccountSchema, AccountCreate, AccountUpdate
from app.routers.auth import get_current_user
from app.core.event_emitter import emit_account_event
from app.core.billing import require_broker_slot
from app.dependencies import get_container
from app.application.dto.account_dto import (
    GetAccountsRequest,
    CreateAccountRequest,
    UpdateAccountRequest,
    DeleteAccountRequest,
    ConnectAccountRequest,
    SyncAccountRequest,
    TestConnectionRequest,
)
from app.application.dto.account_settings_dto import (
    AccountSettingsRequest,
    GetAccountSettingsRequest,
    PositionSizingMode,
)
from app.domain.enums import BrokerType, AccountType
from pydantic import BaseModel, Field


class TestConnectionBody(BaseModel):
    """Request body for connection test endpoint"""
    broker: str
    credentials: dict


router = APIRouter()

@router.get("/")
async def get_accounts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """Get all accounts for current user via hexagonal architecture"""
    container = get_container(request)
    use_case = container.get_accounts_use_case()

    # Execute use case
    dto_request = GetAccountsRequest(
        user_id=current_user.id,
        broker=None,  # Get all brokers
        active_only=False,  # Include inactive accounts
    )
    response = await use_case.execute(dto_request)

    # Convert to API response format
    return {
        "accounts": [
            {
                "id": acc.id,
                "broker": acc.broker.value,
                "balance": float(acc.balance),
                "equity": float(acc.equity),
                "is_connected": acc.is_connected,
            }
            for acc in response.accounts
        ],
        "total": response.total,
    }

@router.post("/test-connection")
async def test_connection(
    request: Request,
    body: TestConnectionBody,
    current_user: User = Depends(get_current_user),
):
    """
    Test broker connection with provided credentials before saving.

    Tests authentication with the broker and returns detailed status.
    Does not save credentials or create an account.

    Returns:
        - success: Whether connection succeeded
        - status: "connected" | "failed" | "timeout"
        - message: Human-readable description
        - details: Optional broker-specific details
    """
    container = get_container(request)
    use_case = container.test_connection_use_case()

    # Validate broker type
    try:
        broker_type = BrokerType(body.broker.lower())
    except ValueError:
        valid_brokers = [b.value for b in BrokerType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker type: {body.broker}. Valid options: {valid_brokers}"
        )

    # Execute use case
    dto_request = TestConnectionRequest(
        broker=broker_type,
        credentials=body.credentials,
    )

    response = await use_case.execute(dto_request)

    result = {
        "success": response.success,
        "status": response.status,
        "message": response.message,
        "details": response.details,
    }

    # Include symbol detection info if available
    if response.detected_format:
        result["detected_format"] = response.detected_format
    if response.symbol_map:
        result["symbol_map"] = response.symbol_map
    if response.sample_symbols:
        result["sample_symbols"] = response.sample_symbols

    return result


@router.post("/")
async def create_account(
    request: Request,
    account: AccountCreate,
    current_user: User = Depends(require_broker_slot),
):
    """Create new trading account with encrypted credentials.

    Requires available broker slot - Free tier limited to 1 broker connection.
    Returns 403 if broker limit exceeded.
    """
    container = get_container(request)
    use_case = container.create_account_use_case()

    # Extract credentials from request
    credentials = {}
    if account.api_key:
        credentials["api_key"] = account.api_key
    if account.api_secret:
        credentials["api_secret"] = account.api_secret
    if account.login:
        credentials["login"] = account.login
    if account.password:
        credentials["password"] = account.password
    if account.server:
        credentials["server"] = account.server
    if account.broker_config:
        credentials.update(account.broker_config)

    # Execute use case
    dto_request = CreateAccountRequest(
        user_id=current_user.id,
        broker=account.broker,
        account_type=account.account_type,
        credentials=credentials,
        account_id=account.account_id,
        currency=account.currency,
        leverage=account.leverage,
        server=account.server,
        # Include symbol detection data if provided
        detected_format=account.detected_format,
        symbol_map=account.symbol_map,
        sample_symbols=account.sample_symbols,
    )

    response = await use_case.execute(dto_request)

    if response.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.error,
        )

    # Emit event
    await emit_account_event("created", response.account_id, {
        "broker": response.broker.value,
        "is_active": response.is_active,
    })

    result = {
        "id": response.account_id,
        "broker": response.broker.value,
        "is_active": response.is_active,
        "message": "Account created with encrypted credentials",
    }

    # Include auto-alias count if any were created
    if response.auto_aliases_created > 0:
        result["auto_aliases_created"] = response.auto_aliases_created
        result["message"] = f"Account created with {response.auto_aliases_created} auto-detected symbol aliases"

    return result


@router.get("/{account_id}")
async def get_account(
    request: Request,
    account_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get specific account via hexagonal architecture"""
    container = get_container(request)
    use_case = container.get_account_use_case()

    account = await use_case.execute(account_id)

    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return {
        "id": account.id,
        "user_id": account.user_id,
        "broker": account.broker.value,
        "account_type": account.account_type.value,
        "balance": float(account.balance),
        "equity": float(account.equity),
        "margin": float(account.margin),
        "free_margin": float(account.free_margin),
        "leverage": account.leverage,
        "currency": account.currency,
        "is_active": account.is_active,
        "is_connected": account.is_connected,
        "server": account.server,
        "last_sync": account.last_sync.isoformat() if account.last_sync else None,
    }

@router.put("/{account_id}")
async def update_account(
    request: Request,
    account_id: str,
    account_update: AccountUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update account with credential re-encryption"""
    container = get_container(request)
    use_case = container.update_account_use_case()

    # Extract credentials if provided
    credentials = None
    update_dict = account_update.dict(exclude_unset=True)

    if "api_key" in update_dict or "api_secret" in update_dict or "broker_config" in update_dict:
        credentials = {}
        if "api_key" in update_dict:
            credentials["api_key"] = update_dict["api_key"]
        if "api_secret" in update_dict:
            credentials["api_secret"] = update_dict["api_secret"]
        if "broker_config" in update_dict:
            credentials.update(update_dict["broker_config"])

    # Execute use case
    dto_request = UpdateAccountRequest(
        account_id=account_id,
        credentials=credentials,
        leverage=update_dict.get("leverage"),
        is_active=update_dict.get("is_active"),
    )

    response = await use_case.execute(dto_request)

    if response.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.error,
        )

    return {
        "id": response.account_id,
        "updated": response.updated,
        "message": "Account updated successfully",
    }

@router.delete("/{account_id}")
async def delete_account(
    request: Request,
    account_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete account and soft-delete its credentials"""
    container = get_container(request)
    use_case = container.delete_account_use_case()

    # Execute use case
    dto_request = DeleteAccountRequest(
        account_id=account_id,
        user_id=current_user.id,
    )

    response = await use_case.execute(dto_request)

    if response.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.error,
        )

    return {
        "id": response.account_id,
        "deleted": response.deleted,
        "message": "Account and credentials deleted successfully",
    }

@router.post("/{account_id}/sync")
async def sync_account(
    request: Request,
    account_id: str,
    current_user: User = Depends(get_current_user),
):
    """Sync account data from broker via hexagonal architecture"""
    container = get_container(request)
    use_case = container.sync_account_use_case()

    # Execute use case
    dto_request = SyncAccountRequest(account_id=account_id)

    try:
        response = await use_case.execute(dto_request)

        return {
            "account_id": response.account_id,
            "balance": float(response.balance),
            "equity": float(response.equity),
            "margin": float(response.margin),
            "free_margin": float(response.free_margin),
            "synced_at": response.synced_at.isoformat(),
            "positions_count": response.positions_count,
            "orders_count": response.orders_count,
            "message": "Account synced successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.get("/{account_id}/balance")
async def get_account_balance(
    request: Request,
    account_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get account balance via hexagonal architecture"""
    container = get_container(request)
    use_case = container.get_account_use_case()

    account = await use_case.execute(account_id)

    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return {
        "account_id": account.id,
        "balance": float(account.balance),
        "equity": float(account.equity),
        "margin": float(account.margin),
        "free_margin": float(account.free_margin),
        "last_sync": account.last_sync.isoformat() if account.last_sync else None,
    }


# Pydantic models for account settings API
class AccountSettingsBody(BaseModel):
    """Request body for updating account settings"""
    # Position sizing
    position_sizing_mode: Optional[str] = Field(None, description="fixed, percent_balance, percent_equity, risk_based")
    fixed_lot_size: Optional[float] = Field(None, ge=0.01, le=100)
    percent_of_balance: Optional[float] = Field(None, ge=0.1, le=100)
    percent_of_equity: Optional[float] = Field(None, ge=0.1, le=100)
    risk_percent_per_trade: Optional[float] = Field(None, ge=0.1, le=10)

    # Risk limits
    max_position_size: Optional[float] = Field(None, ge=0.01)
    max_daily_loss: Optional[float] = Field(None, ge=0)
    max_daily_loss_pct: Optional[float] = Field(None, ge=0, le=100)
    max_drawdown_pct: Optional[float] = Field(None, ge=0, le=100)
    max_open_positions: Optional[int] = Field(None, ge=1, le=100)
    max_daily_trades: Optional[int] = Field(None, ge=1, le=1000)
    trade_cooldown_seconds: Optional[int] = Field(None, ge=0, le=3600)

    # Grouping
    group_id: Optional[int] = None

    # Routing
    is_signal_enabled: Optional[bool] = None
    signal_priority: Optional[int] = Field(None, ge=0, le=100)


@router.get("/{account_id}/settings")
async def get_account_settings(
    request: Request,
    account_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Get current account settings (position sizing, risk limits, routing).

    Returns all configured settings for the specified account.
    """
    container = get_container(request)
    use_case = container.get_account_settings_use_case()

    dto_request = GetAccountSettingsRequest(
        account_id=account_id,
        user_id=current_user.id,
    )

    try:
        response = await use_case.execute(dto_request)
        return {
            "account_id": response.account_id,
            "position_sizing": {
                "mode": response.position_sizing_mode,
                "fixed_lot_size": response.fixed_lot_size,
                "percent_of_balance": response.percent_of_balance,
                "percent_of_equity": response.percent_of_equity,
                "risk_percent_per_trade": response.risk_percent_per_trade,
            },
            "risk_limits": {
                "max_position_size": response.max_position_size,
                "max_daily_loss": response.max_daily_loss,
                "max_daily_loss_pct": response.max_daily_loss_pct,
                "max_drawdown_pct": response.max_drawdown_pct,
                "max_open_positions": response.max_open_positions,
                "max_daily_trades": response.max_daily_trades,
                "trade_cooldown_seconds": response.trade_cooldown_seconds,
            },
            "grouping": {
                "group_id": response.group_id,
                "group_name": response.group_name,
                "group_color": response.group_color,
            },
            "routing": {
                "is_signal_enabled": response.is_signal_enabled,
                "signal_priority": response.signal_priority,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{account_id}/settings")
async def update_account_settings(
    request: Request,
    account_id: int,
    settings: AccountSettingsBody,
    current_user: User = Depends(get_current_user),
):
    """
    Update account settings (position sizing, risk limits, routing).

    Only provided fields will be updated. Omit fields to keep current values.
    """
    container = get_container(request)
    use_case = container.update_account_settings_use_case()

    # Convert string mode to enum if provided
    position_sizing_mode = None
    if settings.position_sizing_mode:
        try:
            position_sizing_mode = PositionSizingMode(settings.position_sizing_mode)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid position_sizing_mode: {settings.position_sizing_mode}. "
                       f"Valid options: fixed, percent_balance, percent_equity, risk_based"
            )

    dto_request = AccountSettingsRequest(
        account_id=account_id,
        position_sizing_mode=position_sizing_mode,
        fixed_lot_size=settings.fixed_lot_size,
        percent_of_balance=settings.percent_of_balance,
        percent_of_equity=settings.percent_of_equity,
        risk_percent_per_trade=settings.risk_percent_per_trade,
        max_position_size=settings.max_position_size,
        max_daily_loss=settings.max_daily_loss,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_drawdown_pct=settings.max_drawdown_pct,
        max_open_positions=settings.max_open_positions,
        max_daily_trades=settings.max_daily_trades,
        trade_cooldown_seconds=settings.trade_cooldown_seconds,
        group_id=settings.group_id,
        is_signal_enabled=settings.is_signal_enabled,
        signal_priority=settings.signal_priority,
    )

    try:
        response = await use_case.execute(dto_request, user_id=current_user.id)
        return {
            "message": "Settings updated successfully",
            "account_id": response.account_id,
            "position_sizing": {
                "mode": response.position_sizing_mode,
                "fixed_lot_size": response.fixed_lot_size,
                "percent_of_balance": response.percent_of_balance,
                "percent_of_equity": response.percent_of_equity,
                "risk_percent_per_trade": response.risk_percent_per_trade,
            },
            "risk_limits": {
                "max_position_size": response.max_position_size,
                "max_daily_loss": response.max_daily_loss,
                "max_daily_loss_pct": response.max_daily_loss_pct,
                "max_drawdown_pct": response.max_drawdown_pct,
                "max_open_positions": response.max_open_positions,
                "max_daily_trades": response.max_daily_trades,
                "trade_cooldown_seconds": response.trade_cooldown_seconds,
            },
            "grouping": {
                "group_id": response.group_id,
                "group_name": response.group_name,
                "group_color": response.group_color,
            },
            "routing": {
                "is_signal_enabled": response.is_signal_enabled,
                "signal_priority": response.signal_priority,
            },
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )