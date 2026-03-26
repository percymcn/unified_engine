"""Phase 8C-8D: Scale-prep + Operational Hardening

Revision ID: 044_phase8cd
Revises: 043
Create Date: 2026-03-14

Adds:
- Phase 8C: Canonical identity fields (family_id, variant_hash, generation, lineage_path)
- Phase 8C: Snapshot links (latest_backtest_snapshot_id, latest_forward_test_snapshot_id)
- Phase 8C: Tags (JSON array for filtering)
- Phase 8C: Snapshot tables (strategy_backtest_snapshots, strategy_forward_test_snapshots)
- Phase 8D: Operational fields (is_paused, paused_at, paused_by, pause_reason)
- Phase 8D: Health tracking (health_status, health_checked_at, health_notes)
- Phase 8D: Rollback/review (rollback_target_strategy_id, last_reviewed_at, last_reviewed_by)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '044_phase8cd'
down_revision = '043'
branch_labels = None
depends_on = None


def upgrade():
    # Phase 8C: Canonical Identity & Lineage
    op.add_column('smartflow_strategies', sa.Column('family_id', sa.String(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('variant_hash', sa.String(64), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('generation', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('smartflow_strategies', sa.Column('lineage_path', sa.String(), nullable=True))

    # Phase 8C: Snapshot Links
    op.add_column('smartflow_strategies', sa.Column('latest_backtest_snapshot_id', sa.Integer(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('latest_forward_test_snapshot_id', sa.Integer(), nullable=True))

    # Phase 8C: Tags
    op.add_column('smartflow_strategies', sa.Column('tags', sa.JSON(), nullable=True))

    # Phase 8D: Operational Hardening
    op.add_column('smartflow_strategies', sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_strategies', sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('paused_by', sa.String(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('pause_reason', sa.Text(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('health_status', sa.String(), nullable=False, server_default='healthy'))
    op.add_column('smartflow_strategies', sa.Column('health_checked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('health_notes', sa.Text(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('rollback_target_strategy_id', sa.String(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('last_reviewed_by', sa.String(), nullable=True))

    # Add indexes for Phase 8C
    op.create_index('ix_smartflow_strategies_family_id', 'smartflow_strategies', ['family_id'])
    op.create_index('ix_smartflow_strategies_variant_hash', 'smartflow_strategies', ['variant_hash'], unique=True)

    # Add indexes for Phase 8D
    op.create_index('ix_smartflow_strategies_is_paused', 'smartflow_strategies', ['is_paused'])
    op.create_index('ix_smartflow_strategies_health_status', 'smartflow_strategies', ['health_status'])

    # Phase 8C: Create backtest snapshot table
    op.create_table(
        'strategy_backtest_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('backtest_days', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.String(), nullable=True),
        sa.Column('end_date', sa.String(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('total_return_pct', sa.Float(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('net_profit', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('comparison_id', sa.String(), nullable=True),
        sa.Column('evaluation_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['strategy_id'], ['smartflow_strategies.strategy_id']),
        sa.ForeignKeyConstraint(['evaluation_id'], ['strategy_evaluations.id'])
    )
    op.create_index('ix_strategy_backtest_snapshots_strategy_id', 'strategy_backtest_snapshots', ['strategy_id'])
    op.create_index('ix_strategy_backtest_snapshots_snapshot_at', 'strategy_backtest_snapshots', ['snapshot_at'])

    # Phase 8C: Create forward-test snapshot table
    op.create_table(
        'strategy_forward_test_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=True),
        sa.Column('losing_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('total_pnl', sa.Float(), nullable=True),
        sa.Column('gate_status', sa.String(), nullable=True),
        sa.Column('gate_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gate_evaluated_by', sa.String(), nullable=True),
        sa.Column('gate_criteria_results', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['strategy_id'], ['smartflow_strategies.strategy_id'])
    )
    op.create_index('ix_strategy_forward_test_snapshots_strategy_id', 'strategy_forward_test_snapshots', ['strategy_id'])
    op.create_index('ix_strategy_forward_test_snapshots_snapshot_at', 'strategy_forward_test_snapshots', ['snapshot_at'])


def downgrade():
    # Drop snapshot tables
    op.drop_table('strategy_forward_test_snapshots')
    op.drop_table('strategy_backtest_snapshots')

    # Drop indexes
    op.drop_index('ix_smartflow_strategies_health_status', 'smartflow_strategies')
    op.drop_index('ix_smartflow_strategies_is_paused', 'smartflow_strategies')
    op.drop_index('ix_smartflow_strategies_variant_hash', 'smartflow_strategies')
    op.drop_index('ix_smartflow_strategies_family_id', 'smartflow_strategies')

    # Drop Phase 8D columns
    op.drop_column('smartflow_strategies', 'last_reviewed_by')
    op.drop_column('smartflow_strategies', 'last_reviewed_at')
    op.drop_column('smartflow_strategies', 'rollback_target_strategy_id')
    op.drop_column('smartflow_strategies', 'health_notes')
    op.drop_column('smartflow_strategies', 'health_checked_at')
    op.drop_column('smartflow_strategies', 'health_status')
    op.drop_column('smartflow_strategies', 'pause_reason')
    op.drop_column('smartflow_strategies', 'paused_by')
    op.drop_column('smartflow_strategies', 'paused_at')
    op.drop_column('smartflow_strategies', 'is_paused')

    # Drop Phase 8C columns
    op.drop_column('smartflow_strategies', 'tags')
    op.drop_column('smartflow_strategies', 'latest_forward_test_snapshot_id')
    op.drop_column('smartflow_strategies', 'latest_backtest_snapshot_id')
    op.drop_column('smartflow_strategies', 'lineage_path')
    op.drop_column('smartflow_strategies', 'generation')
    op.drop_column('smartflow_strategies', 'variant_hash')
    op.drop_column('smartflow_strategies', 'family_id')
