"""Add SmartFlow signal tracking to execution logs

Revision ID: 038_smartflow_tracking
Revises: 037_add_smartflow_ml_tables
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '038_smartflow_tracking'
down_revision = '037'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add smartflow_signal_log_id to execution_logs for ML outcome tracking
    op.add_column('execution_logs', sa.Column('smartflow_signal_log_id', sa.Integer(), nullable=True))

    # Add index for faster lookups
    op.create_index('ix_execution_logs_smartflow_signal', 'execution_logs', ['smartflow_signal_log_id'])


def downgrade() -> None:
    op.drop_index('ix_execution_logs_smartflow_signal', table_name='execution_logs')
    op.drop_column('execution_logs', 'smartflow_signal_log_id')
