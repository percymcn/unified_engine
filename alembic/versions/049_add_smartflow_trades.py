"""Add smartflow_trades table

Revision ID: 049_add_smartflow_trades
Revises: 048_add_webhook_configs
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '049_add_smartflow_trades'
down_revision = '048_add_webhook_configs'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'smartflow_trades',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False, server_default='0'),
        sa.Column('entry_time', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('strategy', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='open'),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    op.create_index('ix_smartflow_trades_user_id', 'smartflow_trades', ['user_id'])
    op.create_index('ix_smartflow_trades_symbol', 'smartflow_trades', ['symbol'])
    op.create_index('ix_smartflow_trades_entry_time', 'smartflow_trades', ['entry_time'])


def downgrade():
    op.drop_index('ix_smartflow_trades_entry_time', table_name='smartflow_trades')
    op.drop_index('ix_smartflow_trades_symbol', table_name='smartflow_trades')
    op.drop_index('ix_smartflow_trades_user_id', table_name='smartflow_trades')
    op.drop_table('smartflow_trades')
