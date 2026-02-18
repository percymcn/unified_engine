"""
Trading Background Tasks

Celery tasks for asynchronous trading operations including:
- Account balance/equity synchronization
- P&L tracking and risk limit monitoring
- Position synchronization
"""

import logging
from datetime import datetime, date as date_type, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.db.database import get_db_session
from app.models.database_models import TradingAccount
from app.domain.services.risk_tracking_hooks import RiskTrackingHooks
from app.domain.services.daily_pnl_service import DailyPnLService
from app.domain.services.drawdown_service import DrawdownService
from app.infrastructure.repositories.daily_pnl_repository import DailyPnLRepository
from app.infrastructure.repositories.equity_history_repository import EquityHistoryRepository

logger = logging.getLogger(__name__)


def _load_account_credentials(db: Session, account: TradingAccount) -> Dict[str, Any]:
    """Load decrypted credentials for a trading account.

    First checks TradingAccount fields, then falls back to Credential table.
    """
    from app.models.database_models import Credential
    from app.core.encryption import get_encryption_service

    credentials: Dict[str, Any] = {}
    encryption = get_encryption_service()
    broker_value = account.broker.value

    # For OAuth-based brokers (Tradovate), check TradingAccount OAuth fields first
    if account.access_token:
        credentials["access_token"] = account.access_token
    if account.refresh_token:
        credentials["refresh_token"] = account.refresh_token
    if account.oauth_environment:
        credentials["environment"] = account.oauth_environment

    # If OAuth tokens found, return early (Tradovate primarily uses these)
    if credentials.get("access_token"):
        credentials["account_id"] = account.account_number
        return credentials

    # Load from Credential table
    rows = db.query(Credential).filter(
        Credential.user_id == account.user_id,
        Credential.service == broker_value,
        Credential.is_active == True
    ).all()

    for row in rows:
        try:
            data = encryption.decrypt_dict(row.encrypted_data)
        except Exception as e:
            logger.warning(f"Failed to decrypt credential {row.id}: {e}")
            continue

        # Match by account_id/account_number, default_broker_account_id, or extra_metadata.metaapi_account_id
        data_account_id = data.get("account_id") or data.get("metaapi_account_id")
        if data_account_id:
            matches_account_number = str(data_account_id) == str(account.account_number)
            matches_broker_account = account.default_broker_account_id and str(data_account_id) == str(account.default_broker_account_id)
            extra_meta_id = account.extra_metadata.get("metaapi_account_id") if account.extra_metadata and isinstance(account.extra_metadata, dict) else None
            matches_meta_account = extra_meta_id and str(data_account_id) == str(extra_meta_id)
            # For brokers with multiple sub-accounts (e.g. ProjectX/TopStep), credential may be
            # saved with any enabled sub-account ID — check the full enabled list
            enabled_ids = account.enabled_broker_account_ids or []
            matches_enabled = str(data_account_id) in [str(i) for i in enabled_ids]
            if not matches_account_number and not matches_broker_account and not matches_meta_account and not matches_enabled:
                continue

        credentials.update(data)

    # Also include account_number/id for broker use
    credentials["account_id"] = account.account_number
    if account.default_broker_account_id:
        credentials["broker_account_id"] = account.default_broker_account_id

    # For MT4/MT5 accounts, also check extra_metadata for metaapi_account_id
    if account.broker and account.broker.value in ("mt4", "mt5"):
        if account.extra_metadata and isinstance(account.extra_metadata, dict):
            if account.extra_metadata.get("metaapi_account_id"):
                credentials["metaapi_account_id"] = account.extra_metadata["metaapi_account_id"]
            if account.extra_metadata.get("server"):
                credentials["server"] = account.extra_metadata["server"]

    return credentials


async def _create_account_executor(account: TradingAccount, db: Session):
    """
    Create broker executor for account with proper credentials and initialization.

    Args:
        account: TradingAccount model
        db: Database session

    Returns:
        (executor, needs_cleanup) tuple, or (None, False) if failed
    """
    try:
        from app.brokers.mt4_executor import MT4Executor
        from app.brokers.mt5_executor import MT5Executor
        from app.brokers.tradelocker_executor import TradeLockerExecutor
        from app.brokers.tradovate_executor import TradovateExecutor
        from app.brokers.projectx_executor import ProjectXExecutor
        from app.core.config import settings
        import asyncio

        credentials = _load_account_credentials(db, account)
        broker_type = account.broker.value
        executor = None
        needs_cleanup = True

        if broker_type == "tradelocker":
            if credentials.get("username") and credentials.get("password") and credentials.get("server"):
                # Normalize environment URL
                raw_env = credentials.get("sdk_environment") or credentials.get("environment", "https://demo.tradelocker.com")
                if raw_env and not raw_env.startswith("http"):
                    if raw_env.lower() in ("demo", "live"):
                        raw_env = f"https://{raw_env.lower()}.tradelocker.com"
                    else:
                        raw_env = f"https://{raw_env}.tradelocker.com"

                executor = TradeLockerExecutor(
                    username=credentials.get("username"),
                    password=credentials.get("password"),
                    server=credentials.get("server"),
                    sdk_environment=raw_env,
                    account_id=credentials.get("broker_account_id"),
                    account_num=credentials.get("account_num"),
                    user_id=account.user_id,
                )

        elif broker_type == "tradovate":
            if credentials.get("access_token"):
                executor = TradovateExecutor(
                    account_id=account.id,
                    access_token=credentials.get("access_token"),
                    environment=credentials.get("environment") or account.oauth_environment or "demo"
                )

        elif broker_type in ("projectx", "topstep"):
            if credentials.get("username") and credentials.get("api_key"):
                broker_account_id = account.default_broker_account_id or account.account_number or str(account.id)
                account_name = account.account_name or broker_account_id
                executor = ProjectXExecutor(
                    account_id=broker_account_id,
                    account_name=account_name,
                    username=credentials.get("username"),
                    api_key=credentials.get("api_key")
                )

        elif broker_type == "mt4":
            metaapi_account_id = credentials.get("metaapi_account_id")
            metaapi_token = credentials.get("metaapi_token") or credentials.get("api_token") or settings.METAAPI_TOKEN
            if metaapi_account_id and metaapi_token:
                executor = MT4Executor(
                    metaapi_token=metaapi_token,
                    metaapi_account_id=metaapi_account_id,
                )
            else:
                logger.warning(f"MT4 account {account.id} missing credentials")

        elif broker_type == "mt5":
            metaapi_account_id = credentials.get("metaapi_account_id")
            metaapi_token = credentials.get("metaapi_token") or credentials.get("api_token") or settings.METAAPI_TOKEN
            if metaapi_account_id and metaapi_token:
                executor = MT5Executor(
                    metaapi_token=metaapi_token,
                    metaapi_account_id=metaapi_account_id,
                )
            else:
                logger.warning(f"MT5 account {account.id} missing credentials")

        else:
            logger.warning(f"Unknown broker type: {broker_type}")
            return None, False

        # Initialize the executor if created
        if executor:
            try:
                await asyncio.wait_for(executor.initialize(), timeout=15.0)
                if not executor.is_connected:
                    logger.warning(f"Executor for {broker_type} initialized but not connected")
            except asyncio.TimeoutError:
                logger.warning(f"Executor initialization for {broker_type} timed out")
            except Exception as e:
                logger.warning(f"Executor initialization for {broker_type} failed: {e}")

        return executor, needs_cleanup

    except Exception as e:
        logger.error(f"Failed to create executor for account {account.id}: {e}")
        return None, False


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
    import asyncio

    # Run async sync in event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_sync_account_equity_async(account_id))


async def _sync_account_equity_async(account_id: int) -> Dict[str, Any]:
    """Async implementation of account equity sync"""
    executor = None
    needs_cleanup = False

    try:
        with get_db_session() as db:
            # Get account
            account = db.query(TradingAccount).filter(TradingAccount.id == account_id).first()
            if not account:
                return {"success": False, "error": f"Account {account_id} not found"}

            if not account.is_active:
                return {"success": False, "error": "Account is inactive"}

            # Create executor
            executor, needs_cleanup = await _create_account_executor(account, db)
            if not executor:
                return {"success": False, "error": "Failed to create broker executor"}

            # Fetch account info from broker
            try:
                # Use broker_account_id if available, otherwise account_number
                broker_account_id = account.default_broker_account_id or account.account_number or str(account.id)

                # Try with account_id first, then without
                try:
                    account_info = await executor.get_account_info(broker_account_id)
                except TypeError:
                    account_info = await executor.get_account_info()

                if not account_info:
                    return {"success": False, "error": "Failed to fetch account info from broker"}

                # Extract balance/equity - handle both dict and pydantic model
                balance = 0.0
                equity = 0.0

                if isinstance(account_info, dict):
                    balance = float(account_info.get('balance', 0) or 0)
                    equity = float(account_info.get('equity', 0) or account_info.get('accountEquity', 0) or 0)
                else:
                    balance = float(getattr(account_info, 'balance', 0) or 0)
                    equity = float(getattr(account_info, 'equity', 0) or getattr(account_info, 'accountEquity', 0) or 0)

                # Update account record
                account.balance = balance
                account.equity = equity
                account.last_sync = datetime.utcnow()
                db.commit()

            except Exception as e:
                logger.error(f"Failed to fetch account info for {account_id}: {e}")
                return {"success": False, "error": str(e)}
            finally:
                # Cleanup executor if needed
                if needs_cleanup and executor:
                    try:
                        await executor.disconnect()
                    except Exception:
                        pass

            # Initialize risk tracking services
            pnl_repo = DailyPnLRepository(db)
            pnl_service = DailyPnLService(pnl_repo)

            drawdown_repo = EquityHistoryRepository(db)
            drawdown_service = DrawdownService(drawdown_repo)

            hooks = RiskTrackingHooks(
                daily_pnl_service=pnl_service,
                drawdown_service=drawdown_service
            )

            # Update P&L and equity tracking
            await hooks.on_equity_update(
                account_id=account_id,
                equity=equity,
                balance=balance,
                unrealized_pnl=(equity - balance)
            )

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


@celery_app.task(name="trading_tasks.sync_all_accounts")
def sync_all_accounts() -> Dict[str, Any]:
    """
    Sync equity/balance for all active accounts.

    Called periodically by Celery Beat (every 5 minutes recommended).

    Returns:
        Summary of sync results
    """
    try:
        with get_db_session() as db:
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


@celery_app.task(name="trading_tasks.reset_daily_counters")
def reset_daily_counters() -> Dict[str, Any]:
    """
    Reset daily trading counters and clear halt flags at session boundary.

    Runs at 6:01 PM EST (prop firm trading day boundary).
    - Logs end-of-session P&L summaries for all accounts
    - Clears is_trading_halted flags so accounts recover for the next session
    - Pre-creates next-day DailyPnL records using current balance as starting_balance

    Returns:
        Reset summary
    """
    from app.models.database_models import DailyPnL

    today = date_type.today()
    tomorrow = today + timedelta(days=1)
    now = datetime.utcnow()

    results = {
        "total": 0,
        "halts_cleared": 0,
        "next_day_records_created": 0,
        "failed": 0,
        "errors": []
    }

    try:
        with get_db_session() as db:
            accounts = db.query(TradingAccount).filter(
                TradingAccount.is_active == True
            ).all()

            results["total"] = len(accounts)
            logger.info(f"Daily reset: processing {len(accounts)} active accounts for session boundary at {now} UTC")

            for account in accounts:
                try:
                    # Get today's DailyPnL record
                    today_pnl = db.query(DailyPnL).filter(
                        DailyPnL.account_id == account.id,
                        DailyPnL.date == today
                    ).first()

                    if today_pnl:
                        # Log end-of-session summary
                        logger.info(
                            f"Session end - account {account.id} ({account.name}): "
                            f"P&L={today_pnl.total_pnl:.2f} ({today_pnl.pnl_percent:.2f}%), "
                            f"trades={today_pnl.trades_count}, "
                            f"halted={today_pnl.is_trading_halted}"
                        )

                        # Clear halt flag so account can trade in next session
                        if today_pnl.is_trading_halted:
                            today_pnl.is_trading_halted = False
                            today_pnl.halt_reason = None
                            results["halts_cleared"] += 1
                            logger.info(f"Cleared trading halt for account {account.id} at session boundary")

                        db.commit()

                        # Pre-create tomorrow's DailyPnL record with today's ending balance
                        current_balance = today_pnl.current_balance or today_pnl.starting_balance
                        existing_tomorrow = db.query(DailyPnL).filter(
                            DailyPnL.account_id == account.id,
                            DailyPnL.date == tomorrow
                        ).first()

                        if not existing_tomorrow and current_balance and current_balance > 0:
                            new_record = DailyPnL(
                                account_id=account.id,
                                date=tomorrow,
                                starting_balance=current_balance,
                                current_balance=current_balance,
                                realized_pnl=0.0,
                                unrealized_pnl=0.0,
                                total_pnl=0.0,
                                pnl_percent=0.0,
                                trades_count=0,
                                winning_trades=0,
                                losing_trades=0,
                                is_trading_halted=False
                            )
                            db.add(new_record)
                            db.commit()
                            results["next_day_records_created"] += 1
                            logger.info(
                                f"Pre-created tomorrow's P&L record for account {account.id}, "
                                f"starting balance: {current_balance:.2f}"
                            )
                    else:
                        logger.debug(f"No DailyPnL record found for account {account.id} on {today}")

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"account_id": account.id, "error": str(e)})
                    logger.error(f"Error during daily reset for account {account.id}: {e}", exc_info=True)
                    try:
                        db.rollback()
                    except Exception:
                        pass

            logger.info(
                f"Daily reset complete: {results['halts_cleared']} halts cleared, "
                f"{results['next_day_records_created']} next-day records created, "
                f"{results['failed']} failed"
            )
            return results

    except Exception as e:
        logger.error(f"Error in reset_daily_counters: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


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
