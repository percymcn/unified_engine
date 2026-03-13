"""add time filter minutes

Revision ID: 036
Revises: 035
Create Date: 2026-03-06 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None


def upgrade():
    # Add minute columns for more precise time filtering
    op.add_column('smartflow_config', sa.Column('time_filter_start_minute', sa.Integer(), nullable=False, server_default='30'))
    op.add_column('smartflow_config', sa.Column('time_filter_end_minute', sa.Integer(), nullable=False, server_default='0'))

    # Update default start hour to 9 (combined with minute=30 gives 9:30am)
    op.execute("UPDATE smartflow_config SET time_filter_start_hour = 9 WHERE time_filter_start_hour = 10")


def downgrade():
    # Revert hour changes
    op.execute("UPDATE smartflow_config SET time_filter_start_hour = 10 WHERE time_filter_start_hour = 9")

    # Drop minute columns
    op.drop_column('smartflow_config', 'time_filter_end_minute')
    op.drop_column('smartflow_config', 'time_filter_start_minute')
