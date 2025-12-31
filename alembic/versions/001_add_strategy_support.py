"""Create API Keys, Strategies, and Account Strategies tables

Revision ID: 001_add_strategy_support
Revises: 
Create Date: 2025-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_strategy_support'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)

    # Create strategies table
    op.create_table('strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('strategy_name', sa.String(), nullable=False),
        sa.Column('strategy_version', sa.String(), nullable=False),
        sa.Column('strategy_source', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_strategies_strategy_id'), 'strategies', ['strategy_id'], unique=True)

    # Create account_strategies table
    op.create_table('account_strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Add strategy fields to signals table
    op.add_column('signals', sa.Column('strategy_id', sa.String(), nullable=True))
    op.add_column('signals', sa.Column('strategy_version', sa.String(), nullable=True))
    op.add_column('signals', sa.Column('strategy_name', sa.String(), nullable=True))
    op.add_column('signals', sa.Column('strategy_source', sa.String(), nullable=True))
    op.create_index('ix_signals_strategy_id', 'signals', 'strategy_id')


def downgrade():
    # Remove strategy fields from signals table
    op.drop_index('ix_signals_strategy_id', table_name='signals')
    op.drop_column('signals', 'strategy_source')
    op.drop_column('signals', 'strategy_name')
    op.drop_column('signals', 'strategy_version')
    op.drop_column('signals', 'strategy_id')

    # Drop account_strategies table
    op.drop_table('account_strategies')

    # Drop strategies table
    op.drop_index(op.f('ix_strategies_strategy_id'), table_name='strategies')
    op.drop_table('strategies')

    # Drop api_keys table
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')