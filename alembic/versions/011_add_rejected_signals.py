"""Add rejected_signals table and max_positions_per_symbol column

Revision ID: 011_add_rejected_signals
Revises: 010_routing_strategy
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '011_add_rejected_signals'
down_revision = '010_routing_strategy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create rejected_signals table and add max_positions_per_symbol column"""
    # Create rejected_signals table
    op.create_table(
        'rejected_signals',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('account_id', sa.Integer, sa.ForeignKey('trading_accounts.id'), index=True),

        # Signal details
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Float),
        sa.Column('source', sa.String(50)),

        # Rejection info
        sa.Column('reason', sa.String(30), nullable=False),  # Enum stored as string
        sa.Column('reason_detail', sa.String(500)),
        sa.Column('limit_value', sa.Float),
        sa.Column('current_value', sa.Float),

        # Metadata
        sa.Column('webhook_config_id', sa.Integer, sa.ForeignKey('webhook_configs.id')),
        sa.Column('original_payload', JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
    )

    # Create composite index for user + date queries
    op.create_index(
        'ix_rejected_signals_user_date',
        'rejected_signals',
        ['user_id', 'created_at']
    )

    # Add max_positions_per_symbol to trading_accounts if not exists
    # Using try/except pattern for idempotent migration
    try:
        op.add_column(
            'trading_accounts',
            sa.Column('max_positions_per_symbol', sa.Integer, server_default='1', nullable=True)
        )
    except Exception:
        pass  # Column may already exist


def downgrade() -> None:
    """Remove rejected_signals table and max_positions_per_symbol column"""
    # Drop index first
    op.drop_index('ix_rejected_signals_user_date', table_name='rejected_signals')

    # Drop rejected_signals table
    op.drop_table('rejected_signals')

    # Remove max_positions_per_symbol column
    try:
        op.drop_column('trading_accounts', 'max_positions_per_symbol')
    except Exception:
        pass
