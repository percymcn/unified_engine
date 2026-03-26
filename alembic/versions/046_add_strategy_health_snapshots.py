"""Add strategy_health_snapshots table

Revision ID: 046_health
Revises: 045_pyramid
Create Date: 2026-03-15

Phase 10: Drift Detection + Strategy Health Scoring
Adds table for storing health evaluation snapshots over time.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = '046_health'
down_revision = '045_pyramid'
branch_labels = None
depends_on = None


def upgrade():
    """Create strategy_health_snapshots table."""
    
    op.create_table(
        'strategy_health_snapshots',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('strategy_id', sa.String, sa.ForeignKey('smartflow_strategies.strategy_id'), nullable=False, index=True),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        
        # Health score
        sa.Column('health_score', sa.Float, nullable=False),
        sa.Column('health_status', sa.String, nullable=False),  # healthy, degraded, critical, unknown
        
        # Drift metrics - Baseline
        sa.Column('baseline_sharpe', sa.Float, nullable=True),
        sa.Column('baseline_win_rate', sa.Float, nullable=True),
        sa.Column('baseline_max_dd', sa.Float, nullable=True),
        sa.Column('baseline_trades', sa.Integer, nullable=True),
        
        # Drift metrics - Current
        sa.Column('current_sharpe', sa.Float, nullable=True),
        sa.Column('current_win_rate', sa.Float, nullable=True),
        sa.Column('current_max_dd', sa.Float, nullable=True),
        sa.Column('current_trades', sa.Integer, nullable=True),
        
        # Drift percentages
        sa.Column('sharpe_drift_pct', sa.Float, nullable=True),
        sa.Column('win_rate_drift_pct', sa.Float, nullable=True),
        sa.Column('drawdown_drift_pct', sa.Float, nullable=True),
        
        # Flags
        sa.Column('sharpe_drifted', sa.Boolean, default=False),
        sa.Column('win_rate_drifted', sa.Boolean, default=False),
        sa.Column('drawdown_drifted', sa.Boolean, default=False),
        sa.Column('insufficient_trades', sa.Boolean, default=False),
        
        # Component scores
        sa.Column('health_factors', JSON, nullable=True),  # {"sharpe": 85, "win_rate": 90, "drawdown": 80}
        
        # Notes
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('auto_paused', sa.Boolean, default=False),
    )


def downgrade():
    """Drop strategy_health_snapshots table."""
    op.drop_table('strategy_health_snapshots')
