"""
Trading Background Tasks

Celery tasks for asynchronous trading operations including:
- Account balance/equity synchronization
- P&L tracking and risk limit monitoring
- Position synchronization
"""

import logging
from datetime import datetime, date as date_type
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.db.database import get_db_session
from app.models.database_models import TradingAccount
from app.domain.services.risk_tracking_hooks import RiskTrackingHooks
from app.domain.services.daily_pnl_service import DailyPnLService
from app.domain.services.drawdown_service import DrawdownService
from app.infrastructure.repositories.daily_pnl_repository import SQLAlchemyDailyPnLRepository
from app.infrastructure.repositories.drawdown_repository import SQLAlchemyDrawdownRepository

logger = logging.getLogger(__name__)


def _create_account_executor(account: TradingAccount, db: Session):
    """
    Create broker executor for account.

    Args:
        account: TradingAccount model
        db: Database session

    Returns:
        Broker executor instance or None
    """
    try:
        from app.brokers.mt4_executor import MT4Executor
        from app.brokers.mt5_executor import MT5Executor
        from app.brokers.tradelocker_executor import TradeLockerExecutor
        from app.brokers.tradovate_executor import TradovateExecutor
        from app.brokers.projectx_executor import ProjectXExecutor
        from app.models.database_models import Credential
        from app.core.encryption import get_encryption_service

        encryption = get_encryption_service()
        broker = account.broker.lower() if account.broker else ""

        # Load credentials
        credential = db.query(Credential).filter(
            Credential.user_id == account.user_id,
            Credential.broker == account.broker
        ).first()

        if not credential:
            logger.warning(f"No credentials found for account {account.id} ({account.broker})")
            return None

        # Decrypt credentials
        creds = {}
        try:
            creds = encryption.decrypt_dict(credential.encrypted_credentials)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for account {account.id}: {e}")
            return None

        # Create executor based on broker
        if broker in ("mt4", "mt5"):
            # MT4/MT5 use MetaAPI
            if not account.metaapi_account_id:
                logger.debug(f"MT4/MT5 account {account.id} has no metaapi_account_id")
                return None

            executor_class = MT4Executor if broker == "mt4" else MT5Executor
            return executor_class(account.metaapi_account_id)

        elif broker == "tradelocker":
            return TradeLockerExecutor(
                email=creds.get("email"),
                password=creds.get("password"),
                server=creds.get("server", "https://demo.tradelocker.com"),
                account_id=account.broker_account_id
            )

        elif broker == "tradovate":
            return TradovateExecutor(
                username=creds.get("username"),
                password=creds.get("password"),
                cid=creds.get("cid"),
                secret=creds.get("secret"),
                environment=creds.get("environment", "demo")
            )

        elif broker in ("projectx", "topstep"):
            return ProjectXExecutor(
                email=creds.get("email"),
                password=creds.get("password")
            )

        else:
            logger.warning(f"Unknown broker type: {broker}")
            return None

    except Exception as e:
        logger.error(f"Failed to create executor for account {account.id}: {e}")
        return None


@celery_app.task(name="trading_tasks.sync_account_equity")
def sync_account_equity(account_id: int) -> Dict[str, Any]:
    """
    Sync single account equity and balance from broker.

    Updates:
    - Account balance/equity
    - DailyPnL table
    - AccountEquityHistory table

    Args:
        account_id: Account ID to sync

    Returns:
        Sync result dict
    """
    db = None
    try:
        db = next(get_db_session())

        # Get account
        account = db.query(TradingAccount).filter(TradingAccount.id == account_id).first()
        if not account:
            return {"success": False, "error": f"Account {account_id} not found"}

        if not account.is_active:
            return {"success": False, "error": "Account is inactive"}

        # Create executor
        executor = _create_account_executor(account, db)
        if not executor:
            return {"success": False, "error": "Failed to create broker executor"}

        # Fetch account info from broker
        try:
            account_info = executor.get_account_info()
            if not account_info:
                return {"success": False, "error": "Failed to fetch account info from broker"}

            balance = float(account_info.get("balance", 0))
            equity = float(account_info.get("equity", balance))

            # Update account record
            account.balance = balance
            account.equity = equity
            account.last_sync = datetime.utcnow()
            db.commit()

        except Exception as e:
            logger.error(f"Failed to fetch account info for {account_id}: {e}")
            return {"success": False, "error": str(e)}

        # Initialize risk tracking services
        pnl_repo = SQLAlchemyDailyPnLRepository(db)
        pnl_service = DailyPnLService(pnl_repo)

        drawdown_repo = SQLAlchemyDrawdownRepository(db)
        drawdown_service = DrawdownService(drawdown_repo)

        hooks = RiskTrackingHooks(
            daily_pnl_service=pnl_service,
            drawdown_service=drawdown_service
        )

        # Update P&L and equity tracking
        await_result = hooks.on_equity_update(
            account_id=account_id,
            equity=equity,
            balance=balance,
            unrealized_pnl=(equity - balance)
        )

        # Run async hook (sync wrapper)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(await_result)

        logger.info(f"Synced account {account_id}: balance=${balance:.2f}, equity=${equity:.2f}")

        return {
            "success": True,
            "account_id": account_id,
            "balance": balance,
            "equity": equity,
            "unrealized_pnl": equity - balance
        }

    except Exception as e:
        logger.error(f"Error syncing account {account_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if db:
            db.close()


@celery_app.task(name="trading_tasks.sync_all_accounts")
def sync_all_accounts() -> Dict[str, Any]:
    """
    Sync equity/balance for all active accounts.

    Called periodically by Celery Beat (every 5 minutes recommended).

    Returns:
        Summary of sync results
    """
    db = None
    try:
        db = next(get_db_session())

        # Get all active accounts
        accounts = db.query(TradingAccount).filter(
            TradingAccount.is_active == True
        ).all()

        logger.info(f"Starting sync for {len(accounts)} active accounts")

        results = {
            "total": len(accounts),
            "synced": 0,
            "failed": 0,
            "errors": []
        }

        for account in accounts:
            try:
                result = sync_account_equity(account.id)
                if result.get("success"):
                    results["synced"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "account_id": account.id,
                        "error": result.get("error")
                    })
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "account_id": account.id,
                    "error": str(e)
                })
                logger.error(f"Failed to sync account {account.id}: {e}")

        logger.info(f"Sync complete: {results['synced']} synced, {results['failed']} failed")

        return results

    except Exception as e:
        logger.error(f"Error in sync_all_accounts: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if db:
            db.close()


@celery_app.task(name="trading_tasks.sync_positions")
def sync_positions() -> Dict[str, Any]:
    """
    Sync open positions from all brokers.

    Future enhancement: Track position changes and call on_trade_closed
    when positions close.

    Returns:
        Sync summary
    """
    # TODO: Implement position tracking
    # When a position closes:
    # - Call hooks.on_trade_closed(account_id, pnl, is_win)
    # - Updates daily_pnl trade counts

    logger.info("Position sync not yet implemented")
    return {"status": "not_implemented"}


@celery_app.task(name="trading_tasks.process_trade")
def process_trade(trade_data: dict) -> Dict[str, Any]:
    """
    Process a trade asynchronously.

    Args:
        trade_data: Trade information dict

    Returns:
        Processing result
    """
    # Placeholder for future trade processing logic
    logger.info(f"Processing trade: {trade_data}")
    return {"status": "processed", "data": trade_data}
