"""Add AI enhancement toggle to SmartFlow config

Revision ID: 040_ai_enhancement
Revises: 039_ai_strategy_cache
Create Date: 2024-03-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '040_ai_enhancement'
down_revision = '039_ai_strategy_cache'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add AI enhancement columns to smartflow_config
    op.add_column('smartflow_config',
        sa.Column('enable_ai_enhancement', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('smartflow_config',
        sa.Column('ai_analysis_types', sa.JSON(), nullable=True, server_default='["technical", "patterns"]')
    )


def downgrade() -> None:
    op.drop_column('smartflow_config', 'ai_analysis_types')
    op.drop_column('smartflow_config', 'enable_ai_enhancement')
