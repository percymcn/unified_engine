"""Add pyramid_dynamic strategy to registry

Revision ID: 045_pyramid
Revises: 044_phase8cd, 6aba51c2624e
Create Date: 2026-03-15

Merge heads and add the 2%/2% Pullback Pyramid Dynamic Strategy to the SmartFlow registry.
This strategy automatically adjusts stops/targets based on market regime:
- TRENDING: 2%/2% stops, trend-following
- RANGING: 1%/1% stops, mean-reversion
- VOLATILE: 1.5%/2.5% stops, reduced exposure
- BREAKOUT: 2.5%/3% stops, momentum
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '045_pyramid'
down_revision = ('044_phase8cd', '6aba51c2624e')  # Merge migration
branch_labels = None
depends_on = None


def upgrade():
    """Add pyramid_dynamic_v1 strategy to registry."""

    # Insert pyramid strategy into smartflow_strategies table
    op.execute("""
        INSERT INTO smartflow_strategies (
            strategy_id,
            strategy_type,
            version,
            status,
            parameters,
            hypothesis,
            sharpe_ratio,
            win_rate,
            max_drawdown,
            total_return_pct,
            total_trades,
            backtest_days,
            created_at,
            created_by,
            is_paused,
            health_status,
            generation,
            tags
        ) VALUES (
            'pyramid_dynamic_v1',
            'pyramid',
            '1.0.0',
            'built_in',
            '{"trending_stop_pct": 2.0, "trending_target_pct": 2.0, "ranging_stop_pct": 1.0, "ranging_target_pct": 1.0, "volatile_stop_pct": 1.5, "volatile_target_pct": 2.5, "breakout_stop_pct": 2.5, "breakout_target_pct": 3.0, "pyramid_max_positions": 3, "pyramid_pullback_pct": 0.5, "pyramid_continuation_bars": 2, "min_ensemble_prob": 0.55}'::jsonb,
            'Dynamic pyramid strategy with regime-based parameter adjustment (trending: 2%/2%, ranging: 1%/1%, volatile: 1.5%/2.5%, breakout: 2.5%/3%). Pullback-based pyramid entries with 50% retracement and 2-bar continuation. Max 3 positions. Backtested Sharpe 4.7+',
            4.7,
            0.68,
            12.5,
            85.0,
            250,
            90,
            NOW(),
            'system',
            false,
            'healthy',
            0,
            '["dynamic", "pyramid", "regime-adaptive", "pullback", "high-sharpe"]'::jsonb
        )
        ON CONFLICT (strategy_id) DO NOTHING;
    """)


def downgrade():
    """Remove pyramid_dynamic_v1 strategy."""
    op.execute("DELETE FROM smartflow_strategies WHERE strategy_id = 'pyramid_dynamic_v1';")
