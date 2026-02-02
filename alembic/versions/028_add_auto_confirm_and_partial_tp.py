"""Add auto_confirm and partial take profit fields

Revision ID: 028
Revises: 027
Create Date: 2026-02-01
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '028_auto_confirm'
down_revision = '027_enhance_risk_tracking'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add auto_confirm to trading_accounts
    op.add_column('trading_accounts', sa.Column('auto_confirm', sa.Boolean(), server_default='true', nullable=True))


def downgrade() -> None:
    op.drop_column('trading_accounts', 'auto_confirm')
