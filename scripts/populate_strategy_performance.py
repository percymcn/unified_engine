#!/usr/bin/env python3
"""
Populate strategy_performance table from trade_journal entries.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database_models import TradeJournal, StrategyPerformance
from app.services.trade_analytics_service import TradeAnalyticsService

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trading_user:trading_password@postgres:5432/trading_db")

def populate_strategy_performance():
    """Populate strategy performance from trade journal."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        analytics_service = TradeAnalyticsService(db)

        # Get distinct strategies per user
        strategies = db.query(
            TradeJournal.user_id,
            TradeJournal.strategy_name
        ).filter(
            TradeJournal.strategy_name.isnot(None),
            TradeJournal.status == 'closed'
        ).distinct().all()

        print(f"Found {len(strategies)} unique user/strategy combinations")

        for user_id, strategy_name in strategies:
            try:
                # Get or create strategy performance record
                perf = db.query(StrategyPerformance).filter(
                    StrategyPerformance.user_id == user_id,
                    StrategyPerformance.strategy_name == strategy_name,
                    StrategyPerformance.period_type == 'all_time'
                ).first()

                if not perf:
                    perf = StrategyPerformance(
                        user_id=user_id,
                        strategy_name=strategy_name,
                        period_type='all_time'
                    )
                    db.add(perf)

                # Calculate metrics
                metrics = analytics_service.calculate_performance_metrics(
                    user_id=user_id,
                    strategy_name=strategy_name
                )

                # Update record
                perf.total_trades = metrics['total_trades']
                perf.winning_trades = metrics['winning_trades']
                perf.losing_trades = metrics['losing_trades']
                perf.breakeven_trades = metrics['breakeven_trades']
                perf.win_rate = metrics['win_rate']
                perf.avg_win = metrics['avg_win']
                perf.avg_loss = metrics['avg_loss']
                perf.largest_win = metrics['largest_win']
                perf.largest_loss = metrics['largest_loss']
                perf.gross_profit = metrics['gross_profit']
                perf.gross_loss = metrics['gross_loss']
                perf.net_profit = metrics['net_profit']
                perf.total_commission = metrics.get('total_commission', 0)
                perf.profit_factor = metrics['profit_factor']
                perf.expectancy = metrics['expectancy']
                perf.max_consecutive_wins = metrics['max_consecutive_wins']
                perf.max_consecutive_losses = metrics['max_consecutive_losses']
                perf.current_streak = metrics['current_streak']
                perf.max_drawdown = metrics['max_drawdown']
                perf.max_drawdown_pct = metrics['max_drawdown_pct']
                perf.avg_holding_time_seconds = metrics.get('avg_holding_time_seconds')
                perf.best_hour = metrics.get('best_hour')
                perf.best_day = metrics.get('best_day')
                perf.best_session = metrics.get('best_session')
                perf.sharpe_ratio = metrics.get('sharpe_ratio')
                perf.is_active = True

                db.commit()
                print(f"  Updated {strategy_name}: {metrics['total_trades']} trades, {metrics['win_rate']:.1f}% win rate, ${metrics['net_profit']:.2f} P&L")

            except Exception as e:
                db.rollback()
                print(f"  Error processing {strategy_name}: {e}")
                continue

        # Show final counts
        perf_count = db.query(StrategyPerformance).filter(
            StrategyPerformance.period_type == 'all_time'
        ).count()
        print(f"\nTotal strategy performance records: {perf_count}")

    except Exception as e:
        print(f"Failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Populating strategy performance...\n")
    populate_strategy_performance()
