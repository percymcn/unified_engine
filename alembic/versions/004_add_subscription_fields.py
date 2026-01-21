"""add subscription fields to users

Revision ID: 004
Revises: 003_add_credentials_table
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_subscription_fields'
down_revision = '003_add_credentials_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add subscription fields to users table
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('subscription_tier', sa.String(), nullable=True, server_default='free'))
    op.add_column('users', sa.Column('subscription_status', sa.String(), nullable=True, server_default='active'))
    op.add_column('users', sa.Column('subscription_ends_at', sa.DateTime(timezone=True), nullable=True))

    # Add index on stripe_customer_id for faster lookups
    op.create_index(op.f('ix_users_stripe_customer_id'), 'users', ['stripe_customer_id'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index(op.f('ix_users_stripe_customer_id'), table_name='users')

    # Remove columns
    op.drop_column('users', 'subscription_ends_at')
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'subscription_tier')
    op.drop_column('users', 'stripe_customer_id')
