from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from decimal import Decimal

from app.db.database import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User
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
import logging
import secrets
import hashlib
from app.core.encryption import get_encryption_service
from app.models.database_models import Credential

logger = logging.getLogger(__name__)


class TestConnectionBody(BaseModel):
    """Request body for connection test endpoint"""
    broker: str
    credentials: dict


class DiscoverAccountsBody(BaseModel):
    """Request body for account discovery endpoint"""
    broker: str
    credentials: dict


def generate_broker_webhook_key(broker: str, user_id: int) -> str:
    """Generate unique webhook key for broker connection.
    
    Format: webhook_<broker>_user<userId>_<shortRandom>
    Example: webhook_tradelocker_user1234_a8f3c1
    """
    short_random = secrets.token_urlsafe(6)[:8]  # 8 chars, URL-safe
    return f"webhook_{broker.lower()}_user{user_id}_{short_random}"


class DiscoveredAccount(BaseModel):
    """Discovered account from broker - standardized format"""
    broker_account_id: str = Field(..., description="Broker's account ID")
    account_number: Optional[str] = Field(None, description="Account number (if different from broker_account_id)")
    display_name: str = Field(..., description="Display name for the account")
    status: str = Field(default="unknown", description="Account status: active|inactive|blown|unknown")
    account_type: str = Field(default="unknown", description="Account type: eval|funded|demo|unknown")
    broker: str = Field(..., description="Broker identifier")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Legacy fields for backward compatibility
    id: Optional[str] = Field(None, description="Alias for broker_account_id")
    name: Optional[str] = Field(None, description="Alias for display_name")
    currency: Optional[str] = Field(None, description="Account currency")
    is_live: Optional[bool] = Field(None, description="Is live account")
    balance: Optional[float] = Field(None, description="Account balance")
    equity: Optional[float] = Field(None, description="Account equity")


class DiscoverAccountsResponse(BaseModel):
    """Response from account discovery"""
    accounts: List[DiscoveredAccount]
    message: Optional[str] = None


class SelectAccountBody(BaseModel):
    """Request body for account selection toggle"""
    selected: bool


class FetchAvailableAccountsBody(BaseModel):
    """Optional request body for fetching available accounts"""
    credentials: Optional[dict] = None  # Override stored credentials

class ConnectAccountBody(BaseModel):
    """Request body for connecting an existing account"""
    oauth_tokens: Optional[Dict[str, Any]] = None


router = APIRouter()

def _load_credential_fallback(
    db: Session,
    user_id: int,
    broker: str,
    account_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Load decrypted credentials from the credentials store.

    Falls back to the latest matching credential record when TradingAccount fields are empty.
    Filters by account_number when provided.
    """
    credentials: Dict[str, Any] = {}
    encryption = get_encryption_service()

    rows = db.query(Credential).filter(
        Credential.user_id == user_id,
        Credential.service == broker,
        Credential.is_active == True
    ).all()

    for row in rows:
        try:
            data = encryption.decrypt_dict(row.encrypted_data)
        except Exception:
            continue

        data_account_id = data.get("account_id") or data.get("metaapi_account_id")
        if account_number and data_account_id and str(data_account_id) != str(account_number):
            continue

        credentials.update(data)

    return credentials

@router.get("/")
async def get_accounts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all accounts for current user via hexagonal architecture"""
    container = get_container(request)
    use_case = container.get_accounts_use_case()

    # Execute use case
    dto_request = GetAccountsRequest(
        user_id=current_user.id,
        broker=None,  # Get all brokers
        active_only=not include_inactive,
    )
    response = await use_case.execute(dto_request)

    # Convert to API response format
    # Need to fetch webhook_key from ORM since domain entity doesn't include it
    from app.models.database_models import TradingAccount as TradingAccountORM
    
    accounts_with_webhook = []
    for acc in response.accounts:
        # Get full account details from ORM since AccountSummaryDTO is lightweight
        orm_account = db.query(TradingAccountORM).filter(
            TradingAccountORM.id == int(acc.id)
        ).first()
        
        if not orm_account:
            # Skip if account not found in DB
            continue
        
        if not include_inactive and not orm_account.is_active:
            continue

        account_dict = {
            "id": int(acc.id),  # Frontend expects number
            "account_id": orm_account.account_number or acc.id,
            "user_id": current_user.id,
            "broker": acc.broker.value,
            "account_type": orm_account.account_type.value if orm_account.account_type else "demo",
            "balance": float(acc.balance),
            "equity": float(acc.equity),
            "margin": float(orm_account.margin) if orm_account.margin else 0.0,
            "free_margin": float(orm_account.free_margin) if orm_account.free_margin else 0.0,
            "leverage": int(orm_account.leverage) if orm_account.leverage else 100,
            "currency": orm_account.currency or "USD",
            "is_active": orm_account.is_active if hasattr(orm_account, 'is_active') else True,
            "is_connected": acc.is_connected,
            "last_sync": orm_account.last_sync.isoformat() if orm_account.last_sync else None,
            "created_at": orm_account.created_at.isoformat() if orm_account.created_at else None,
            "webhook_key": orm_account.webhook_key,
            # Broker account selection
            "enabled_broker_account_ids": orm_account.enabled_broker_account_ids or [],
            "default_broker_account_id": orm_account.default_broker_account_id,
            "discovered_accounts_cache": orm_account.discovered_accounts_cache,
        }
        accounts_with_webhook.append(account_dict)
    
    return {
        "accounts": accounts_with_webhook,
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

@router.post("/{account_id}/connect")
async def connect_account(
    request: Request,
    account_id: str,
    body: ConnectAccountBody,
    current_user: User = Depends(get_current_user),
):
    """
    Connect an existing account to its broker and mark it as connected.

    Optionally accepts OAuth tokens for brokers like Tradovate.
    """
    container = get_container(request)
    use_case = container.connect_account_use_case()

    dto_request = ConnectAccountRequest(
        account_id=account_id,
        oauth_tokens=body.oauth_tokens,
    )

    response = await use_case.execute(dto_request)

    if response.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.error,
        )

    return {
        "id": response.account_id,
        "is_connected": response.is_connected,
        "balance": float(response.balance or 0),
        "equity": float(response.equity or 0),
        "message": "Account connected successfully",
    }


@router.post("/discover")
async def discover_accounts(
    request: Request,
    body: DiscoverAccountsBody,
    current_user: User = Depends(get_current_user),
):
    """
    Discover available accounts from broker using provided credentials.
    
    READ-ONLY operation - does not save credentials or create accounts.
    Uses same credential parsing + broker construction as test-connection.
    
    Returns:
        - accounts: List of discovered accounts with id, name, account_type, currency, is_live, balance, equity
        - message: Optional message if no accounts found or error occurred
    """
    # Validate broker type
    try:
        broker_type = BrokerType(body.broker.lower())
    except ValueError:
        valid_brokers = [b.value for b in BrokerType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker type: {body.broker}. Valid options: {valid_brokers}"
        )

    # Build executor using same approach as test_connection
    executor = None
    try:
        if broker_type == BrokerType.TRADELOCKER:
            from app.brokers.tradelocker_executor import TradeLockerExecutor
            from app.core.config import settings
            # Get config and override with provided credentials
            config = settings.get_broker_config("tradelocker")
            if body.credentials.get("username") and body.credentials.get("password") and body.credentials.get("server"):
                config["username"] = body.credentials.get("username")
                config["password"] = body.credentials.get("password")
                config["server"] = body.credentials.get("server")
                config["sdk_environment"] = body.credentials.get("sdk_environment") or body.credentials.get("environment", "https://demo.tradelocker.com")
            elif body.credentials.get("api_key"):
                config["api_key"] = body.credentials.get("api_key")
            executor = TradeLockerExecutor()
            # Override config values
            if body.credentials.get("username"):
                executor._sdk_username = body.credentials.get("username")
            if body.credentials.get("password"):
                executor._sdk_password = body.credentials.get("password")
            if body.credentials.get("server"):
                executor._sdk_server = body.credentials.get("server")
            # Accept both sdk_environment (new) and environment (legacy)
            if body.credentials.get("sdk_environment") or body.credentials.get("environment"):
                # Normalize environment URL to ensure it has proper scheme
                raw_env = body.credentials.get("sdk_environment") or body.credentials.get("environment")
                if raw_env:
                    raw_env = raw_env.strip()
                    if not raw_env.startswith("http://") and not raw_env.startswith("https://"):
                        if raw_env.lower() in ("demo", "live"):
                            raw_env = f"https://{raw_env.lower()}.tradelocker.com"
                        elif "." in raw_env:
                            raw_env = f"https://{raw_env}"
                        else:
                            raw_env = f"https://{raw_env}.tradelocker.com"
                executor._sdk_environment = raw_env
            if body.credentials.get("api_key"):
                executor.api_key = body.credentials.get("api_key")
            # Re-check availability
            executor._sdk_available = all([executor._sdk_username, executor._sdk_password, executor._sdk_server])
            executor._brand_api_available = bool(executor.api_key)
            executor.is_available = executor._sdk_available or executor._brand_api_available
            
        elif broker_type in (BrokerType.PROJECTX, BrokerType.TOPSTEP):
            from app.brokers.projectx_executor import ProjectXExecutor
            executor = ProjectXExecutor(
                username=body.credentials.get("username"),
                api_key=body.credentials.get("api_key") or body.credentials.get("api_token"),
            )
            
            # Verify credentials are provided
            if not executor.is_available:
                return DiscoverAccountsResponse(
                    accounts=[],
                    message="ProjectX/TopStep discovery requires username and api_key credentials"
                )
            
        elif broker_type == BrokerType.TRADOVATE:
            from app.brokers.tradovate_executor import TradovateExecutor
            executor = TradovateExecutor(
                access_token=body.credentials.get("access_token"),
                environment=body.credentials.get("environment", "demo"),
            )
            # For password mode, set all required fields
            if not executor._use_oauth and body.credentials.get("user_id"):
                executor.user_id = body.credentials.get("user_id")
                executor.password = body.credentials.get("password")
                # Set optional OAuth app credentials for password auth
                if body.credentials.get("app_id"):
                    executor.app_id = body.credentials.get("app_id")
                if body.credentials.get("app_version"):
                    executor.app_version = body.credentials.get("app_version")
                if body.credentials.get("cid"):
                    executor.cid = body.credentials.get("cid")
                if body.credentials.get("sec"):
                    executor.sec = body.credentials.get("sec")
                
        elif broker_type == BrokerType.MT4:
            from app.brokers.mt4_executor import MT4Executor
            executor = MT4Executor(
                metaapi_token=body.credentials.get("metaapi_token"),
                metaapi_account_id=body.credentials.get("metaapi_account_id"),
            )
            if not executor._has_metaapi_credentials():
                executor.manager_login = body.credentials.get("manager_login") or body.credentials.get("login")
                executor.manager_password = body.credentials.get("manager_password") or body.credentials.get("password")
                
        elif broker_type == BrokerType.MT5:
            from app.brokers.mt5_executor import MT5Executor
            executor = MT5Executor(
                metaapi_token=body.credentials.get("metaapi_token"),
                metaapi_account_id=body.credentials.get("metaapi_account_id"),
            )
            if not executor._has_metaapi_credentials():
                executor.manager_login = body.credentials.get("manager_login") or body.credentials.get("login")
                executor.manager_password = body.credentials.get("manager_password") or body.credentials.get("password")
        else:
            return DiscoverAccountsResponse(
                accounts=[],
                message=f"Broker {broker_type.value} does not support account discovery"
            )
        
        if not executor or not executor.is_available:
            return DiscoverAccountsResponse(
                accounts=[],
                message="Executor not available with provided credentials"
            )
        
        # Initialize executor
        initialized = await executor.initialize()
        if not initialized:
            return DiscoverAccountsResponse(
                accounts=[],
                message="Failed to initialize broker connection"
            )
        
        # Get accounts
        try:
            broker_accounts = await executor.get_accounts()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error getting accounts from {broker_type.value}: {e}")
            
            # For ProjectX, check if SDK discovery is not supported
            if broker_type in (BrokerType.PROJECTX, BrokerType.TOPSTEP):
                return DiscoverAccountsResponse(
                    accounts=[],
                    message=f"Account discovery failed: {str(e)}. You can still add accounts manually with your account ID."
                )
            
            return DiscoverAccountsResponse(
                accounts=[],
                message=f"Error discovering accounts: {str(e)}"
            )
        
        # Normalize to DiscoveredAccount format (standardized)
        discovered = []
        for acc in broker_accounts:
            # Extract account fields - executors return Account objects with various attributes
            acc_id = str(getattr(acc, 'id', ''))
            account_number = getattr(acc, 'account_number', None) or acc_id
            account_name = getattr(acc, 'name', None) or getattr(acc, 'account_name', None) or account_number or acc_id
            
            # Determine account_type
            account_type_raw = getattr(acc, 'account_type', 'live')
            # Map to standardized types
            if account_type_raw in ('evaluation', 'eval', 'challenge'):
                account_type = 'eval'
            elif account_type_raw in ('funded', 'live'):
                account_type = 'funded'
            elif account_type_raw == 'demo':
                account_type = 'demo'
            else:
                account_type = 'unknown'
            
            # Get flags for determining status and for backward compat fields
            is_live = getattr(acc, 'is_live', False)
            is_active = getattr(acc, 'is_active', True)

            # Determine status - check extra_data first (set by SDK wrappers with blow/expired detection)
            extra_data = getattr(acc, 'extra_data', {}) or {}
            if extra_data.get('status'):
                # SDK already determined status (active, blown, expired, inactive)
                status = extra_data['status']
            else:
                # Fallback to is_live/is_active flags
                balance = float(getattr(acc, 'balance', 0))

                if not is_active:
                    status = 'inactive'
                elif balance < 100:
                    # Blown account detection
                    status = 'blown'
                elif is_live:
                    status = 'active'
                else:
                    status = 'active'  # Default to active for demo accounts
            
            currency = getattr(acc, 'currency', 'USD')
            balance = float(getattr(acc, 'balance', 0))
            equity = float(getattr(acc, 'equity', 0))
            
            # Build metadata
            meta = {
                'currency': currency,
                'balance': balance,
                'equity': equity,
                'leverage': getattr(acc, 'leverage', None),
                'margin': getattr(acc, 'margin', None),
                'free_margin': getattr(acc, 'free_margin', None),
            }
            
            discovered.append(DiscoveredAccount(
                broker_account_id=acc_id,
                account_number=account_number if account_number != acc_id else None,
                display_name=account_name,
                status=status,
                account_type=account_type,
                broker=broker_type.value,
                meta=meta,
                # Legacy fields for backward compatibility
                id=acc_id,
                name=account_name,
                currency=currency,
                is_live=is_live,
                balance=balance,
                equity=equity,
            ))
        
        # For ProjectX/TopStep, if no accounts discovered but connection succeeded,
        # provide helpful message
        if not discovered and broker_type in (BrokerType.PROJECTX, BrokerType.TOPSTEP):
            return DiscoverAccountsResponse(
                accounts=[],
                message="No accounts found. ProjectX/TopStep accounts may need to be added manually with your account ID."
            )

        # Filter to only show active/funded/sim accounts for cleaner UX
        # Only show accounts with status in ('active', 'funded') or account_type in ('funded', 'demo', 'eval')
        filtered = [
            acc for acc in discovered
            if acc.status in ('active', 'funded')
            or acc.account_type in ('funded', 'demo', 'eval', 'sim')
        ]

        # Keep SDK order (most recent first by ID) - only take first 5
        # The SDK already sorts by account ID descending (newest accounts first)
        filtered = filtered[:5]

        return DiscoverAccountsResponse(
            accounts=filtered if filtered else discovered[:5],  # Fallback to first 5 if filter too strict
            message=None if filtered else "No active accounts found. Showing available accounts."
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error discovering accounts for {broker_type.value}: {e}")
        return DiscoverAccountsResponse(
            accounts=[],
            message=f"Error discovering accounts: {str(e)}"
        )
    finally:
        # Cleanup executor if needed
        if executor and hasattr(executor, 'shutdown'):
            try:
                await executor.shutdown()
            except:
                pass


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
    db: Session = Depends(get_db),
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

    # Fetch the created account to return full Account object
    from app.models.database_models import TradingAccount as TradingAccountORM, BrokerType as ORMBrokerType
    # Map domain broker to ORM broker enum
    orm_broker = ORMBrokerType.PROJECTX if account.broker.value == "projectx" else getattr(ORMBrokerType, account.broker.value.upper(), ORMBrokerType.PROJECTX)
    
    orm_account = db.query(TradingAccountORM).filter(
        TradingAccountORM.account_number == account.account_id,
        TradingAccountORM.user_id == current_user.id
    ).order_by(TradingAccountORM.created_at.desc()).first()
    
    if not orm_account:
        # Fallback: try to find by broker enum
        orm_account = db.query(TradingAccountORM).filter(
            TradingAccountORM.user_id == current_user.id,
            TradingAccountORM.broker == orm_broker
        ).order_by(TradingAccountORM.created_at.desc()).first()

    if orm_account:
        # Update broker account selection fields if provided
        if account.enabled_broker_account_ids is not None:
            orm_account.enabled_broker_account_ids = account.enabled_broker_account_ids
        if account.default_broker_account_id is not None:
            orm_account.default_broker_account_id = account.default_broker_account_id
        if account.discovered_accounts_cache is not None:
            orm_account.discovered_accounts_cache = account.discovered_accounts_cache

        # Ensure default settings are initialized for new accounts
        if not orm_account.position_sizing_mode:
            orm_account.position_sizing_mode = "fixed"
        if orm_account.fixed_lot_size is None:
            orm_account.fixed_lot_size = 0.01
        if orm_account.percent_of_balance is None:
            orm_account.percent_of_balance = 1.0
        if orm_account.percent_of_equity is None:
            orm_account.percent_of_equity = 1.0
        if orm_account.risk_percent_per_trade is None:
            orm_account.risk_percent_per_trade = 1.0
        if orm_account.is_signal_enabled is None:
            orm_account.is_signal_enabled = True
        if orm_account.signal_priority is None:
            orm_account.signal_priority = 0

        # Auto-connect when credentials are provided (safe, opt-in by input)
        has_credentials = bool(credentials) or bool(account.oauth_tokens)
        if has_credentials:
            try:
                connect_use_case = container.connect_account_use_case()
                connect_response = await connect_use_case.execute(
                    ConnectAccountRequest(
                        account_id=str(orm_account.id),
                        oauth_tokens=account.oauth_tokens,
                    )
                )
                if connect_response.is_connected:
                    orm_account.is_connected = True
                    if connect_response.balance is not None:
                        orm_account.balance = float(connect_response.balance)
                    if connect_response.equity is not None:
                        orm_account.equity = float(connect_response.equity)
            except Exception as exc:
                logger.warning(
                    "Auto-connect failed for account %s (broker=%s): %s",
                    orm_account.id,
                    orm_account.broker.value if hasattr(orm_account.broker, "value") else orm_account.broker,
                    exc,
                )

        db.commit()

        return {
            "id": orm_account.id,
            "account_id": orm_account.account_number,
            "user_id": orm_account.user_id,
            "broker": orm_account.broker.value,
            "account_type": orm_account.account_type.value,
            "currency": orm_account.currency or "USD",
            "leverage": int(orm_account.leverage) if orm_account.leverage else 100,
            "balance": float(orm_account.balance) if orm_account.balance else 0.0,
            "equity": float(orm_account.equity) if orm_account.equity else 0.0,
            "margin": float(orm_account.margin) if orm_account.margin else 0.0,
            "free_margin": float(orm_account.free_margin) if orm_account.free_margin else 0.0,
            "is_active": orm_account.is_active,
            "is_connected": orm_account.is_connected,
            "last_sync": orm_account.last_sync.isoformat() if orm_account.last_sync else None,
            "created_at": orm_account.created_at.isoformat() if orm_account.created_at else None,
            "webhook_key": orm_account.webhook_key,
            "enabled_broker_account_ids": orm_account.enabled_broker_account_ids or [],
            "default_broker_account_id": orm_account.default_broker_account_id,
            "discovered_accounts_cache": orm_account.discovered_accounts_cache,
        }
    
    # Fallback response if account not found in DB
    result = {
        "id": int(response.account_id) if response.account_id.isdigit() else 0,
        "account_id": response.account_id,
        "user_id": current_user.id,
        "broker": response.broker.value,
        "account_type": account.account_type.value,
        "currency": account.currency or "USD",
        "leverage": account.leverage or 100,
        "balance": 0.0,
        "equity": 0.0,
        "margin": 0.0,
        "free_margin": 0.0,
        "is_active": response.is_active,
        "is_connected": False,
        "last_sync": None,
        "created_at": None,
        "webhook_key": None,
    }

    # Include auto-alias count if any were created
    if response.auto_aliases_created > 0:
        result["auto_aliases_created"] = response.auto_aliases_created
        result["message"] = f"Account created with {response.auto_aliases_created} auto-detected symbol aliases"
    else:
        result["message"] = "Account created with encrypted credentials"

    return result


@router.get("/{account_id}")
async def get_account(
    request: Request,
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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

    # Get webhook_key and other fields from ORM (Patch 1.2.1)
    from app.models.database_models import TradingAccount as TradingAccountORM
    # AccountDTO.id is already a string, not AccountId object
    account_id_str = account.id if isinstance(account.id, str) else str(account.id)
    orm_account = db.query(TradingAccountORM).filter(
        TradingAccountORM.id == int(account_id_str)
    ).first()

    if not orm_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found in database"
        )

    return {
        "id": int(account_id_str),
        "account_id": orm_account.account_number or account_id_str,
        "user_id": account.user_id,
        "broker": account.broker.value,
        "account_type": account.account_type.value if account.account_type else "demo",
        "balance": float(account.balance),
        "equity": float(account.equity),
        "margin": float(account.margin),
        "free_margin": float(account.free_margin),
        "leverage": int(account.leverage) if account.leverage else 100,
        "currency": account.currency or "USD",
        "is_active": account.is_active,
        "is_connected": account.is_connected,
        "server": account.server,
        "last_sync": account.last_sync.isoformat() if account.last_sync else None,
        "created_at": orm_account.created_at.isoformat() if orm_account.created_at else None,
        "webhook_key": orm_account.webhook_key,
        # Broker account selection
        "enabled_broker_account_ids": orm_account.enabled_broker_account_ids or [],
        "default_broker_account_id": orm_account.default_broker_account_id,
        "discovered_accounts_cache": orm_account.discovered_accounts_cache,
    }

@router.put("/{account_id}")
async def update_account(
    request: Request,
    account_id: str,
    account_update: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update account with credential re-encryption and broker account selection"""
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

    # Update broker account selection fields directly in ORM
    from app.models.database_models import TradingAccount as TradingAccountORM
    orm_account = db.query(TradingAccountORM).filter(
        TradingAccountORM.id == int(account_id),
        TradingAccountORM.user_id == current_user.id
    ).first()
    
    if not orm_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Update broker account selection if provided
    if account_update.enabled_broker_account_ids is not None:
        orm_account.enabled_broker_account_ids = account_update.enabled_broker_account_ids
    if account_update.default_broker_account_id is not None:
        orm_account.default_broker_account_id = account_update.default_broker_account_id
    if account_update.discovered_accounts_cache is not None:
        orm_account.discovered_accounts_cache = account_update.discovered_accounts_cache
    
    db.commit()
    
    return {
        "id": orm_account.id,
        "account_id": orm_account.account_number,
        "broker": orm_account.broker.value,
        "enabled_broker_account_ids": orm_account.enabled_broker_account_ids or [],
        "default_broker_account_id": orm_account.default_broker_account_id,
        "discovered_accounts_cache": orm_account.discovered_accounts_cache,
        "updated": True,
        "message": "Account updated successfully",
    }

@router.post("/{account_id}/refresh-accounts")
async def refresh_broker_accounts(
    request: Request,
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Refresh discovered broker accounts using stored credentials.
    
    Re-discovers accounts from broker and updates the discovered_accounts_cache.
    Does not change enabled/default selections unless explicitly requested.
    """
    from app.models.database_models import TradingAccount as TradingAccountORM
    from app.core.encryption import decrypt
    
    # Get account
    orm_account = db.query(TradingAccountORM).filter(
        TradingAccountORM.id == int(account_id),
        TradingAccountORM.user_id == current_user.id,
        TradingAccountORM.is_active == True
    ).first()
    
    if not orm_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Build credentials from stored account
    credentials: Dict[str, Any] = {}
    broker = orm_account.broker.value
    
    try:
        # PRIORITY: Load from Credential table first (this is where account creation stores them)
        fallback = _load_credential_fallback(
            db=db,
            user_id=current_user.id,
            broker=broker,
            account_number=orm_account.account_number
        )
        credentials.update(fallback)

        # Then check TradingAccount fields as backup
        if broker == "tradelocker":
            if orm_account.api_key and "api_key" not in credentials:
                credentials["api_key"] = decrypt(orm_account.api_key)
            # Check metadata for SDK credentials (backup only)
            if orm_account.extra_metadata:
                import json
                meta = json.loads(orm_account.extra_metadata) if isinstance(orm_account.extra_metadata, str) else orm_account.extra_metadata
                if meta.get("username") and "username" not in credentials:
                    credentials["username"] = meta["username"]
                if meta.get("password") and "password" not in credentials:
                    credentials["password"] = meta["password"]
                if meta.get("server") and "server" not in credentials:
                    credentials["server"] = meta["server"]
        elif broker in ("projectx", "topstep"):
            if orm_account.api_key and "username" not in credentials:
                credentials["username"] = decrypt(orm_account.api_key)
            if orm_account.api_secret and "api_key" not in credentials:
                credentials["api_key"] = decrypt(orm_account.api_secret)
        elif broker == "tradovate":
            if orm_account.access_token and "access_token" not in credentials:
                credentials["access_token"] = decrypt(orm_account.access_token)
            if "environment" not in credentials:
                credentials["environment"] = orm_account.oauth_environment or "demo"
        elif broker in ("mt4", "mt5"):
            if orm_account.api_key and "metaapi_token" not in credentials:
                credentials["metaapi_token"] = decrypt(orm_account.api_key)
            if orm_account.extra_metadata:
                import json
                meta = json.loads(orm_account.extra_metadata) if isinstance(orm_account.extra_metadata, str) else orm_account.extra_metadata
                if meta.get("metaapi_account_id") and "metaapi_account_id" not in credentials:
                    credentials["metaapi_account_id"] = meta["metaapi_account_id"]
        
        # Call discover endpoint logic
        discover_body = DiscoverAccountsBody(
            broker=broker,
            credentials=credentials
        )
        
        # Call discover_accounts (it doesn't need db, but we'll pass request)
        discover_response = await discover_accounts(request, discover_body, current_user)
        
        # Update cache
        if discover_response.accounts:
            orm_account.discovered_accounts_cache = [
                {
                    "broker_account_id": acc.broker_account_id,
                    "account_number": acc.account_number,
                    "display_name": acc.display_name,
                    "status": acc.status,
                    "account_type": acc.account_type,
                    "meta": acc.meta,
                }
                for acc in discover_response.accounts
            ]
            db.commit()
        
        return {
            "account_id": account_id,
            "discovered_count": len(discover_response.accounts),
            "accounts": discover_response.accounts,
            "message": discover_response.message or "Accounts refreshed successfully",
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh accounts for {account_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh accounts: {str(e)}"
        )


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
    db: Session = Depends(get_db),
):
    """Sync account data from broker via hexagonal architecture"""
    container = get_container(request)
    use_case = container.sync_account_use_case()

    # Convert account_id to string if it's a number (from frontend)
    account_id_str = str(account_id)

    # Execute use case
    dto_request = SyncAccountRequest(account_id=account_id_str)

    try:
        response = await use_case.execute(dto_request)

        # Get full account details from ORM to return complete Account object
        from app.models.database_models import TradingAccount as TradingAccountORM
        orm_account = db.query(TradingAccountORM).filter(
            TradingAccountORM.id == int(account_id_str)
        ).first()

        if not orm_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        # Return full Account object that frontend expects
        return {
            "id": int(account_id_str),
            "account_id": orm_account.account_number or account_id_str,
            "user_id": current_user.id,
            "broker": orm_account.broker.value,
            "account_type": orm_account.account_type.value if orm_account.account_type else "demo",
            "balance": float(response.balance),
            "equity": float(response.equity),
            "margin": float(response.margin),
            "free_margin": float(response.free_margin),
            "leverage": int(orm_account.leverage) if orm_account.leverage else 100,
            "currency": orm_account.currency or "USD",
            "is_active": orm_account.is_active if hasattr(orm_account, 'is_active') else True,
            "is_connected": True,  # Just synced, so connected
            "server": orm_account.server,
            "last_sync": response.synced_at.isoformat(),
            "created_at": orm_account.created_at.isoformat() if orm_account.created_at else None,
            "webhook_key": orm_account.webhook_key,
            "enabled_broker_account_ids": orm_account.enabled_broker_account_ids or [],
            "default_broker_account_id": orm_account.default_broker_account_id,
            "discovered_accounts_cache": orm_account.discovered_accounts_cache,
            "positions_count": response.positions_count,
            "orders_count": response.orders_count,
            "message": "Account synced successfully",
        }
    except HTTPException:
        raise
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
    db: Session = Depends(get_db),
):
    """
    Get current account settings (position sizing, risk limits, routing).

    Returns all configured settings for the specified account.
    """
    from app.models.database_models import TradingAccount as TradingAccountORM

    container = get_container(request)
    use_case = container.get_account_settings_use_case()

    # Handle both sync and async sessions
    if hasattr(db, "query"):
        orm_account = db.query(TradingAccountORM).filter(
            TradingAccountORM.id == account_id,
            TradingAccountORM.user_id == current_user.id
        ).first()
    else:
        # Async session - use select/execute
        stmt = select(TradingAccountORM).where(
            TradingAccountORM.id == account_id,
            TradingAccountORM.user_id == current_user.id
        )
        result = await db.execute(stmt)
        orm_account = result.scalar_one_or_none()

    if not orm_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

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
                "default_stop_loss": getattr(response, 'default_stop_loss', None),
                "default_take_profit": getattr(response, 'default_take_profit', None),
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
            "account": {
                "id": orm_account.id,
                "account_id": orm_account.account_number,
                "user_id": orm_account.user_id,
                "broker": orm_account.broker.value,
                "account_type": orm_account.account_type.value if orm_account.account_type else "demo",
                "currency": orm_account.currency or "USD",
                "leverage": int(orm_account.leverage) if orm_account.leverage else 100,
                "is_active": orm_account.is_active,
                "is_connected": orm_account.is_connected,
                "balance": float(orm_account.balance or 0.0),
                "equity": float(orm_account.equity or 0.0),
                "margin": float(orm_account.margin or 0.0),
                "free_margin": float(orm_account.free_margin or 0.0),
                "last_sync": orm_account.last_sync.isoformat() if orm_account.last_sync else None,
                "created_at": orm_account.created_at.isoformat() if orm_account.created_at else None,
                "webhook_key": orm_account.webhook_key,
                "enabled_broker_account_ids": orm_account.enabled_broker_account_ids or [],
                "default_broker_account_id": orm_account.default_broker_account_id,
                "discovered_accounts_cache": orm_account.discovered_accounts_cache,
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
        default_stop_loss=settings.default_stop_loss,
        default_take_profit=settings.default_take_profit,
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
                "default_stop_loss": getattr(response, 'default_stop_loss', None),
                "default_take_profit": getattr(response, 'default_take_profit', None),
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
