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
from datetime import datetime


class TestConnectionBody(BaseModel):
    """Request body for connection test endpoint"""
    broker: str
    credentials: dict


class SelectAccountBody(BaseModel):
    """Request body for account selection toggle"""
    selected: bool


class FetchAvailableAccountsBody(BaseModel):
    """Optional request body for fetching available accounts"""
    credentials: Optional[dict] = None  # Override stored credentials


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


@router.get("/available/{broker_type}")
async def get_available_accounts(
    request: Request,
    broker_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch available accounts from broker SDK.

    Returns list of accounts available on the broker, with selection status
    cross-referenced against stored TradingAccounts.

    Args:
        broker_type: Broker type (tradelocker, projectx, tradovate, mt4, mt5)

    Returns:
        List of available accounts with:
        - id: Broker's account ID
        - name: Account name
        - account_type: live, demo, evaluation, express
        - balance: Account balance (if available)
        - currency: Account currency
        - is_stored: Whether account exists in database
        - is_selected: Whether account is selected to receive signals (is_signal_enabled)
        - stored_account_id: Database account ID (if stored)
    """
    from app.services.account_fetcher_service import AccountFetcherService
    from app.models.database_models import TradingAccount, BrokerType as DBBrokerType
    from app.core.encryption import decrypt

    # Validate broker type
    try:
        broker_enum = BrokerType(broker_type.lower())
    except ValueError:
        valid_brokers = [b.value for b in BrokerType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker type: {broker_type}. Valid options: {valid_brokers}"
        )

    # Get stored accounts for this broker to extract credentials
    stored_accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.broker == DBBrokerType(broker_type.lower()),
        TradingAccount.is_active == True
    ).all()

    if not stored_accounts:
        return {
            "broker_type": broker_type,
            "accounts": [],
            "message": "No stored accounts for this broker. Connect an account first."
        }

    # Use first stored account's credentials to fetch available accounts
    account = stored_accounts[0]
    credentials = {}

    # Build credentials from stored account
    if account.api_key:
        try:
            credentials["api_key"] = decrypt(account.api_key)
        except Exception:
            credentials["api_key"] = account.api_key
    if account.api_secret:
        try:
            credentials["api_secret"] = decrypt(account.api_secret)
        except Exception:
            credentials["api_secret"] = account.api_secret
    if account.access_token:
        try:
            credentials["access_token"] = decrypt(account.access_token)
        except Exception:
            credentials["access_token"] = account.access_token
    if account.oauth_environment:
        credentials["environment"] = account.oauth_environment

    # Add any extra metadata credentials
    if account.extra_metadata:
        for key in ["username", "email", "password", "server", "token", "account_id", "metaapi_account_id"]:
            if key in account.extra_metadata:
                credentials[key] = account.extra_metadata[key]

    # Fetch available accounts from broker
    fetcher = AccountFetcherService()
    try:
        broker_accounts = await fetcher.fetch_all_accounts(
            user_id=current_user.id,
            broker_type=broker_type,
            credentials=credentials
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch accounts from broker: {str(e)}"
        )

    # Build lookup of stored accounts by account_number (external ID)
    stored_lookup = {acc.account_number: acc for acc in stored_accounts}

    # Combine broker accounts with stored info
    result_accounts = []
    for broker_acc in broker_accounts:
        stored = stored_lookup.get(broker_acc.id) or stored_lookup.get(str(broker_acc.id))

        result_accounts.append({
            "id": broker_acc.id,
            "name": broker_acc.name,
            "account_type": broker_acc.account_type,
            "balance": broker_acc.balance,
            "equity": broker_acc.equity,
            "currency": broker_acc.currency,
            "server": broker_acc.server,
            "login": broker_acc.login,
            "broker_type": broker_acc.broker_type,
            "is_active": broker_acc.is_active,
            "is_stored": stored is not None,
            "is_selected": stored.is_signal_enabled if stored else False,
            "stored_account_id": stored.id if stored else None,
        })

    return {
        "broker_type": broker_type,
        "accounts": result_accounts,
        "total": len(result_accounts),
    }


@router.put("/{account_id}/select")
async def toggle_account_selection(
    request: Request,
    account_id: int,
    body: SelectAccountBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle account selection for signal routing.

    When selected=True, the account will receive trading signals.
    When selected=False, the account will not receive signals.

    Args:
        account_id: Database account ID (not broker account ID)
        body: { "selected": boolean }

    Returns:
        Updated account selection status
    """
    from app.models.database_models import TradingAccount

    # Get account
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )

    # Update selection status
    account.is_signal_enabled = body.selected
    account.updated_at = datetime.utcnow()
    db.commit()

    return {
        "account_id": account.id,
        "account_number": account.account_number,
        "broker": account.broker.value,
        "is_selected": account.is_signal_enabled,
        "message": f"Account {'selected' if body.selected else 'deselected'} for signal routing"
    }


@router.post("/sync-all")
async def sync_all_accounts(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Re-fetch and sync accounts from all connected brokers.

    Updates stored accounts with latest balance/equity from brokers.
    Identifies new accounts available on brokers (but doesn't auto-add them).

    Returns:
        Sync results per broker including:
        - updated_count: Accounts updated with fresh data
        - new_available_count: New accounts detected on broker
        - error: Any errors during sync
    """
    from app.services.account_fetcher_service import AccountFetcherService
    from app.models.database_models import TradingAccount, BrokerType as DBBrokerType
    from app.core.encryption import decrypt

    # Get all stored accounts grouped by broker
    stored_accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    if not stored_accounts:
        return {
            "synced": False,
            "message": "No accounts to sync",
            "results": []
        }

    # Group by broker
    accounts_by_broker = {}
    for acc in stored_accounts:
        broker = acc.broker.value
        if broker not in accounts_by_broker:
            accounts_by_broker[broker] = []
        accounts_by_broker[broker].append(acc)

    fetcher = AccountFetcherService()
    results = []

    for broker_type, accounts in accounts_by_broker.items():
        result = {
            "broker": broker_type,
            "updated_count": 0,
            "new_available_count": 0,
            "error": None
        }

        try:
            # Use first account's credentials
            account = accounts[0]
            credentials = {}

            if account.api_key:
                try:
                    credentials["api_key"] = decrypt(account.api_key)
                except Exception:
                    credentials["api_key"] = account.api_key
            if account.access_token:
                try:
                    credentials["access_token"] = decrypt(account.access_token)
                except Exception:
                    credentials["access_token"] = account.access_token
            if account.oauth_environment:
                credentials["environment"] = account.oauth_environment
            if account.extra_metadata:
                for key in ["username", "email", "password", "server", "token"]:
                    if key in account.extra_metadata:
                        credentials[key] = account.extra_metadata[key]

            # Fetch accounts from broker
            broker_accounts = await fetcher.fetch_all_accounts(
                user_id=current_user.id,
                broker_type=broker_type,
                credentials=credentials
            )

            # Build lookup for matching
            stored_lookup = {acc.account_number: acc for acc in accounts}

            # Update matching accounts
            for broker_acc in broker_accounts:
                stored = stored_lookup.get(broker_acc.id) or stored_lookup.get(str(broker_acc.id))

                if stored:
                    # Update with fresh data
                    if broker_acc.balance is not None:
                        stored.balance = broker_acc.balance
                    if broker_acc.equity is not None:
                        stored.equity = broker_acc.equity
                    stored.last_sync = datetime.utcnow()
                    result["updated_count"] += 1
                else:
                    # New account available on broker
                    result["new_available_count"] += 1

            db.commit()

        except Exception as e:
            result["error"] = str(e)

        results.append(result)

    total_updated = sum(r["updated_count"] for r in results)
    total_new = sum(r["new_available_count"] for r in results)

    return {
        "synced": True,
        "message": f"Synced {total_updated} accounts. {total_new} new accounts available.",
        "results": results
    }


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