"""Add default_stop_loss and default_take_profit to trading_accounts

Revision ID: add_default_stop_take_profit
Revises: 020_bridge_schema_drift_reconciliation
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021_add_default_stop_take_profit'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    # Add default_stop_loss and default_take_profit columns
    op.add_column('trading_accounts', sa.Column('default_stop_loss', sa.Float(), nullable=True))
    op.add_column('trading_accounts', sa.Column('default_take_profit', sa.Float(), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column('trading_accounts', 'default_take_profit')
    op.drop_column('trading_accounts', 'default_stop_loss')
