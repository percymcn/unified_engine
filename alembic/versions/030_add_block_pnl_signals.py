"""Add block_pnl_signals column to momentum_settings

Revision ID: 030_block_pnl
Revises: 029_partial_tp
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '030_block_pnl'
down_revision = '029_partial_tp'
branch_labels = None
depends_on = None


def upgrade():
    # Add block_pnl_signals column to momentum_settings table
    # This allows users to auto-reject signals (vs just warn) when trading against profitable positions
    op.add_column(
        'momentum_settings',
        sa.Column('block_pnl_signals', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade():
    op.drop_column('momentum_settings', 'block_pnl_signals')
