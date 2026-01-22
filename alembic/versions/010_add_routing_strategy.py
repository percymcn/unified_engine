"""Add routing strategy columns to webhook_configs

Revision ID: 010_routing_strategy
Revises: 009_add_account_settings_and_groups
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '010_routing_strategy'
down_revision = '009_add_account_settings_and_groups'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add routing_strategy and specific_account_ids to webhook_configs"""
    # Add routing_strategy column with default value
    op.add_column(
        'webhook_configs',
        sa.Column('routing_strategy', sa.String(30), server_default='default_only', nullable=True)
    )

    # Add specific_account_ids JSON column
    op.add_column(
        'webhook_configs',
        sa.Column('specific_account_ids', JSON, nullable=True)
    )


def downgrade() -> None:
    """Remove routing columns from webhook_configs"""
    op.drop_column('webhook_configs', 'specific_account_ids')
    op.drop_column('webhook_configs', 'routing_strategy')
