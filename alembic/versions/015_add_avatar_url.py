"""add avatar_url to users

Revision ID: 015
Revises: 014
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    """Add avatar_url column to users table."""
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade():
    """Remove avatar_url column."""
    op.drop_column('users', 'avatar_url')
