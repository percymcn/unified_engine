"""
Broker Health Check Router
Returns connection status for all brokers based on stored accounts
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any
from app.db.database import get_db
from app.models.database_models import TradingAccount, BrokerType as DBBrokerType, Credential
from app.core.encryption import decrypt, get_encryption_service
import json
from app.brokers.tradelocker_executor import TradeLockerExecutor
from app.brokers.tradovate_executor import TradovateExecutor
from app.brokers.projectx_executor import ProjectXExecutor
from app.brokers.mt4_executor import MT4Executor
from app.brokers.mt5_executor import MT5Executor
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["brokers", "health"])

def _load_credential_fallback(
    db: Session,
    account: TradingAccount,
    broker_type: DBBrokerType
) -> Dict[str, Any]:
    """Load decrypted credentials from Credential table with account_id matching."""
    credentials: Dict[str, Any] = {}
    encryption = get_encryption_service()

    # Try both lowercase and original case for service name
    service_names = [broker_type.value.lower(), broker_type.value]

    rows = db.query(Credential).filter(
        Credential.user_id == account.user_id,
        Credential.service.in_(service_names),
        Credential.is_active == True
    ).all()

    for row in rows:
        try:
            data = encryption.decrypt_dict(row.encrypted_data)
        except Exception:
            continue

        # More flexible account matching:
        # 1. If no account_id in credential data, accept it (single credential for broker)
        # 2. If account_id matches account_number, accept it
        # 3. If only one active credential exists for this user/broker, accept it
        data_account_id = data.get("account_id") or data.get("metaapi_account_id")
        if data_account_id:
            # Skip if there's an account_id but it doesn't match
            # However, the account_number might be a UUID while credential has numeric ID
            # So only skip if we have multiple credentials and this one doesn't match
            if len(rows) > 1 and account.account_number and str(data_account_id) != str(account.account_number):
                continue

        credentials.update(data)

    return credentials

@router.get("/brokers/health")
async def get_broker_health(db: Session = Depends(get_db)):
    """
    Get health status for all brokers based on stored accounts.
    Tests connection for each broker that has stored accounts.
    """
    broker_status = {}
    
    # Get all brokers with stored accounts
    brokers_with_accounts = db.query(TradingAccount.broker).distinct().all()
    broker_types = [b[0] for b in brokers_with_accounts]
    
    # Check each broker
    for broker_type in broker_types:
        try:
            # Get first active account for this broker
            account = db.query(TradingAccount).filter(
                TradingAccount.broker == broker_type,
                TradingAccount.is_active == True
            ).first()
            
            if not account:
                broker_status[broker_type.value] = {
                    "connected": False,
                    "status": "no_accounts",
                    "message": "No active accounts configured"
                }
                continue
            
            # Test connection based on broker type
            is_connected = await _test_broker_connection(broker_type, account, db)
            
            broker_status[broker_type.value] = {
                "connected": is_connected,
                "status": "connected" if is_connected else "disconnected",
                "message": "Broker online" if is_connected else "Broker offline"
            }
            
        except Exception as e:
            logger.error(f"Error checking {broker_type.value} health: {e}")
            broker_status[broker_type.value] = {
                "connected": False,
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    # Also check brokers that might be configured but have no accounts
    all_broker_types = [DBBrokerType.TRADELOCKER, DBBrokerType.TRADOVATE, 
                       DBBrokerType.PROJECTX, DBBrokerType.MT4, DBBrokerType.MT5]
    
    for broker_type in all_broker_types:
        if broker_type.value not in broker_status:
            broker_status[broker_type.value] = {
                "connected": False,
                "status": "not_configured",
                "message": "No accounts configured"
            }
    
    return {
        "status": "healthy" if any(s.get("connected") for s in broker_status.values()) else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "brokers": broker_status
    }


async def _test_broker_connection(broker_type: DBBrokerType, account: TradingAccount, db: Session) -> bool:
    """Test broker connection using stored account credentials"""
    try:
        # Decrypt credentials - check both TradingAccount fields and Credential table
        credentials: Dict[str, Any] = {}
        
        # First, try to get credentials from TradingAccount fields
        if broker_type in [DBBrokerType.TRADELOCKER, DBBrokerType.TRADOVATE, DBBrokerType.PROJECTX]:
            if hasattr(account, 'api_key') and account.api_key:
                try:
                    credentials["api_key"] = decrypt(account.api_key)
                except Exception as e:
                    logger.warning(f"Failed to decrypt api_key: {e}")
            if hasattr(account, 'api_secret') and account.api_secret:
                try:
                    credentials["api_secret"] = decrypt(account.api_secret)
                except Exception as e:
                    logger.warning(f"Failed to decrypt api_secret: {e}")
            if hasattr(account, 'server') and account.server:
                credentials["server"] = account.server
            
            # If no credentials in TradingAccount, try Credential table
            if not credentials.get("api_key") and not credentials.get("username"):
                credentials.update(_load_credential_fallback(db, account, broker_type))
        
        elif broker_type in [DBBrokerType.MT4, DBBrokerType.MT5]:
            # MT4/MT5 might store credentials in api_key/api_secret or separate fields
            if hasattr(account, 'login') and account.login:
                credentials["login"] = account.login
            elif hasattr(account, 'api_key') and account.api_key:
                try:
                    credentials["login"] = decrypt(account.api_key)
                except:
                    credentials["login"] = account.api_key
            
            if hasattr(account, 'password') and account.password:
                try:
                    credentials["password"] = decrypt(account.password)
                except Exception as e:
                    logger.warning(f"Failed to decrypt password: {e}")
            elif hasattr(account, 'api_secret') and account.api_secret:
                try:
                    credentials["password"] = decrypt(account.api_secret)
                except:
                    credentials["password"] = account.api_secret
            
            if hasattr(account, 'server') and account.server:
                credentials["server"] = account.server
            
            # If no credentials, try Credential table
            if not credentials.get("login") and not credentials.get("metaapi_token"):
                credentials.update(_load_credential_fallback(db, account, broker_type))

            # Also check extra_metadata for metaapi_account_id (metaapi.py stores it there)
            if hasattr(account, 'extra_metadata') and account.extra_metadata:
                if account.extra_metadata.get("metaapi_account_id"):
                    credentials["metaapi_account_id"] = account.extra_metadata.get("metaapi_account_id")
                if account.extra_metadata.get("server") and not credentials.get("server"):
                    credentials["server"] = account.extra_metadata.get("server")

        # Check if we have required credentials
        if broker_type == DBBrokerType.TRADELOCKER:
            has_sdk = all([credentials.get("username"), credentials.get("password"), credentials.get("server")])
            has_brand = bool(credentials.get("api_key"))
            if not (has_sdk or has_brand):
                logger.warning("tradelocker: Missing username/password/server or api_key")
                return False
        elif broker_type == DBBrokerType.TRADOVATE:
            has_oauth = bool(credentials.get("access_token"))
            has_password = bool(credentials.get("user_id") and credentials.get("password"))
            if not (has_oauth or has_password):
                logger.warning("tradovate: Missing access_token or user_id/password")
                return False
        elif broker_type == DBBrokerType.PROJECTX:
            if not credentials.get("api_key") or not credentials.get("username"):
                logger.warning("projectx: Missing username/api_key")
                return False
        elif broker_type in [DBBrokerType.MT4, DBBrokerType.MT5]:
            # Use settings.METAAPI_TOKEN as fallback if not in credentials
            metaapi_token = credentials.get("metaapi_token") or settings.METAAPI_TOKEN
            has_metaapi = bool(metaapi_token and credentials.get("metaapi_account_id"))
            has_manager = bool(credentials.get("login") and credentials.get("password") and credentials.get("server"))
            if not (has_metaapi or has_manager):
                logger.warning(f"{broker_type.value}: Missing MetaAPI or manager credentials")
                return False
            # Store resolved token for later use
            if metaapi_token and not credentials.get("metaapi_token"):
                credentials["metaapi_token"] = metaapi_token
        
        # Create executor and test connection
        executor = None
        try:
            if broker_type == DBBrokerType.TRADELOCKER:
                # TradeLocker SDK uses username/password/server - pass through constructor
                if credentials.get("username") and credentials.get("password") and credentials.get("server"):
                    # Normalize environment URL if provided
                    raw_env = None
                    if credentials.get("sdk_environment") or credentials.get("environment"):
                        raw_env = (credentials.get("sdk_environment") or credentials.get("environment")).strip()
                        if not raw_env.startswith("http://") and not raw_env.startswith("https://"):
                            if raw_env.lower() in ("demo", "live"):
                                raw_env = f"https://{raw_env.lower()}.tradelocker.com"
                            elif "." in raw_env:
                                raw_env = f"https://{raw_env}"
                            else:
                                raw_env = f"https://{raw_env}.tradelocker.com"

                    # Pass ALL credentials through constructor - no env var fallback
                    executor = TradeLockerExecutor(
                        username=credentials.get("username"),
                        password=credentials.get("password"),
                        server=credentials.get("server"),
                        sdk_environment=raw_env,
                        account_id=credentials.get("broker_account_id"),
                        account_num=credentials.get("account_num"),
                    )
                else:
                    return False
                
            elif broker_type == DBBrokerType.TRADOVATE:
                if credentials.get("access_token"):
                    executor = TradovateExecutor(
                        account_id=account.id,
                        access_token=credentials.get("access_token"),
                        environment=credentials.get("environment") or account.oauth_environment,
                    )
                else:
                    executor = TradovateExecutor()
                    if credentials.get("user_id") and credentials.get("password"):
                        executor.user_id = credentials.get("user_id")
                        executor.password = credentials.get("password")
                    else:
                        return False
                
            elif broker_type == DBBrokerType.PROJECTX:
                executor = ProjectXExecutor(
                    username=credentials.get("username"),
                    api_key=credentials.get("api_key")
                )
                if not executor.is_available:
                    return False
                
            elif broker_type == DBBrokerType.MT4:
                # Try MetaAPI credentials first (from settings fallback if needed)
                metaapi_token = credentials.get("metaapi_token") or settings.METAAPI_TOKEN
                metaapi_account_id = credentials.get("metaapi_account_id") or credentials.get("account_id")

                if metaapi_token and metaapi_account_id:
                    executor = MT4Executor(
                        metaapi_token=metaapi_token,
                        metaapi_account_id=metaapi_account_id,
                    )
                else:
                    # Try creating executor with global config (manager mode)
                    executor = MT4Executor()
                    if not executor.is_available:
                        logger.warning(f"MT4: No MetaAPI or manager credentials configured")
                        return False

            elif broker_type == DBBrokerType.MT5:
                # Try MetaAPI credentials first (from settings fallback if needed)
                metaapi_token = credentials.get("metaapi_token") or settings.METAAPI_TOKEN
                metaapi_account_id = credentials.get("metaapi_account_id") or credentials.get("account_id")

                if metaapi_token and metaapi_account_id:
                    executor = MT5Executor(
                        metaapi_token=metaapi_token,
                        metaapi_account_id=metaapi_account_id,
                    )
                else:
                    # Try creating executor with global config (manager mode)
                    executor = MT5Executor()
                    if not executor.is_available:
                        logger.warning(f"MT5: No MetaAPI or manager credentials configured")
                        return False
            
            if executor:
                # Try to initialize (with timeout)
                import asyncio
                try:
                    success = await asyncio.wait_for(executor.initialize(), timeout=10.0)
                    if success and executor.is_connected:
                        await executor.disconnect()
                        return True
                    else:
                        if executor:
                            try:
                                await executor.disconnect()
                            except:
                                pass
                        return False
                except asyncio.TimeoutError:
                    logger.warning(f"{broker_type.value} connection test timed out")
                    if executor:
                        try:
                            await executor.disconnect()
                        except:
                            pass
                    return False
                except Exception as e:
                    logger.warning(f"{broker_type.value} connection test failed: {e}")
                    if executor:
                        try:
                            await executor.disconnect()
                        except:
                            pass
                    return False
                    
        except Exception as e:
            logger.error(f"Error creating executor for {broker_type.value}: {e}")
            if executor:
                try:
                    await executor.disconnect()
                except:
                    pass
            return False
        
        return False
        
    except Exception as e:
        logger.error(f"Error testing {broker_type.value} connection: {e}")
        return False
