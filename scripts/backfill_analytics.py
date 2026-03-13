#!/usr/bin/env python3
"""
Backfill analytics data from existing execution_logs.
This creates TradeJournal entries and updates TimeBasedStats for historical data.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.models import ExecutionLog
from app.models.database_models import TradeJournal, TimeBasedStats
from app.services.trade_analytics_service import TradeAnalyticsService

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trading_user:trading_password@localhost:5432/trading_db")

def backfill_analytics():
    """Create analytics entries from existing execution logs."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        analytics_service = TradeAnalyticsService(db)

        # Get all CLOSE actions with P&L that don't have journal entries
        print("Fetching CLOSE executions with P&L...")
        close_logs = db.query(ExecutionLog).filter(
            ExecutionLog.action == 'CLOSE',
            ExecutionLog.pnl.isnot(None),
            ExecutionLog.status == 'success'
        ).order_by(ExecutionLog.created_at).all()

        print(f"Found {len(close_logs)} CLOSE executions with P&L")

        # Group by account to get user_id
        from app.models.database_models import TradingAccount

        created_count = 0
        skipped_count = 0

        for log in close_logs:
            try:
                # Get account to find user_id
                account = db.query(TradingAccount).filter(TradingAccount.id == log.account_id).first()
                if not account:
                    skipped_count += 1
                    continue

                user_id = account.user_id

                # Check if journal entry already exists for this execution
                existing = db.query(TradeJournal).filter(
                    TradeJournal.exit_execution_id == log.id
                ).first()
                if existing:
                    skipped_count += 1
                    continue

                # Create a closed journal entry directly
                entry_time = log.created_at or datetime.utcnow()
                entry_hour = entry_time.hour
                entry_day_of_week = entry_time.weekday()
                entry_session = analytics_service._get_trading_session(entry_time)

                # Determine side based on context (assume we're closing a long if no other info)
                side = 'buy'  # Default assumption

                journal_entry = TradeJournal(
                    user_id=user_id,
                    account_id=log.account_id,
                    trade_uuid=str(log.signal_id) if log.signal_id else f"backfill-{log.id}",
                    broker_trade_id=log.order_id,
                    symbol=log.symbol,
                    side=side,
                    quantity=float(log.volume) if log.volume else 1.0,
                    quantity_closed=float(log.volume) if log.volume else 1.0,
                    entry_price=float(log.entry_price) if log.entry_price else 0,
                    exit_price=float(log.exit_price) if log.exit_price else 0,
                    entry_time=entry_time,
                    exit_time=log.closed_at or entry_time,
                    entry_execution_id=None,
                    exit_execution_id=log.id,
                    gross_pnl=float(log.pnl) if log.pnl else 0,
                    net_pnl=float(log.pnl) if log.pnl else 0,
                    commission=0,
                    swap=0,
                    status='closed',
                    entry_hour=entry_hour,
                    entry_day_of_week=entry_day_of_week,
                    entry_session=entry_session,
                    exit_reason='signal'
                )
                db.add(journal_entry)
                db.commit()
                db.refresh(journal_entry)

                # Update time-based stats
                analytics_service._update_time_based_stats(journal_entry)
                analytics_service._update_strategy_performance(journal_entry)
                analytics_service._update_equity_curve(journal_entry)

                created_count += 1
                if created_count % 50 == 0:
                    print(f"Created {created_count} journal entries...")

            except Exception as e:
                db.rollback()
                print(f"Error processing log {log.id}: {e}")
                skipped_count += 1
                continue

        print(f"\nBackfill complete!")
        print(f"Created: {created_count} journal entries")
        print(f"Skipped: {skipped_count}")

        # Show final stats
        journal_count = db.query(TradeJournal).count()
        time_stats_count = db.query(TimeBasedStats).count()
        print(f"\nTotal TradeJournal entries: {journal_count}")
        print(f"Total TimeBasedStats entries: {time_stats_count}")

    except Exception as e:
        print(f"Backfill failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting analytics backfill...")
    backfill_analytics()
