"""add confidence and reason to signal logs

Revision ID: 042
Revises: 041
Create Date: 2026-03-13 01:50:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '042'
down_revision = '041_bearish_bias'
branch_labels = None
depends_on = None


def upgrade():
    # Add confidence and reason columns to smartflow_signal_logs
    op.add_column('smartflow_signal_logs', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('smartflow_signal_logs', sa.Column('reason', sa.Text(), nullable=True))


def downgrade():
    # Remove confidence and reason columns
    op.drop_column('smartflow_signal_logs', 'reason')
    op.drop_column('smartflow_signal_logs', 'confidence')
