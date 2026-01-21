from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.db.database import get_db
from app.models.models import Account, User
from app.models.schemas import Account as AccountSchema, AccountCreate, AccountUpdate
from app.routers.auth import get_current_user
from app.core.event_emitter import emit_account_event
from app.dependencies import get_container
from app.application.dto.account_dto import (
    GetAccountsRequest,
    CreateAccountRequest,
    UpdateAccountRequest,
    DeleteAccountRequest,
    ConnectAccountRequest,
    SyncAccountRequest,
)
from app.domain.enums import BrokerType, AccountType

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

@router.post("/")
async def create_account(
    request: Request,
    account: AccountCreate,
    current_user: User = Depends(get_current_user),
):
    """Create new trading account with encrypted credentials"""
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

    return {
        "id": response.account_id,
        "broker": response.broker.value,
        "is_active": response.is_active,
        "message": "Account created with encrypted credentials",
    }

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