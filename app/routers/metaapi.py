"""
MetaApi Account Router - BYOA (Bring Your Own Account)

Endpoints for connecting existing MT4/MT5 accounts via MetaApi Cloud.

Security:
- Passwords are NEVER stored or logged
- Only metaapi_account_id is persisted in the Credential table
- All endpoints require authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from app.db.database import get_db
from app.models.models import User
from app.routers.auth import get_current_user
from app.core.encryption import get_encryption_service
from app.core.billing import require_broker_slot
from app.models.database_models import TradingAccount, Credential, BrokerType, AccountType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["metaapi"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ConnectMetaApiRequest(BaseModel):
    """Request to connect an existing MT4/MT5 account via MetaApi"""
    platform: str = Field(..., description="Platform type: 'mt4' or 'mt5'")
    login: str = Field(..., description="MT4/MT5 account login number")
    password: str = Field(..., description="MT4/MT5 account password (NOT stored)")
    server: str = Field(..., description="Broker server name (e.g., 'ICMarkets-Demo')")
    nickname: Optional[str] = Field(None, description="Friendly name for the account")
    account_type: Optional[str] = Field("funded", description="Account type: demo, live, funded, evaluation")


class ConnectMetaApiResponse(BaseModel):
    """Response from MetaApi account connection"""
    account_id: int
    metaapi_account_id: str
    status: str
    platform: str
    login: str
    server: str
    webhook_key: str
    message: str
    account_info: Optional[Dict[str, Any]] = None


class MetaApiStatusResponse(BaseModel):
    """Response for MetaApi account status check"""
    account_id: int
    metaapi_account_id: Optional[str]
    status: str
    state: Optional[str] = None
    connection_status: Optional[str] = None
    platform: str
    server: Optional[str] = None
    last_error: Optional[str] = None
    last_sync: Optional[datetime] = None


class ReconnectResponse(BaseModel):
    """Response from reconnect operation"""
    account_id: int
    metaapi_account_id: str
    status: str
    deployed: bool
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/connect/metaapi", response_model=ConnectMetaApiResponse)
async def connect_metaapi_account(
    body: ConnectMetaApiRequest,
    current_user: User = Depends(require_broker_slot),
    db: Session = Depends(get_db),
):
    """
    Connect an existing MT4/MT5 account via MetaApi Cloud.

    This is BYOA (Bring Your Own Account) - connect your existing prop-firm
    or broker account (FTMO, TFT, etc.) for webhook execution.

    **Security Guarantees:**
    - Password is sent to MetaApi only
    - Password is NEVER stored in our database
    - Password is NEVER logged
    - Only the metaapi_account_id is persisted

    **Flow:**
    1. Validate credentials
    2. Create account in MetaApi Cloud
    3. Deploy and wait for connection
    4. Store metaapi_account_id + metadata (no password)
    5. Generate webhook key

    Returns the account_id and webhook_key for TradingView integration.
    """
    from app.services.metaapi_account_service import (
        get_metaapi_account_service,
        MetaApiAccountError,
        AuthenticationError,
        ServerNotFoundError,
        AccountBlockedError,
        ConnectionTimeoutError,
    )
    from app.routers.accounts import generate_broker_webhook_key

    # Validate platform
    platform = body.platform.lower()
    if platform not in ("mt4", "mt5"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform: '{body.platform}'. Must be 'mt4' or 'mt5'."
        )

    # Get service
    service = get_metaapi_account_service()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MetaApi service not configured. Contact administrator."
        )

    # Validate account type
    try:
        account_type_enum = AccountType(body.account_type.lower() if body.account_type else "funded")
    except ValueError:
        account_type_enum = AccountType.FUNDED

    # Connect via MetaApi (password sent to MetaApi, NOT stored by us)
    try:
        result = await service.connect_existing_account(
            platform=platform,
            login=body.login,
            password=body.password,  # Sent to MetaApi only
            server=body.server,
            nickname=body.nickname,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ServerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AccountBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ConnectionTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except MetaApiAccountError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"MetaApi connect failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection failed: {str(e)}"
        )

    # Password is now discarded from memory (no longer needed)
    # DO NOT reference body.password after this point

    metaapi_account_id = result["metaapi_account_id"]
    logger.info(f"MetaApi account connected: {metaapi_account_id} for user {current_user.id}")

    # Create TradingAccount record
    broker_type = BrokerType.MT4 if platform == "mt4" else BrokerType.MT5
    webhook_key = generate_broker_webhook_key(platform, current_user.id)

    account = TradingAccount(
        user_id=current_user.id,
        broker=broker_type,
        account_type=account_type_enum,
        account_number=body.login,
        account_name=body.nickname or f"{platform.upper()}-{body.login}",
        is_active=True,
        is_connected=result["status"] == "ready",
        is_signal_enabled=True,
        webhook_key=webhook_key,
        currency=result.get("account_info", {}).get("currency", "USD"),
        leverage=result.get("account_info", {}).get("leverage", 100),
        balance=result.get("account_info", {}).get("balance", 0),
        equity=result.get("account_info", {}).get("equity", 0),
        margin=result.get("account_info", {}).get("margin", 0),
        free_margin=result.get("account_info", {}).get("free_margin", 0),
        last_sync=datetime.utcnow() if result.get("account_info") else None,
        extra_metadata={
            "metaapi_account_id": metaapi_account_id,
            "server": body.server,
            "metaapi_name": result.get("name"),
        },
    )

    db.add(account)
    db.flush()  # Get account.id

    # Store credential (metaapi_account_id only, NO password)
    encryption = get_encryption_service()
    credential_data = {
        "metaapi_account_id": metaapi_account_id,
        "login": body.login,
        "server": body.server,
        "platform": platform,
        # NOTE: password is NOT stored
    }

    credential = Credential(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=f"{platform.upper()}-{body.login}",
        type="metaapi",
        service=platform,
        encrypted_data=encryption.encrypt_dict(credential_data),
        is_active=True,
    )

    db.add(credential)
    db.commit()

    logger.info(f"Account {account.id} created with metaapi_account_id={metaapi_account_id}")

    return ConnectMetaApiResponse(
        account_id=account.id,
        metaapi_account_id=metaapi_account_id,
        status=result["status"],
        platform=platform,
        login=body.login,
        server=body.server,
        webhook_key=webhook_key,
        message="Account connected successfully. Use the webhook_key for TradingView integration.",
        account_info=result.get("account_info"),
    )


@router.get("/{account_id}/metaapi/status", response_model=MetaApiStatusResponse)
async def get_metaapi_status(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get deployment and connection status for a MetaApi-connected account.

    Returns current state (DEPLOYED, DEPLOYING, UNDEPLOYED) and
    connection status (CONNECTED, DISCONNECTED, CONNECTING).

    Use this to check if the account is ready for webhook execution.
    """
    from app.services.metaapi_account_service import get_metaapi_account_service

    # Get account
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Verify it's an MT4/MT5 account
    broker = account.broker.value.lower() if hasattr(account.broker, 'value') else str(account.broker).lower()
    if broker not in ("mt4", "mt5"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not a MetaApi account (broker: {broker})"
        )

    # Get metaapi_account_id from metadata or credential
    metaapi_account_id = None
    if account.extra_metadata:
        metaapi_account_id = account.extra_metadata.get("metaapi_account_id")

    if not metaapi_account_id:
        # Try credential table
        encryption = get_encryption_service()
        credential = db.query(Credential).filter(
            Credential.user_id == current_user.id,
            Credential.service == broker,
            Credential.is_active == True
        ).order_by(Credential.created_at.desc()).first()

        if credential:
            try:
                cred_data = encryption.decrypt_dict(credential.encrypted_data)
                metaapi_account_id = cred_data.get("metaapi_account_id")
            except Exception:
                pass

    if not metaapi_account_id:
        return MetaApiStatusResponse(
            account_id=account_id,
            metaapi_account_id=None,
            status="not_provisioned",
            platform=broker,
            last_error="No metaapi_account_id found. Account may need provisioning.",
        )

    # Get status from MetaApi
    service = get_metaapi_account_service()
    if not service:
        return MetaApiStatusResponse(
            account_id=account_id,
            metaapi_account_id=metaapi_account_id,
            status="service_unavailable",
            platform=broker,
            last_error="MetaApi service not configured",
        )

    status_result = await service.get_account_status(metaapi_account_id)

    # Update account connection status in DB
    if status_result.get("status") == "ready":
        account.is_connected = True
        account.last_sync = datetime.utcnow()
        db.commit()
    elif status_result.get("status") == "disconnected":
        account.is_connected = False
        db.commit()

    return MetaApiStatusResponse(
        account_id=account_id,
        metaapi_account_id=metaapi_account_id,
        status=status_result.get("status", "unknown"),
        state=status_result.get("state"),
        connection_status=status_result.get("connection_status"),
        platform=broker,
        server=status_result.get("server") or (account.extra_metadata or {}).get("server"),
        last_error=status_result.get("error"),
        last_sync=account.last_sync,
    )


@router.post("/{account_id}/metaapi/reconnect", response_model=ReconnectResponse)
async def reconnect_metaapi_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Redeploy a MetaApi account that has disconnected.

    Use this if the account status shows as disconnected or failed.
    This will attempt to redeploy the account without requiring new credentials.

    Note: This does NOT infinitely retry. If deployment fails, check the
    status endpoint for error details.
    """
    from app.services.metaapi_account_service import get_metaapi_account_service

    # Get account
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Verify it's an MT4/MT5 account
    broker = account.broker.value.lower() if hasattr(account.broker, 'value') else str(account.broker).lower()
    if broker not in ("mt4", "mt5"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not a MetaApi account (broker: {broker})"
        )

    # Get metaapi_account_id
    metaapi_account_id = None
    if account.extra_metadata:
        metaapi_account_id = account.extra_metadata.get("metaapi_account_id")

    if not metaapi_account_id:
        encryption = get_encryption_service()
        credential = db.query(Credential).filter(
            Credential.user_id == current_user.id,
            Credential.service == broker,
            Credential.is_active == True
        ).order_by(Credential.created_at.desc()).first()

        if credential:
            try:
                cred_data = encryption.decrypt_dict(credential.encrypted_data)
                metaapi_account_id = cred_data.get("metaapi_account_id")
            except Exception:
                pass

    if not metaapi_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No metaapi_account_id found. Account needs to be connected first."
        )

    # Get service
    service = get_metaapi_account_service()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MetaApi service not configured"
        )

    # Deploy
    result = await service.deploy_account(metaapi_account_id)

    # Update DB
    if result.get("status") == "ready":
        account.is_connected = True
        account.last_sync = datetime.utcnow()
        db.commit()

    return ReconnectResponse(
        account_id=account_id,
        metaapi_account_id=metaapi_account_id,
        status=result.get("status", "unknown"),
        deployed=result.get("deployed", False),
        message=result.get("message") or f"Reconnect {'successful' if result.get('deployed') else 'failed'}",
    )
