"""Add portfolio_risk_snapshots table

Revision ID: 047_portfolio_risk
Revises: 046_health
Create Date: 2026-03-15

Phase 11: Portfolio Risk Engine
Adds table for storing portfolio-level risk snapshots.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = '047_portfolio_risk'
down_revision = '046_health'
branch_labels = None
depends_on = None


def upgrade():
    """Create portfolio_risk_snapshots table."""
    
    op.create_table(
        'portfolio_risk_snapshots',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        
        # Portfolio composition
        sa.Column('total_strategies', sa.Integer, nullable=False),
        sa.Column('active_strategies', sa.Integer, nullable=False),
        sa.Column('total_allocation_pct', sa.Float, nullable=False),
        
        # Risk metrics
        sa.Column('portfolio_var', sa.Float, nullable=True),
        sa.Column('portfolio_cvar', sa.Float, nullable=True),
        sa.Column('portfolio_volatility', sa.Float, nullable=True),
        sa.Column('portfolio_sharpe', sa.Float, nullable=True),
        
        # Drawdown
        sa.Column('current_drawdown_pct', sa.Float, default=0.0),
        sa.Column('max_drawdown_pct', sa.Float, default=0.0),
        
        # Leverage
        sa.Column('current_leverage', sa.Float, default=1.0),
        sa.Column('recommended_leverage', sa.Float, default=1.0),
        
        # Risk budget
        sa.Column('risk_budget_used', sa.Float, default=0.0),
        sa.Column('risk_budget_available', sa.Float, default=100.0),
        
        # Flags
        sa.Column('is_halted', sa.Boolean, default=False),
        sa.Column('halt_reason', sa.String, nullable=True),
        
        # Strategy contributions
        sa.Column('strategy_risks', JSON, nullable=True),
    )


def downgrade():
    """Drop portfolio_risk_snapshots table."""
    op.drop_table('portfolio_risk_snapshots')
