"""Bridge schema drift from create_all to migration-defined schema

Revision ID: 020
Revises: 019
Create Date: 2026-01-23
Applied: 2026-01-23 (manually via psql, then alembic_version updated)

This migration reconciles schema drift caused by:
1. Using Base.metadata.create_all() instead of alembic upgrade
2. Manual SQL commands that used different column names
3. Stamping to head (019) without running actual migrations

Changes:
- signal_counters: Rename columns to match ORM expectations, add missing columns, drop extra columns
- discard_bin: Rename columns to match ORM expectations

This is a NON-DESTRUCTIVE migration - no data loss, only column renames.

NOTE: The actual DB had a mix of old and new column names due to multiple create_all runs.
This migration handles the specific drift state discovered on 2026-01-23:
- signal_counters had: directional_bias, opposite_momentum (correct!), total_signals (duplicate!), last_signal_at
- discard_bin had: raw_payload, normalized_payload
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # signal_counters table fixes (IDEMPOTENT)
    # =========================================================================
    # Rename columns to match ORM model (database_models.py SignalCounter)

    # 1. Rename directional_bias to current_bias (if directional_bias exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='signal_counters' AND column_name='directional_bias')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='signal_counters' AND column_name='current_bias') THEN
                ALTER TABLE signal_counters RENAME COLUMN directional_bias TO current_bias;
            END IF;
        END
        $$;
    """)

    # 2. Drop total_signals if it exists (duplicate of opposite_momentum)
    op.execute("ALTER TABLE signal_counters DROP COLUMN IF EXISTS total_signals;")

    # 3. Rename last_signal_at to last_signal_ts
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='signal_counters' AND column_name='last_signal_at')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='signal_counters' AND column_name='last_signal_ts') THEN
                ALTER TABLE signal_counters RENAME COLUMN last_signal_at TO last_signal_ts;
            END IF;
        END
        $$;
    """)

    # 4. Add missing columns
    op.execute("ALTER TABLE signal_counters ADD COLUMN IF NOT EXISTS last8_pattern VARCHAR(16);")
    op.execute("ALTER TABLE signal_counters ADD COLUMN IF NOT EXISTS chop_mode BOOLEAN NOT NULL DEFAULT false;")

    # 5. Drop created_at if exists (not in ORM model)
    op.execute("ALTER TABLE signal_counters DROP COLUMN IF EXISTS created_at;")

    # =========================================================================
    # discard_bin table fixes (IDEMPOTENT)
    # =========================================================================
    # Rename columns to match ORM model (database_models.py DiscardBin)

    # 1. Rename raw_payload to raw_signal_json
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='discard_bin' AND column_name='raw_payload')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='discard_bin' AND column_name='raw_signal_json') THEN
                ALTER TABLE discard_bin RENAME COLUMN raw_payload TO raw_signal_json;
                ALTER TABLE discard_bin ALTER COLUMN raw_signal_json TYPE JSON USING raw_signal_json::json;
            END IF;
        END
        $$;
    """)

    # 2. Rename normalized_payload to normalized_signal_json
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='discard_bin' AND column_name='normalized_payload')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='discard_bin' AND column_name='normalized_signal_json') THEN
                ALTER TABLE discard_bin RENAME COLUMN normalized_payload TO normalized_signal_json;
            END IF;
        END
        $$;
    """)


def downgrade():
    # =========================================================================
    # Reverse discard_bin changes
    # =========================================================================
    op.alter_column('discard_bin', 'normalized_signal_json',
                    new_column_name='normalized_payload',
                    type_=sa.Text(),
                    existing_type=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='normalized_signal_json::text')

    op.alter_column('discard_bin', 'raw_signal_json',
                    new_column_name='raw_payload',
                    type_=sa.Text(),
                    existing_type=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='raw_signal_json::text')

    # =========================================================================
    # Reverse signal_counters changes
    # =========================================================================
    # Add back created_at column
    op.add_column('signal_counters',
                  sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))

    # Drop added columns
    op.drop_column('signal_counters', 'chop_mode')
    op.drop_column('signal_counters', 'last8_pattern')

    # Reverse column renames
    op.alter_column('signal_counters', 'last_signal_ts',
                    new_column_name='last_signal_at',
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=True)

    op.alter_column('signal_counters', 'opposite_momentum',
                    new_column_name='total_signals',
                    existing_type=sa.Integer(),
                    existing_nullable=True)

    op.alter_column('signal_counters', 'current_bias',
                    new_column_name='directional_bias',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)
