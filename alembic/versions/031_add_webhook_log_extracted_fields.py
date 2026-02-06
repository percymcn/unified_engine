"""Add extracted fields to webhook_logs for easier querying

Revision ID: 031_add_webhook_log_fields
Revises: 030_add_block_pnl_signals
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031'
down_revision = '030_block_pnl'
branch_labels = None
depends_on = None


def upgrade():
    # Add extracted fields to webhook_logs for easier querying
    op.add_column('webhook_logs', sa.Column('symbol', sa.String(), nullable=True))
    op.add_column('webhook_logs', sa.Column('action', sa.String(), nullable=True))
    op.add_column('webhook_logs', sa.Column('quantity', sa.Float(), nullable=True))
    op.add_column('webhook_logs', sa.Column('price', sa.Float(), nullable=True))
    op.add_column('webhook_logs', sa.Column('stop_loss', sa.Float(), nullable=True))
    op.add_column('webhook_logs', sa.Column('take_profit', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('webhook_logs', 'take_profit')
    op.drop_column('webhook_logs', 'stop_loss')
    op.drop_column('webhook_logs', 'price')
    op.drop_column('webhook_logs', 'quantity')
    op.drop_column('webhook_logs', 'action')
    op.drop_column('webhook_logs', 'symbol')
