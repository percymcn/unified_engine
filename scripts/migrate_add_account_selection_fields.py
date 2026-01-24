#!/usr/bin/env python3
"""
Migration script to add account selection fields to trading_accounts table.
Idempotent - safe to run multiple times.

Fields added:
- enabled_broker_account_ids (JSON)
- default_broker_account_id (VARCHAR(100))
- discovered_accounts_cache (JSON)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.db.database import engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_sqlite():
    """Check if database is SQLite"""
    return "sqlite" in settings.DATABASE_URL.lower()

def is_postgres():
    """Check if database is PostgreSQL"""
    return "postgresql" in settings.DATABASE_URL.lower() or "postgres" in settings.DATABASE_URL.lower()

def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate_sqlite():
    """Apply migration for SQLite"""
    logger.info("Detected SQLite database")
    
    with engine.connect() as conn:
        # SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS directly
        # We need to check first
        if not column_exists("trading_accounts", "enabled_broker_account_ids"):
            logger.info("Adding enabled_broker_account_ids column...")
            conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN enabled_broker_account_ids TEXT"))
            conn.commit()
            logger.info("✓ Added enabled_broker_account_ids")
        else:
            logger.info("✓ enabled_broker_account_ids already exists")
        
        if not column_exists("trading_accounts", "default_broker_account_id"):
            logger.info("Adding default_broker_account_id column...")
            conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN default_broker_account_id VARCHAR(100)"))
            conn.commit()
            logger.info("✓ Added default_broker_account_id")
        else:
            logger.info("✓ default_broker_account_id already exists")
        
        if not column_exists("trading_accounts", "discovered_accounts_cache"):
            logger.info("Adding discovered_accounts_cache column...")
            conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN discovered_accounts_cache TEXT"))
            conn.commit()
            logger.info("✓ Added discovered_accounts_cache")
        else:
            logger.info("✓ discovered_accounts_cache already exists")

def migrate_postgres():
    """Apply migration for PostgreSQL"""
    logger.info("Detected PostgreSQL database")
    
    with engine.connect() as conn:
        # PostgreSQL supports IF NOT EXISTS
        if not column_exists("trading_accounts", "enabled_broker_account_ids"):
            logger.info("Adding enabled_broker_account_ids column...")
            conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN enabled_broker_account_ids JSONB"))
            conn.commit()
            logger.info("✓ Added enabled_broker_account_ids")
        else:
            logger.info("✓ enabled_broker_account_ids already exists")
        
        if not column_exists("trading_accounts", "default_broker_account_id"):
            logger.info("Adding default_broker_account_id column...")
            conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN default_broker_account_id VARCHAR(100)"))
            conn.commit()
            logger.info("✓ Added default_broker_account_id")
        else:
            logger.info("✓ default_broker_account_id already exists")
        
        if not column_exists("trading_accounts", "discovered_accounts_cache"):
            logger.info("Adding discovered_accounts_cache column...")
            conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN discovered_accounts_cache JSONB"))
            conn.commit()
            logger.info("✓ Added discovered_accounts_cache")
        else:
            logger.info("✓ discovered_accounts_cache already exists")

def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("Migration: Add Account Selection Fields")
    logger.info("=" * 60)
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
    
    try:
        if is_sqlite():
            migrate_sqlite()
        elif is_postgres():
            migrate_postgres()
        else:
            logger.error(f"Unsupported database type: {settings.DATABASE_URL}")
            logger.error("Supported databases: SQLite, PostgreSQL")
            return 1
        
        logger.info("=" * 60)
        logger.info("✓ Migration completed successfully")
        logger.info("=" * 60)
        return 0
        
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
