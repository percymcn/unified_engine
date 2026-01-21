"""add broker_symbol_formats table

Revision ID: 007_add_broker_symbol_format
Revises: 006_add_symbol_alias
Create Date: 2026-01-21 20:47:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_broker_symbol_format'
down_revision = '006_add_symbol_alias'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create broker_symbol_formats table
    op.create_table(
        'broker_symbol_formats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False, unique=True),
        sa.Column('detected_patterns', sa.JSON(), nullable=True),
        sa.Column('sample_symbols', sa.JSON(), nullable=True),
        sa.Column('common_symbols_map', sa.JSON(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create index for account lookup
    op.create_index('ix_broker_symbol_formats_account_id', 'broker_symbol_formats', ['account_id'])


def downgrade() -> None:
    op.drop_index('ix_broker_symbol_formats_account_id', table_name='broker_symbol_formats')
    op.drop_table('broker_symbol_formats')
