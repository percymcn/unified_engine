"""add_strategy_registry_tables

Revision ID: 043
Revises: 042
Create Date: 2026-03-14

Phase 6A: Strategy Registry tables for SmartFlow variant generation and evaluation.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '043'
down_revision = '042'
branch_labels = None
depends_on = None


def upgrade():
    # Create smartflow_strategies table
    op.create_table(
        'smartflow_strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('strategy_type', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),

        # Configuration
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('parent_strategy_id', sa.String(), nullable=True),
        sa.Column('parameter_changes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('hypothesis', sa.Text(), nullable=True),

        # Performance metrics
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('total_return_pct', sa.Float(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('backtest_days', sa.Integer(), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),

        # Evaluation tracking
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latest_evaluation_id', sa.Integer(), nullable=True),
        sa.Column('latest_comparison_id', sa.String(), nullable=True),

        # Approval tracking
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),

        # Rejection tracking
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by', sa.String(), nullable=True),
        sa.Column('rejection_notes', sa.Text(), nullable=True),

        # Retirement tracking
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retired_by', sa.String(), nullable=True),
        sa.Column('retirement_reason', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for smartflow_strategies
    op.create_index('ix_smartflow_strategies_strategy_id', 'smartflow_strategies', ['strategy_id'], unique=True)
    op.create_index('ix_smartflow_strategies_strategy_type', 'smartflow_strategies', ['strategy_type'])
    op.create_index('ix_smartflow_strategies_status', 'smartflow_strategies', ['status'])

    # Create strategy_evaluations table
    op.create_table(
        'strategy_evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('comparison_id', sa.String(), nullable=False),

        # Evaluation configuration
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('backtest_days', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.String(), nullable=True),
        sa.Column('end_date', sa.String(), nullable=True),

        # Performance results
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('total_return_pct', sa.Float(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('net_profit', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),

        # Evaluation criteria
        sa.Column('criteria_checked', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('criteria_results', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('recommendation', sa.String(), nullable=False),

        # Metadata
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('evaluated_by', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['smartflow_strategies.strategy_id'])
    )

    # Create strategy_candidates table
    op.create_table(
        'strategy_candidates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('parent_strategy_id', sa.String(), nullable=False),

        # Generation metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),

        # Limits enforcement
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['smartflow_strategies.strategy_id']),
        sa.UniqueConstraint('strategy_id')
    )


def downgrade():
    op.drop_table('strategy_candidates')
    op.drop_table('strategy_evaluations')
    op.drop_index('ix_smartflow_strategies_status', table_name='smartflow_strategies')
    op.drop_index('ix_smartflow_strategies_strategy_type', table_name='smartflow_strategies')
    op.drop_index('ix_smartflow_strategies_strategy_id', table_name='smartflow_strategies')
    op.drop_table('smartflow_strategies')
