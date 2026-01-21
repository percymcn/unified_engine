"""add symbol_aliases table

Revision ID: 006_add_symbol_alias
Revises: 005_add_token_expiry
Create Date: 2026-01-21 20:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_symbol_alias'
down_revision = '005_add_token_expiry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create symbol_aliases table
    op.create_table(
        'symbol_aliases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('source_symbol', sa.String(50), nullable=False),
        sa.Column('broker_type', sa.String(50), nullable=False),
        sa.Column('target_symbol', sa.String(50), nullable=False),
        sa.Column('is_auto_detected', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create indexes for common query patterns
    op.create_index('ix_symbol_aliases_user_id', 'symbol_aliases', ['user_id'])
    op.create_index('ix_symbol_aliases_source_symbol', 'symbol_aliases', ['source_symbol'])
    op.create_index('ix_symbol_aliases_broker_type', 'symbol_aliases', ['broker_type'])

    # Create unique constraint: one mapping per user/source/broker
    op.create_unique_constraint(
        'uq_symbol_alias_user_source_broker',
        'symbol_aliases',
        ['user_id', 'source_symbol', 'broker_type']
    )


def downgrade() -> None:
    op.drop_constraint('uq_symbol_alias_user_source_broker', 'symbol_aliases', type_='unique')
    op.drop_index('ix_symbol_aliases_broker_type', table_name='symbol_aliases')
    op.drop_index('ix_symbol_aliases_source_symbol', table_name='symbol_aliases')
    op.drop_index('ix_symbol_aliases_user_id', table_name='symbol_aliases')
    op.drop_table('symbol_aliases')
