from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

from app.db.database import get_db
from app.models.models import Account, TradingAccount, WebhookConfig
from app.routers.auth import get_current_user
from app.models.schemas import User
from app.infrastructure.container import get_container
from app.application.dto.account_dto import AccountCreate
from app.domain.enums import BrokerType
from app.core.encryption import encryption_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("/activate")
async def activate_account(
    account_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate and connect a trading account.
    
    This endpoint marks an account as active and establishes the connection
    to the broker, enabling signal execution.
    """
    try:
        # Validate required fields
        if not account_data.get('account_id'):
            raise HTTPException(
                status_code=400,
                detail="account_id is required"
            )
        
        # Find existing account
        account = db.query(Account).filter(
            Account.id == int(account_data['account_id']),
            Account.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(
                status_code=404,
                detail="Account not found"
            )
        
        # Extract broker type for connection
        broker_type = account.broker
        
        # Get container and broker adapter
        container = get_container()
        broker_adapter = container.get_broker_adapter(broker_type)
        
        # Connect to broker (mock for demo accounts, real for production)
        if account.account_type == "demo":
            # For demo accounts, simulate successful connection
            connection_result = {
                "success": True,
                "account_id": str(account.id),
                "broker": broker_type.value,
                "status": "connected",
                "balance": 10000.0,  # Demo balance
                "message": "Demo account connected successfully"
            }
        else:
            # For real accounts, attempt actual broker connection
            try:
                credentials_data = await _get_account_credentials(db, account.id)
                connection_result = await broker_adapter.connect(credentials_data)
            except Exception as e:
                logger.error(f"Failed to connect account {account.id}: {e}")
                connection_result = {
                    "success": False,
                    "account_id": str(account.id),
                    "broker": broker_type.value,
                    "status": "failed",
                    "error": str(e)
                }
        
        if connection_result.get("success"):
            # Update account status to active and connected
            account.is_active = True
            account.is_connected = True
            account.last_sync = None  # Will be updated on first data sync
            
            # Update webhook configuration if not exists
            if not account.webhook_key:
                from app.routers.webhooks import generate_webhook_key
                account.webhook_key = generate_webhook_key()
            
            db.commit()
            
            # Create webhook config for this account
            webhook_config = WebhookConfig(
                account_id=account.id,
                webhook_key=account.webhook_key,
                broker_type=broker_type,
                is_active=True
            )
            db.add(webhook_config)
            db.commit()
            
            logger.info(f"Account {account.id} activated and connected successfully")
        
        return connection_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account activation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Account activation failed"
        )

async def _get_account_credentials(db: Session, account_id: int) -> Dict[str, Any]:
    """
    Get decrypted credentials for an account.
    """
    from app.models.database_models import Credential
    
    credential = db.query(Credential).filter(
        Credential.account_id == account_id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=404,
            detail="Credentials not found for account"
        )
    
    try:
        decrypted_data = encryption_service.decrypt_dict(credential.encrypted_data)
        return decrypted_data
    except Exception as e:
        logger.error(f"Failed to decrypt credentials for account {account_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt account credentials"
        )

@router.get("/activation-status/{account_id}")
async def get_activation_status(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the activation status of a specific account.
    """
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    
    return {
        "account_id": account.id,
        "broker": account.broker.value if account.broker else None,
        "account_type": account.account_type,
        "is_active": account.is_active,
        "is_connected": account.is_connected,
        "last_sync": account.last_sync.isoformat() if account.last_sync else None,
        "has_webhook_key": bool(account.webhook_key),
        "status": "connected" if account.is_connected else "disconnected",
        "activation_message": (
            "Account is active and connected" if account.is_connected 
            else "Account requires activation"
        )
    }