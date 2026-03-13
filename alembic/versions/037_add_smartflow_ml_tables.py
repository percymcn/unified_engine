"""Add SmartFlow ML tables for self-learning capabilities

Revision ID: 037
Revises: 036
Create Date: 2026-03-09

Tables:
- smartflow_signal_outcomes: Track P&L outcomes of signals
- smartflow_patterns: Store recognized flow patterns
- smartflow_model_state: ML model parameters and state
- smartflow_market_regimes: Detected market regimes
- smartflow_ml_metrics: Performance metrics over time
- smartflow_correlation_signals: Cross-ticker correlation events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = '037'
down_revision = '036'
branch_labels = None
depends_on = None


def upgrade():
    # Patterns - Recognized flow patterns with historical outcomes (CREATE FIRST for FK)
    op.create_table(
        'smartflow_patterns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),  # "bullish_sweep_cluster", "bearish_capitulation"
        sa.Column('description', sa.Text(), nullable=True),

        # Pattern definition
        sa.Column('pattern_features', JSON, nullable=False),  # Feature vector defining the pattern
        sa.Column('pattern_type', sa.String(50), nullable=False),  # sweep, block, split, multi_leg

        # Historical performance
        sa.Column('total_occurrences', sa.Integer(), default=0),
        sa.Column('win_count', sa.Integer(), default=0),
        sa.Column('loss_count', sa.Integer(), default=0),
        sa.Column('win_rate', sa.Float(), default=0.0),
        sa.Column('avg_pnl', sa.Float(), default=0.0),
        sa.Column('avg_pnl_winner', sa.Float(), default=0.0),
        sa.Column('avg_pnl_loser', sa.Float(), default=0.0),
        sa.Column('expectancy', sa.Float(), default=0.0),  # (win_rate * avg_win) - (loss_rate * avg_loss)
        sa.Column('profit_factor', sa.Float(), default=0.0),  # gross_profit / gross_loss

        # Confidence
        sa.Column('confidence_score', sa.Float(), default=50.0),  # 0-100
        sa.Column('sample_size_weight', sa.Float(), default=0.0),  # Higher with more samples

        # Best conditions
        sa.Column('best_hour', sa.Integer(), nullable=True),
        sa.Column('best_day', sa.Integer(), nullable=True),
        sa.Column('best_regime', sa.String(20), nullable=True),

        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_patterns_name', 'smartflow_patterns', ['name'])
    op.create_index('ix_patterns_win_rate', 'smartflow_patterns', ['win_rate'])
    op.create_index('ix_patterns_confidence', 'smartflow_patterns', ['confidence_score'])

    # Signal Outcomes - Track what happened after each signal (after patterns for FK)
    op.create_table(
        'smartflow_signal_outcomes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('signal_log_id', sa.Integer(), sa.ForeignKey('smartflow_signal_logs.id'), nullable=False),

        # Trade outcome
        sa.Column('trade_executed', sa.Boolean(), default=False, nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_percent', sa.Float(), nullable=True),
        sa.Column('is_winner', sa.Boolean(), nullable=True),

        # Timing
        sa.Column('time_to_target', sa.Integer(), nullable=True),
        sa.Column('time_in_trade', sa.Integer(), nullable=True),
        sa.Column('max_favorable_excursion', sa.Float(), nullable=True),
        sa.Column('max_adverse_excursion', sa.Float(), nullable=True),

        # Market context at signal
        sa.Column('market_regime', sa.String(20), nullable=True),
        sa.Column('vix_level', sa.Float(), nullable=True),
        sa.Column('spy_price', sa.Float(), nullable=True),
        sa.Column('hour_of_day', sa.Integer(), nullable=True),
        sa.Column('day_of_week', sa.Integer(), nullable=True),

        # Flow context
        sa.Column('flow_pattern', JSON, nullable=True),
        sa.Column('pattern_id', sa.Integer(), sa.ForeignKey('smartflow_patterns.id'), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_signal_outcomes_signal_log_id', 'smartflow_signal_outcomes', ['signal_log_id'])
    op.create_index('ix_signal_outcomes_is_winner', 'smartflow_signal_outcomes', ['is_winner'])
    op.create_index('ix_signal_outcomes_market_regime', 'smartflow_signal_outcomes', ['market_regime'])

    # Model State - ML model parameters and adaptive thresholds
    op.create_table(
        'smartflow_model_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticker', sa.String(10), nullable=False, unique=True),

        # Adaptive thresholds (learned from outcomes)
        sa.Column('optimal_buy_threshold', sa.Float(), default=4.0),
        sa.Column('optimal_sell_threshold', sa.Float(), default=-4.0),
        sa.Column('optimal_close_threshold', sa.Float(), default=1.0),

        # Confidence calibration
        sa.Column('fss_accuracy_by_range', JSON, nullable=True),  # {"0-2": 0.45, "2-4": 0.55, "4-6": 0.65, "6+": 0.75}
        sa.Column('confidence_multiplier', sa.Float(), default=1.0),  # Adjust confidence based on recent accuracy

        # Time-of-day optimization
        sa.Column('hourly_win_rates', JSON, nullable=True),  # {"9": 0.55, "10": 0.62, ...}
        sa.Column('best_trading_hours', JSON, nullable=True),  # [10, 11, 14, 15]
        sa.Column('avoid_hours', JSON, nullable=True),  # [12, 13] - lunch hours

        # Day-of-week optimization
        sa.Column('daily_win_rates', JSON, nullable=True),  # {"0": 0.52, "1": 0.58, ...} (0=Monday)
        sa.Column('best_trading_days', JSON, nullable=True),

        # Recent performance (rolling window)
        sa.Column('recent_win_rate', sa.Float(), default=0.5),  # Last 50 signals
        sa.Column('recent_expectancy', sa.Float(), default=0.0),
        sa.Column('recent_signals_count', sa.Integer(), default=0),

        # Model versioning
        sa.Column('model_version', sa.Integer(), default=1),
        sa.Column('last_trained_at', sa.DateTime(), nullable=True),
        sa.Column('training_samples', sa.Integer(), default=0),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_model_state_ticker', 'smartflow_model_state', ['ticker'])

    # Market Regimes - Track detected market conditions
    op.create_table(
        'smartflow_market_regimes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticker', sa.String(10), nullable=False, index=True),

        # Regime classification
        sa.Column('regime', sa.String(20), nullable=False),  # trending_up, trending_down, ranging, volatile, squeeze
        sa.Column('regime_confidence', sa.Float(), default=0.5),  # 0-1
        sa.Column('regime_strength', sa.Float(), default=0.5),  # 0-1, how strong is the trend/range

        # Regime indicators
        sa.Column('atr_percentile', sa.Float(), nullable=True),  # ATR vs historical (0-100)
        sa.Column('trend_strength', sa.Float(), nullable=True),  # ADX-like measurement
        sa.Column('vix_level', sa.Float(), nullable=True),
        sa.Column('volume_ratio', sa.Float(), nullable=True),  # vs 20-day avg

        # Recommendations
        sa.Column('recommended_action', sa.String(20), nullable=True),  # trade_normal, reduce_size, avoid_trades
        sa.Column('size_multiplier', sa.Float(), default=1.0),  # 0.5 = half size, 1.0 = normal, 1.5 = increase

        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), index=True),
    )
    op.create_index('ix_market_regimes_ticker_time', 'smartflow_market_regimes', ['ticker', 'timestamp'])

    # ML Metrics - Track learning progress over time
    op.create_table(
        'smartflow_ml_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticker', sa.String(10), nullable=False, index=True),
        sa.Column('metric_date', sa.Date(), nullable=False, index=True),

        # Daily performance
        sa.Column('signals_generated', sa.Integer(), default=0),
        sa.Column('signals_executed', sa.Integer(), default=0),
        sa.Column('winners', sa.Integer(), default=0),
        sa.Column('losers', sa.Integer(), default=0),
        sa.Column('win_rate', sa.Float(), default=0.0),

        # P&L metrics
        sa.Column('gross_profit', sa.Float(), default=0.0),
        sa.Column('gross_loss', sa.Float(), default=0.0),
        sa.Column('net_pnl', sa.Float(), default=0.0),
        sa.Column('profit_factor', sa.Float(), default=0.0),
        sa.Column('expectancy', sa.Float(), default=0.0),

        # ML-specific metrics
        sa.Column('model_confidence_avg', sa.Float(), default=0.0),  # Avg confidence of signals
        sa.Column('threshold_used', sa.Float(), default=4.0),  # What FSS threshold was used
        sa.Column('regime_accuracy', sa.Float(), default=0.0),  # Was regime detection correct
        sa.Column('pattern_matches', sa.Integer(), default=0),  # How many patterns were recognized

        # Improvement tracking
        sa.Column('baseline_win_rate', sa.Float(), default=0.5),  # Pre-ML baseline
        sa.Column('improvement_vs_baseline', sa.Float(), default=0.0),  # % improvement

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_ml_metrics_date', 'smartflow_ml_metrics', ['metric_date'])
    op.create_unique_constraint('uq_ml_metrics_ticker_date', 'smartflow_ml_metrics', ['ticker', 'metric_date'])

    # Correlation Signals - Cross-ticker agreement events
    op.create_table(
        'smartflow_correlation_signals',
        sa.Column('id', sa.Integer(), primary_key=True),

        # Signal details
        sa.Column('signal_type', sa.String(20), nullable=False),  # bullish_alignment, bearish_alignment
        sa.Column('direction', sa.String(10), nullable=False),  # buy, sell
        sa.Column('confidence', sa.Float(), nullable=False),  # 0-100

        # Participating tickers
        sa.Column('tickers_aligned', JSON, nullable=False),  # ["SPY", "QQQ", "IWM"]
        sa.Column('alignment_scores', JSON, nullable=False),  # {"SPY": 5.2, "QQQ": 4.8, "IWM": 4.1}
        sa.Column('total_tickers', sa.Integer(), nullable=False),

        # Composite score
        sa.Column('composite_fss', sa.Float(), nullable=False),  # Weighted average FSS
        sa.Column('conviction_level', sa.String(20), nullable=False),  # low, medium, high, extreme

        # Outcome tracking
        sa.Column('outcome_tracked', sa.Boolean(), default=False),
        sa.Column('was_profitable', sa.Boolean(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),

        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), index=True),
    )
    op.create_index('ix_correlation_signals_type', 'smartflow_correlation_signals', ['signal_type'])
    op.create_index('ix_correlation_signals_conviction', 'smartflow_correlation_signals', ['conviction_level'])

    # Add ML-related columns to smartflow_config
    op.add_column('smartflow_config', sa.Column('ml_enabled', sa.Boolean(), default=True, nullable=False, server_default='true'))
    op.add_column('smartflow_config', sa.Column('use_adaptive_thresholds', sa.Boolean(), default=True, nullable=False, server_default='true'))
    op.add_column('smartflow_config', sa.Column('use_regime_filter', sa.Boolean(), default=True, nullable=False, server_default='true'))
    op.add_column('smartflow_config', sa.Column('use_time_optimization', sa.Boolean(), default=True, nullable=False, server_default='true'))
    op.add_column('smartflow_config', sa.Column('use_pattern_recognition', sa.Boolean(), default=True, nullable=False, server_default='true'))
    op.add_column('smartflow_config', sa.Column('use_correlation_filter', sa.Boolean(), default=False, nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('min_correlation_tickers', sa.Integer(), default=2, nullable=False, server_default='2'))
    op.add_column('smartflow_config', sa.Column('ml_confidence_boost', sa.Float(), default=0.0, nullable=False, server_default='0.0'))


def downgrade():
    # Remove columns from smartflow_config
    op.drop_column('smartflow_config', 'ml_confidence_boost')
    op.drop_column('smartflow_config', 'min_correlation_tickers')
    op.drop_column('smartflow_config', 'use_correlation_filter')
    op.drop_column('smartflow_config', 'use_pattern_recognition')
    op.drop_column('smartflow_config', 'use_time_optimization')
    op.drop_column('smartflow_config', 'use_regime_filter')
    op.drop_column('smartflow_config', 'use_adaptive_thresholds')
    op.drop_column('smartflow_config', 'ml_enabled')

    # Drop tables
    op.drop_table('smartflow_correlation_signals')
    op.drop_table('smartflow_ml_metrics')
    op.drop_table('smartflow_market_regimes')
    op.drop_table('smartflow_model_state')
    op.drop_table('smartflow_patterns')
    op.drop_table('smartflow_signal_outcomes')
