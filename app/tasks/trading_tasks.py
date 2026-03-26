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
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

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
    Reconcile open positions in database with actual broker positions.
    Marks trades as closed if they no longer exist on the broker side.

    This handles:
    - Stop-outs
    - Manual closes
    - TP/SL hits
    - Broker-side position closures

    Returns:
        Sync summary with reconciliation stats
    """
    try:
        with get_db_session() as db:
            from app.models.database_models import TradeJournal, TradingAccount
            from app.brokers.mt5_executor import MT5Executor
            from app.brokers.mt4_executor import MT4Executor
            from app.brokers.tradelocker_executor import TradeLockerExecutor
            from app.brokers.projectx_executor import ProjectXExecutor
            from datetime import datetime, timedelta

            # Get all open positions from last 30 days (ignore older ones)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            open_trades = db.query(TradeJournal).filter(
                TradeJournal.status == "open",
                TradeJournal.created_at >= cutoff_date
            ).all()

            logger.info(f"Reconciling {len(open_trades)} open positions")

            results = {
                "total_checked": len(open_trades),
                "still_open": 0,
                "marked_closed": 0,
                "errors": 0,
                "details": []
            }

            # Group trades by account for efficient broker queries
            trades_by_account = defaultdict(list)
            for trade in open_trades:
                trades_by_account[trade.account_id].append(trade)

            for account_id, trades in trades_by_account.items():
                try:
                    account = db.query(TradingAccount).filter(
                        TradingAccount.id == account_id
                    ).first()

                    if not account or not account.is_active:
                        continue

                    # Load credentials and create executor
                    credentials = _load_account_credentials(db, account)
                    if not credentials:
                        logger.warning(f"No credentials for account {account_id}")
                        continue

                    # Create appropriate executor
                    executor = None
                    try:
                        if account.broker.value == "mt5":
                            executor = MT5Executor(credentials)
                        elif account.broker.value == "mt4":
                            executor = MT4Executor(credentials)
                        elif account.broker.value == "tradelocker":
                            executor = TradeLockerExecutor(credentials)
                        elif account.broker.value == "projectx":
                            executor = ProjectXExecutor(credentials)
                        else:
                            continue

                        # Get current open positions from broker
                        import asyncio
                        broker_positions = asyncio.run(executor.get_positions())

                        # Create lookup of broker position IDs
                        broker_position_ids = {
                            str(pos.get("id", pos.get("positionId", pos.get("ticket", ""))))
                            for pos in broker_positions
                        }

                        # Check each trade
                        for trade in trades:
                            position_id = str(trade.broker_trade_id or "")

                            # If position not found on broker, mark as closed
                            if position_id and position_id not in broker_position_ids:
                                trade.status = "closed"
                                trade.exit_time = datetime.utcnow()
                                trade.exit_reason = "auto_reconciled"

                                # Set exit price to entry if we don't have it (unknown P&L)
                                if not trade.exit_price:
                                    trade.exit_price = trade.entry_price
                                    trade.net_pnl = 0.0
                                    trade.gross_pnl = 0.0

                                results["marked_closed"] += 1
                                results["details"].append({
                                    "trade_id": trade.id,
                                    "symbol": trade.symbol,
                                    "account": account_id,
                                    "reason": "not_found_on_broker"
                                })

                                logger.info(f"Marked trade {trade.id} ({trade.symbol}) as closed - not found on broker")
                            else:
                                results["still_open"] += 1

                        db.commit()

                    finally:
                        if executor:
                            try:
                                asyncio.run(executor.disconnect())
                            except:
                                pass

                except Exception as e:
                    results["errors"] += 1
                    logger.error(f"Error reconciling account {account_id}: {e}", exc_info=True)

            logger.info(f"Position reconciliation complete: {results['marked_closed']} closed, {results['still_open']} still open")

            return results

    except Exception as e:
        logger.error(f"Error in sync_positions: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(name="trading_tasks.update_smartflow_outcomes")
def update_smartflow_outcomes() -> Dict[str, Any]:
    """
    Track SmartFlow signal outcomes and update ML analytics.

    Checks closed trades from the last 24 hours and links them to SmartFlow signals.
    Updates ML metrics and analytics for continuous improvement.

    Returns:
        Update summary with outcome tracking stats
    """
    try:
        with get_db_session() as db:
            from app.models.database_models import TradeJournal
            from app.models.smartflow_models import SmartFlowSignalLog, SmartFlowSignalOutcome
            from datetime import datetime, timedelta

            # Get recently closed trades (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            closed_trades = db.query(TradeJournal).filter(
                TradeJournal.status == "closed",
                TradeJournal.exit_time.isnot(None),
                TradeJournal.exit_time >= cutoff_time
            ).all()

            logger.info(f"Checking {len(closed_trades)} recently closed trades for SmartFlow outcome tracking")

            results = {
                "total_trades_checked": len(closed_trades),
                "outcomes_created": 0,
                "outcomes_updated": 0,
                "signals_matched": 0,
                "errors": 0
            }

            for trade in closed_trades:
                try:
                    # Look for matching SmartFlow signal within 5 minutes of trade entry
                    signal_window_start = trade.entry_time - timedelta(minutes=5)
                    signal_window_end = trade.entry_time + timedelta(minutes=5)

                    # Try to find matching signal by symbol and time
                    matching_signal = db.query(SmartFlowSignalLog).filter(
                        SmartFlowSignalLog.ticker == trade.symbol,
                        SmartFlowSignalLog.created_at >= signal_window_start,
                        SmartFlowSignalLog.created_at <= signal_window_end
                    ).order_by(
                        func.abs(
                            func.extract('epoch', SmartFlowSignalLog.created_at) -
                            func.extract('epoch', trade.entry_time)
                        )
                    ).first()

                    if not matching_signal:
                        continue

                    results["signals_matched"] += 1

                    # Check if outcome already exists
                    existing_outcome = db.query(SmartFlowSignalOutcome).filter(
                        SmartFlowSignalOutcome.signal_log_id == matching_signal.id
                    ).first()

                    # Calculate metrics
                    pnl = trade.net_pnl or trade.gross_pnl or 0.0
                    is_winner = pnl > 0
                    pnl_percent = None

                    if trade.entry_price and trade.exit_price and trade.entry_price != 0:
                        if trade.side == "buy":
                            pnl_percent = ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100
                        elif trade.side == "sell":
                            pnl_percent = ((trade.entry_price - trade.exit_price) / trade.entry_price) * 100

                    time_in_trade = None
                    if trade.exit_time and trade.entry_time:
                        time_in_trade = int((trade.exit_time - trade.entry_time).total_seconds() / 60)  # minutes

                    # Create or update outcome
                    if existing_outcome:
                        # Update existing
                        existing_outcome.trade_executed = True
                        existing_outcome.entry_price = trade.entry_price
                        existing_outcome.exit_price = trade.exit_price
                        existing_outcome.pnl = pnl
                        existing_outcome.pnl_percent = pnl_percent
                        existing_outcome.is_winner = is_winner
                        existing_outcome.time_in_trade = time_in_trade
                        existing_outcome.updated_at = datetime.utcnow()

                        results["outcomes_updated"] += 1
                        logger.debug(f"Updated outcome for signal {matching_signal.id}: {trade.symbol} PnL=${pnl:.2f}")
                    else:
                        # Create new outcome
                        outcome = SmartFlowSignalOutcome(
                            signal_log_id=matching_signal.id,
                            trade_executed=True,
                            entry_price=trade.entry_price,
                            exit_price=trade.exit_price,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            is_winner=is_winner,
                            time_in_trade=time_in_trade,
                            hour_of_day=trade.entry_time.hour if trade.entry_time else None,
                            day_of_week=trade.entry_time.weekday() if trade.entry_time else None
                        )
                        db.add(outcome)

                        results["outcomes_created"] += 1
                        logger.debug(f"Created outcome for signal {matching_signal.id}: {trade.symbol} PnL=${pnl:.2f}")

                    db.commit()

                except Exception as e:
                    results["errors"] += 1
                    logger.error(f"Error processing trade {trade.id} for SmartFlow outcomes: {e}")
                    db.rollback()

            # Update ML metrics summary
            try:
                from app.models.smartflow_models import SmartFlowMLMetrics

                # Calculate win rate and performance metrics
                total_outcomes = db.query(SmartFlowSignalOutcome).filter(
                    SmartFlowSignalOutcome.trade_executed == True,
                    SmartFlowSignalOutcome.is_winner.isnot(None)
                ).count()

                winning_outcomes = db.query(SmartFlowSignalOutcome).filter(
                    SmartFlowSignalOutcome.trade_executed == True,
                    SmartFlowSignalOutcome.is_winner == True
                ).count()

                win_rate = (winning_outcomes / total_outcomes * 100) if total_outcomes > 0 else 0.0

                avg_winner = db.query(func.avg(SmartFlowSignalOutcome.pnl)).filter(
                    SmartFlowSignalOutcome.is_winner == True
                ).scalar() or 0.0

                avg_loser = db.query(func.avg(SmartFlowSignalOutcome.pnl)).filter(
                    SmartFlowSignalOutcome.is_winner == False
                ).scalar() or 0.0

                # Update or create ML metrics per ticker
                # Get breakdown by ticker from outcomes
                from sqlalchemy import distinct
                tickers = db.query(distinct(SmartFlowSignalLog.ticker)).all()
                tickers = [t[0] for t in tickers if t[0]]

                if not tickers:
                    tickers = ['SPY']  # Default if no signals yet

                today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                for ticker in tickers:
                    # Get ticker-specific metrics
                    ticker_outcomes = db.query(SmartFlowSignalOutcome).join(
                        SmartFlowSignalLog
                    ).filter(
                        SmartFlowSignalLog.ticker == ticker,
                        SmartFlowSignalOutcome.trade_executed == True
                    ).all()

                    ticker_total = len(ticker_outcomes)
                    ticker_winners = len([o for o in ticker_outcomes if o.is_winner])
                    ticker_losers = ticker_total - ticker_winners
                    ticker_win_rate = (ticker_winners / ticker_total * 100) if ticker_total > 0 else 0.0

                    # Calculate P&L
                    gross_profit = sum(o.pnl for o in ticker_outcomes if o.pnl and o.pnl > 0)
                    gross_loss = abs(sum(o.pnl for o in ticker_outcomes if o.pnl and o.pnl < 0))
                    net_pnl = gross_profit - gross_loss
                    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
                    expectancy = (net_pnl / ticker_total) if ticker_total > 0 else 0.0

                    # Check if record exists for today
                    existing = db.query(SmartFlowMLMetrics).filter(
                        SmartFlowMLMetrics.ticker == ticker,
                        SmartFlowMLMetrics.metric_date >= today
                    ).first()

                    if existing:
                        # Update existing
                        existing.signals_executed = ticker_total
                        existing.winners = ticker_winners
                        existing.losers = ticker_losers
                        existing.win_rate = ticker_win_rate
                        existing.gross_profit = gross_profit
                        existing.gross_loss = gross_loss
                        existing.net_pnl = net_pnl
                        existing.profit_factor = profit_factor
                        existing.expectancy = expectancy
                    else:
                        # Create new daily record
                        new_metrics = SmartFlowMLMetrics(
                            ticker=ticker,
                            metric_date=today,
                            signals_generated=ticker_total,
                            signals_executed=ticker_total,
                            winners=ticker_winners,
                            losers=ticker_losers,
                            win_rate=ticker_win_rate,
                            gross_profit=gross_profit,
                            gross_loss=gross_loss,
                            net_pnl=net_pnl,
                            profit_factor=profit_factor,
                            expectancy=expectancy
                        )
                        db.add(new_metrics)

                db.commit()

                logger.info(f"SmartFlow ML metrics updated: WinRate={win_rate:.1f}%, TotalSignals={total_outcomes}")

            except Exception as e:
                logger.error(f"Error updating ML metrics: {e}")

            logger.info(
                f"SmartFlow outcome tracking complete: "
                f"{results['outcomes_created']} created, {results['outcomes_updated']} updated, "
                f"{results['signals_matched']} signals matched"
            )

            return results

    except Exception as e:
        logger.error(f"Error in update_smartflow_outcomes: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


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


@celery_app.task(name="trading_tasks.capture_strategy_health_snapshots")
def capture_strategy_health_snapshots() -> Dict[str, Any]:
    """
    Capture health snapshots for all strategies in the registry.

    Compares current forward-test performance against baseline backtest metrics
    to detect drift and strategy degradation.

    Runs every 30 minutes.
    """
    try:
        with get_db_session() as db:
            from app.models.strategy_registry_models import (
                SmartFlowStrategy, StrategyHealthSnapshot
            )
            from app.services.strategy_registry.health import get_health_monitor

            health_monitor = get_health_monitor()

            # Get all active strategies
            strategies = db.query(SmartFlowStrategy).filter(
                SmartFlowStrategy.status.in_(['approved', 'built_in'])
            ).all()

            results = {
                "strategies_checked": 0,
                "snapshots_created": 0,
                "errors": 0
            }

            for strategy in strategies:
                try:
                    # Calculate health score
                    health = health_monitor.calculate_health_score(strategy.strategy_id)

                    if health:
                        # Create snapshot
                        snapshot = StrategyHealthSnapshot(
                            strategy_id=strategy.strategy_id,
                            health_score=health.score,
                            health_status=health.status.value,
                            sharpe_drift_pct=health.drift_metrics.sharpe_drift_pct,
                            win_rate_drift_pct=health.drift_metrics.win_rate_drift_pct,
                            drawdown_drift_pct=health.drift_metrics.drawdown_drift_pct,
                            notes="; ".join(health.notes) if health.notes else None
                        )
                        db.add(snapshot)
                        results["snapshots_created"] += 1

                    results["strategies_checked"] += 1

                except Exception as e:
                    results["errors"] += 1
                    logger.error(f"Error capturing health for {strategy.strategy_id}: {e}")

            db.commit()
            logger.info(
                f"Strategy health snapshots: {results['snapshots_created']} created "
                f"for {results['strategies_checked']} strategies"
            )

            return results

    except Exception as e:
        logger.error(f"Error in capture_strategy_health_snapshots: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="trading_tasks.capture_forward_test_snapshots")
def capture_forward_test_snapshots() -> Dict[str, Any]:
    """
    Capture forward test performance snapshots for strategy registry.

    Saves current forward test metrics to DB so Strategy Registry UI
    can display live forward test data.

    Runs every 5 minutes.
    """
    try:
        from app.services.forward_test import get_forward_tester

        tester = get_forward_tester()
        stats = tester.get_status()

        if not stats.get('active'):
            logger.debug("Forward test not active, skipping snapshot")
            return {"success": True, "message": "Forward test not active"}

        # Save snapshot for pyramid_dynamic_v1 (what forward test uses)
        success = tester.save_snapshot_to_registry("pyramid_dynamic_v1")

        if success:
            logger.info(
                f"Forward test snapshot saved: trades={stats.get('total_trades', 0)}, "
                f"win_rate={stats.get('win_rate', 0):.1f}%"
            )
            return {
                "success": True,
                "total_trades": stats.get('total_trades', 0),
                "win_rate": stats.get('win_rate', 0),
                "total_pnl": stats.get('total_pnl', 0)
            }
        else:
            return {"success": False, "error": "Failed to save snapshot"}

    except Exception as e:
        logger.error(f"Error in capture_forward_test_snapshots: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="trading_tasks.capture_portfolio_risk_snapshot")
def capture_portfolio_risk_snapshot() -> Dict[str, Any]:
    """
    Capture portfolio-level risk metrics snapshot.

    Aggregates risk across all active strategies and calculates:
    - Portfolio VaR
    - Total exposure
    - Correlation risk
    - Drawdown status

    Runs every hour.
    """
    try:
        with get_db_session() as db:
            from app.models.strategy_registry_models import (
                SmartFlowStrategy, PortfolioRiskSnapshot
            )
            from app.services.strategy_registry.portfolio_risk import get_portfolio_risk_engine

            risk_engine = get_portfolio_risk_engine(db)

            # Get active strategies
            active_strategies = db.query(SmartFlowStrategy).filter(
                SmartFlowStrategy.status.in_(['approved', 'built_in']),
                SmartFlowStrategy.is_paused == False
            ).all()

            strategy_ids = [s.strategy_id for s in active_strategies]

            if not strategy_ids:
                logger.info("No active strategies for portfolio risk snapshot")
                return {"success": True, "strategies": 0}

            # Calculate portfolio risk
            portfolio_metrics = risk_engine.calculate_portfolio_risk(strategy_ids)

            # Create snapshot
            snapshot = PortfolioRiskSnapshot(
                total_strategies=len(strategy_ids),
                active_strategies=len(strategy_ids),
                total_allocation_pct=100.0,  # Default to 100% allocation
                portfolio_var=portfolio_metrics.portfolio_var if portfolio_metrics else 0.0,
                current_leverage=portfolio_metrics.current_leverage if portfolio_metrics else 1.0,
                current_drawdown_pct=portfolio_metrics.current_drawdown_pct if portfolio_metrics else 0.0,
                risk_budget_used=portfolio_metrics.risk_budget_used if portfolio_metrics else 0.0,
                is_halted=portfolio_metrics.has_risk_breach if portfolio_metrics else False,
                halt_reason=portfolio_metrics.breach_reason if portfolio_metrics and portfolio_metrics.has_risk_breach else None
            )
            db.add(snapshot)
            db.commit()

            logger.info(
                f"Portfolio risk snapshot: {len(strategy_ids)} strategies, "
                f"VaR={snapshot.portfolio_var:.2f}, DD={snapshot.current_drawdown_pct:.1f}%"
            )

            return {
                "success": True,
                "strategies": len(strategy_ids),
                "var": snapshot.portfolio_var,
                "drawdown_pct": snapshot.current_drawdown_pct
            }

    except Exception as e:
        logger.error(f"Error in capture_portfolio_risk_snapshot: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
