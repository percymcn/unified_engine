"""add smartflow enhanced toggles and confirmation filters

Revision ID: 035
Revises: 6aba51c2624e
Create Date: 2026-03-05

Adds enhanced toggle fields and confirmation filters to smartflow_config table:

Enhanced toggles:
- enable_vix_inverse: VIX/UVXY inverse sentiment
- enable_golden_sweeps: Golden sweep bonuses
- enable_leveraged_etfs: Use leveraged ETFs
- vix_golden_threshold: VIX golden sweep threshold
- min_premium: Minimum flow premium to count

Confirmation filters:
- enable_price_confirmation: EMA filter
- enable_rsi_filter: RSI overbought/oversold filter
- enable_volume_filter: Volume spike requirement
- enable_time_filter: Time-of-day guard
- enable_fib_confluence: Fibonacci retracement bonus
- min_confidence_score: Minimum confidence % to execute
- rsi_overbought, rsi_oversold: RSI thresholds
- volume_spike_multiplier: Volume spike multiplier
- time_filter_start_hour, time_filter_end_hour: Trading hours
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '035'
down_revision = '034'
branch_labels = None
depends_on = None


def upgrade():
    # Enhanced toggles
    op.add_column('smartflow_config', sa.Column('enable_vix_inverse', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('enable_golden_sweeps', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('enable_leveraged_etfs', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('vix_golden_threshold', sa.Float(), nullable=False, server_default='100000.0'))
    op.add_column('smartflow_config', sa.Column('min_premium', sa.Float(), nullable=False, server_default='50000.0'))

    # Confirmation filter toggles
    op.add_column('smartflow_config', sa.Column('enable_price_confirmation', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('enable_rsi_filter', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('enable_volume_filter', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('enable_time_filter', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('enable_fib_confluence', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smartflow_config', sa.Column('min_confidence_score', sa.Float(), nullable=False, server_default='70.0'))

    # Confirmation filter parameters
    op.add_column('smartflow_config', sa.Column('rsi_overbought', sa.Float(), nullable=False, server_default='70.0'))
    op.add_column('smartflow_config', sa.Column('rsi_oversold', sa.Float(), nullable=False, server_default='30.0'))
    op.add_column('smartflow_config', sa.Column('volume_spike_multiplier', sa.Float(), nullable=False, server_default='1.5'))
    op.add_column('smartflow_config', sa.Column('time_filter_start_hour', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('smartflow_config', sa.Column('time_filter_end_hour', sa.Integer(), nullable=False, server_default='15'))


def downgrade():
    # Remove confirmation filter parameters
    op.drop_column('smartflow_config', 'time_filter_end_hour')
    op.drop_column('smartflow_config', 'time_filter_start_hour')
    op.drop_column('smartflow_config', 'volume_spike_multiplier')
    op.drop_column('smartflow_config', 'rsi_oversold')
    op.drop_column('smartflow_config', 'rsi_overbought')

    # Remove confirmation filter toggles
    op.drop_column('smartflow_config', 'min_confidence_score')
    op.drop_column('smartflow_config', 'enable_fib_confluence')
    op.drop_column('smartflow_config', 'enable_time_filter')
    op.drop_column('smartflow_config', 'enable_volume_filter')
    op.drop_column('smartflow_config', 'enable_rsi_filter')
    op.drop_column('smartflow_config', 'enable_price_confirmation')

    # Remove enhanced toggles
    op.drop_column('smartflow_config', 'min_premium')
    op.drop_column('smartflow_config', 'vix_golden_threshold')
    op.drop_column('smartflow_config', 'enable_leveraged_etfs')
    op.drop_column('smartflow_config', 'enable_golden_sweeps')
    op.drop_column('smartflow_config', 'enable_vix_inverse')
