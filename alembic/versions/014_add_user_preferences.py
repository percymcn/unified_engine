"""add user preferences

Revision ID: 014
Revises: 013
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    """Add timezone and notification_preferences columns to users table."""
    # Add timezone column with default UTC
    op.add_column('users', sa.Column('timezone', sa.String(length=50), nullable=True))

    # Add notification_preferences JSON column
    op.add_column('users', sa.Column('notification_preferences', sa.JSON(), nullable=True))

    # Set defaults for existing users
    op.execute("UPDATE users SET timezone = 'UTC' WHERE timezone IS NULL")
    op.execute("""
        UPDATE users SET notification_preferences = '{"trade_alerts": true, "error_notifications": true, "daily_summary": false, "email_notifications": true}'
        WHERE notification_preferences IS NULL
    """)


def downgrade():
    """Remove user preferences columns."""
    op.drop_column('users', 'notification_preferences')
    op.drop_column('users', 'timezone')
