"""Add signal intelligence tables

Revision ID: 018
Revises: 017
Create Date: 2026-01-22

Adds three tables for Signal Intelligence Layer:
- momentum_settings: User-level momentum guard configuration
- signal_counters: Per-session signal momentum tracking
- discard_bin: Discarded signals audit trail
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    # Create momentum_settings table
    op.create_table(
        'momentum_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('warn_at', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('auto_breakeven', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('pause_on_chop', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_exposure', sa.Numeric(precision=12, scale=2), nullable=False, server_default='5000.00'),
        sa.Column('auto_pause_on_exposure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allow_hedge', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('staleness_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('staleness_seconds', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('force_old_signals', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('discard_flush_interval', sa.String(10), nullable=False, server_default='24h'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_momentum_settings_user_id', 'momentum_settings', ['user_id'], unique=True)

    # Create signal_counters table
    op.create_table(
        'signal_counters',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_key', sa.String(255), nullable=False),
        sa.Column('current_bias', sa.String(10), nullable=False, server_default='none'),  # 'buy', 'sell', 'none'
        sa.Column('opposite_momentum', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_signal_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last8_pattern', sa.String(16), nullable=True),  # Compact string like 'BBSBSBSB'
        sa.Column('chop_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'session_key')
    )
    op.create_index('ix_signal_counters_user_id', 'signal_counters', ['user_id'])
    op.create_index('ix_signal_counters_session_key', 'signal_counters', ['session_key'])

    # Create discard_bin table
    op.create_table(
        'discard_bin',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),  # 'stale', 'momentum', 'exposure', etc.
        sa.Column('raw_signal_json', sa.JSON(), nullable=True),
        sa.Column('normalized_signal_json', sa.JSON(), nullable=True),
        sa.Column('age_ms', sa.Integer(), nullable=True),
        sa.Column('broker_target', sa.String(50), nullable=True),
        sa.Column('symbol', sa.String(50), nullable=True),
        sa.Column('side', sa.String(10), nullable=True),  # 'buy', 'sell'
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_discard_bin_user_id', 'discard_bin', ['user_id'])
    op.create_index('ix_discard_bin_received_at', 'discard_bin', ['received_at'])
    op.create_index('ix_discard_bin_reason', 'discard_bin', ['reason'])


def downgrade():
    op.drop_index('ix_discard_bin_reason', table_name='discard_bin')
    op.drop_index('ix_discard_bin_received_at', table_name='discard_bin')
    op.drop_index('ix_discard_bin_user_id', table_name='discard_bin')
    op.drop_table('discard_bin')
    
    op.drop_index('ix_signal_counters_session_key', table_name='signal_counters')
    op.drop_index('ix_signal_counters_user_id', table_name='signal_counters')
    op.drop_table('signal_counters')
    
    op.drop_index('ix_momentum_settings_user_id', table_name='momentum_settings')
    op.drop_table('momentum_settings')
