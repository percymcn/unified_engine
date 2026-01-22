"""Add deduplication settings to users table

Revision ID: 017
Revises: 016
Create Date: 2026-01-22

Adds enable_deduplication and deduplication_scope columns to users table
for configuring signal deduplication behavior.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # Add enable_deduplication column with default True
    op.add_column('users', sa.Column(
        'enable_deduplication',
        sa.Boolean(),
        nullable=True,
        server_default='true'
    ))

    # Add deduplication_scope column with default 'per_account'
    op.add_column('users', sa.Column(
        'deduplication_scope',
        sa.String(20),
        nullable=True,
        server_default='per_account'
    ))


def downgrade():
    op.drop_column('users', 'deduplication_scope')
    op.drop_column('users', 'enable_deduplication')
