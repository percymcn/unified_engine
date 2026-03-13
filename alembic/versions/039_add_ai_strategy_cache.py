"""Add AI Strategy cache table

Revision ID: 039_ai_strategy_cache
Revises: 038_add_smartflow_signal_tracking
Create Date: 2024-03-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '039_ai_strategy_cache'
down_revision = '038_smartflow_tracking'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AI Strategy Analysis Cache table
    op.create_table(
        'ai_strategy_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(64), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('ticker', sa.String(20), nullable=False),
        sa.Column('recommendation', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for fast lookups
    op.create_index('ix_ai_strategy_cache_cache_key', 'ai_strategy_cache', ['cache_key'], unique=True)
    op.create_index('ix_ai_strategy_cache_ticker', 'ai_strategy_cache', ['ticker'])
    op.create_index('ix_ai_strategy_cache_expires', 'ai_strategy_cache', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_ai_strategy_cache_expires', 'ai_strategy_cache')
    op.drop_index('ix_ai_strategy_cache_ticker', 'ai_strategy_cache')
    op.drop_index('ix_ai_strategy_cache_cache_key', 'ai_strategy_cache')
    op.drop_table('ai_strategy_cache')
