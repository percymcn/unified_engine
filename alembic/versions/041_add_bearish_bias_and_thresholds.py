"""Add bearish bias toggle and adjusted thresholds to smartflow_config

Revision ID: 041_bearish_bias
Revises: 040_add_ai_enhancement_toggle
Create Date: 2026-03-12 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '041_bearish_bias'
down_revision = '040_ai_enhancement'  # Match the actual revision ID
branch_labels = None
depends_on = None


def upgrade():
    # Add enable_bearish_bias column to smartflow_config
    op.add_column('smartflow_config', sa.Column('enable_bearish_bias', sa.Boolean(), nullable=True, server_default='false'))

    # Update existing config to have better thresholds (Solution 2)
    # buy_threshold: 4 -> 6 (reduce buy signals)
    # sell_threshold: -4 -> -2 (allow more sell signals)
    op.execute("""
        UPDATE smartflow_config
        SET buy_threshold = 6,
            sell_threshold = -2,
            enable_bearish_bias = true
        WHERE id = 1
    """)


def downgrade():
    # Revert thresholds
    op.execute("""
        UPDATE smartflow_config
        SET buy_threshold = 4,
            sell_threshold = -4
        WHERE id = 1
    """)

    # Drop column
    op.drop_column('smartflow_config', 'enable_bearish_bias')
