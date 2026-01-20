"""add credentials table

Revision ID: 003_add_credentials_table
Revises: 002_add_strategy_support_manual
Create Date: 2026-01-20 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_credentials_table'
down_revision = '002_add_strategy_support_manual'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'credentials',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('service', sa.String(50), nullable=False, index=True),
        sa.Column('encrypted_data', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rotation_days', sa.Integer(), nullable=True),
        sa.Column('last_rotated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('access_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_credentials_user_service', 'credentials', ['user_id', 'service'])


def downgrade() -> None:
    op.drop_index('ix_credentials_user_service', table_name='credentials')
    op.drop_table('credentials')
