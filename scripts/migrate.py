"""
Database migrations and seed data for Unified Trading Engine.
Creates initial database schema and populates with sample data.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, SessionLocal, Base
from app.models.models import User, Account, Position, Trade, Signal, WebhookLog
from app.core.security import get_password_hash


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def drop_tables():
    """Drop all database tables (use with caution!)."""
    print("⚠️  Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Database tables dropped successfully")


def create_admin_user():
    """Create default admin user."""
    print("Creating admin user...")
    
    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.email == "admin@tradingengine.com").first()
        if existing_admin:
            print("ℹ️  Admin user already exists")
            return
        
        # Create admin user
        admin_user = User(
            email="admin@tradingengine.com",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),  # Change this in production!
            is_active=True,
            is_admin=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin user created: {admin_user.email}")
        print("⚠️  Default password: admin123 (CHANGE THIS IN PRODUCTION!)")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def create_sample_user():
    """Create a sample regular user for testing."""
    print("Creating sample user...")
    
    db = SessionLocal()
    try:
        # Check if sample user already exists
        existing_user = db.query(User).filter(User.email == "trader@example.com").first()
        if existing_user:
            print("ℹ️  Sample user already exists")
            return
        
        # Create sample user
        sample_user = User(
            email="trader@example.com",
            full_name="Sample Trader",
            hashed_password=get_password_hash("trader123"),
            is_active=True,
            is_admin=False,
            created_at=datetime.utcnow()
        )
        
        db.add(sample_user)
        db.commit()
        db.refresh(sample_user)
        
        print(f"✅ Sample user created: {sample_user.email}")
        print("ℹ️  Sample password: trader123")
        
    except Exception as e:
        print(f"❌ Error creating sample user: {e}")
        db.rollback()
    finally:
        db.close()


def create_sample_accounts():
    """Create sample trading accounts."""
    print("Creating sample accounts...")
    
    db = SessionLocal()
    try:
        # Get sample user
        sample_user = db.query(User).filter(User.email == "trader@example.com").first()
        if not sample_user:
            print("❌ Sample user not found, skipping account creation")
            return
        
        # Check if accounts already exist
        existing_accounts = db.query(Account).filter(Account.user_id == sample_user.id).count()
        if existing_accounts > 0:
            print("ℹ️  Sample accounts already exist")
            return
        
        # Create sample accounts for each broker
        sample_accounts = [
            Account(
                user_id=sample_user.id,
                broker="MT4",
                account_id="12345",
                account_name="Demo MT4 Account",
                is_active=True,
                api_key="demo_mt4_key",
                api_secret="demo_mt4_secret",
                created_at=datetime.utcnow()
            ),
            Account(
                user_id=sample_user.id,
                broker="MT5",
                account_id="67890",
                account_name="Demo MT5 Account",
                is_active=True,
                api_key="demo_mt5_key",
                api_secret="demo_mt5_secret",
                created_at=datetime.utcnow()
            ),
            Account(
                user_id=sample_user.id,
                broker="TRADELOCKER",
                account_id="TL_DEMO_001",
                account_name="Demo TradeLocker Account",
                is_active=True,
                api_key="demo_tl_key",
                api_secret="demo_tl_secret",
                created_at=datetime.utcnow()
            ),
            Account(
                user_id=sample_user.id,
                broker="TRADOVATE",
                account_id="TV_DEMO_001",
                account_name="Demo Tradovate Account",
                is_active=True,
                api_key="demo_tv_key",
                api_secret="demo_tv_secret",
                created_at=datetime.utcnow()
            ),
            Account(
                user_id=sample_user.id,
                broker="PROJECTX",
                account_id="PX_DEMO_001",
                account_name="Demo ProjectX Account",
                is_active=True,
                api_key="demo_px_key",
                api_secret="demo_px_secret",
                created_at=datetime.utcnow()
            )
        ]
        
        for account in sample_accounts:
            db.add(account)
        
        db.commit()
        print(f"✅ Created {len(sample_accounts)} sample accounts")
        
    except Exception as e:
        print(f"❌ Error creating sample accounts: {e}")
        db.rollback()
    finally:
        db.close()


def create_sample_signals():
    """Create sample trading signals."""
    print("Creating sample signals...")
    
    db = SessionLocal()
    try:
        # Get sample user and accounts
        sample_user = db.query(User).filter(User.email == "trader@example.com").first()
        if not sample_user:
            print("❌ Sample user not found, skipping signal creation")
            return
        
        mt4_account = db.query(Account).filter(
            Account.user_id == sample_user.id,
            Account.broker == "MT4"
        ).first()
        
        if not mt4_account:
            print("❌ Sample MT4 account not found, skipping signal creation")
            return
        
        # Check if signals already exist
        existing_signals = db.query(Signal).filter(Signal.user_id == sample_user.id).count()
        if existing_signals > 0:
            print("ℹ️  Sample signals already exist")
            return
        
        # Create sample signals
        sample_signals = [
            Signal(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="EURUSD",
                order_type="MARKET",
                side="BUY",
                quantity=0.1,
                price=1.1000,
                stop_loss=1.0900,
                take_profit=1.1100,
                signal_type="ENTRY",
                strategy="MA_Cross",
                confidence=0.85,
                status="executed",
                created_at=datetime.utcnow() - timedelta(hours=2),
                executed_at=datetime.utcnow() - timedelta(hours=2)
            ),
            Signal(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="EURUSD",
                order_type="MARKET",
                side="SELL",
                quantity=0.1,
                price=1.1050,
                signal_type="EXIT",
                strategy="MA_Cross",
                confidence=0.90,
                status="executed",
                related_signal_id=None,  # Will be set after first signal is created
                created_at=datetime.utcnow() - timedelta(hours=1),
                executed_at=datetime.utcnow() - timedelta(hours=1)
            ),
            Signal(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="GBPUSD",
                order_type="MARKET",
                side="BUY",
                quantity=0.15,
                price=1.2500,
                stop_loss=1.2400,
                take_profit=1.2600,
                signal_type="ENTRY",
                strategy="Breakout",
                confidence=0.75,
                status="pending",
                created_at=datetime.utcnow() - timedelta(minutes=30)
            )
        ]
        
        # Add signals and set relationships
        for i, signal in enumerate(sample_signals):
            db.add(signal)
            db.flush()  # Get the ID
            
            # Set related_signal_id for the exit signal
            if i == 1:  # Second signal is the exit for the first
                signal.related_signal_id = sample_signals[0].id
        
        db.commit()
        print(f"✅ Created {len(sample_signals)} sample signals")
        
    except Exception as e:
        print(f"❌ Error creating sample signals: {e}")
        db.rollback()
    finally:
        db.close()


def create_sample_trades():
    """Create sample trade history."""
    print("Creating sample trades...")
    
    db = SessionLocal()
    try:
        # Get sample user and account
        sample_user = db.query(User).filter(User.email == "trader@example.com").first()
        if not sample_user:
            print("❌ Sample user not found, skipping trade creation")
            return
        
        mt4_account = db.query(Account).filter(
            Account.user_id == sample_user.id,
            Account.broker == "MT4"
        ).first()
        
        if not mt4_account:
            print("❌ Sample MT4 account not found, skipping trade creation")
            return
        
        # Check if trades already exist
        existing_trades = db.query(Trade).filter(Trade.user_id == sample_user.id).count()
        if existing_trades > 0:
            print("ℹ️  Sample trades already exist")
            return
        
        # Create sample trades
        sample_trades = [
            Trade(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="EURUSD",
                side="BUY",
                quantity=0.1,
                entry_price=1.1000,
                exit_price=1.1050,
                stop_loss=1.0900,
                take_profit=1.1100,
                profit=50.0,
                status="closed",
                trade_type="MANUAL",
                strategy="MA_Cross",
                entry_time=datetime.utcnow() - timedelta(hours=2),
                exit_time=datetime.utcnow() - timedelta(hours=1),
                created_at=datetime.utcnow() - timedelta(hours=2)
            ),
            Trade(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="GBPUSD",
                side="SELL",
                quantity=0.15,
                entry_price=1.2500,
                exit_price=1.2450,
                stop_loss=1.2600,
                take_profit=1.2400,
                profit=75.0,
                status="closed",
                trade_type="MANUAL",
                strategy="Breakout",
                entry_time=datetime.utcnow() - timedelta(days=1),
                exit_time=datetime.utcnow() - timedelta(days=1) + timedelta(hours=2),
                created_at=datetime.utcnow() - timedelta(days=1)
            ),
            Trade(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="USDJPY",
                side="BUY",
                quantity=0.2,
                entry_price=110.50,
                exit_price=None,
                stop_loss=109.50,
                take_profit=112.00,
                profit=None,
                status="open",
                trade_type="MANUAL",
                strategy="Scalping",
                entry_time=datetime.utcnow() - timedelta(minutes=15),
                exit_time=None,
                created_at=datetime.utcnow() - timedelta(minutes=15)
            )
        ]
        
        for trade in sample_trades:
            db.add(trade)
        
        db.commit()
        print(f"✅ Created {len(sample_trades)} sample trades")
        
    except Exception as e:
        print(f"❌ Error creating sample trades: {e}")
        db.rollback()
    finally:
        db.close()


def create_sample_positions():
    """Create sample current positions."""
    print("Creating sample positions...")
    
    db = SessionLocal()
    try:
        # Get sample user and account
        sample_user = db.query(User).filter(User.email == "trader@example.com").first()
        if not sample_user:
            print("❌ Sample user not found, skipping position creation")
            return
        
        mt4_account = db.query(Account).filter(
            Account.user_id == sample_user.id,
            Account.broker == "MT4"
        ).first()
        
        if not mt4_account:
            print("❌ Sample MT4 account not found, skipping position creation")
            return
        
        # Check if positions already exist
        existing_positions = db.query(Position).filter(Position.user_id == sample_user.id).count()
        if existing_positions > 0:
            print("ℹ️  Sample positions already exist")
            return
        
        # Create sample positions
        sample_positions = [
            Position(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="EURUSD",
                side="BUY",
                quantity=0.1,
                entry_price=1.1000,
                current_price=1.1025,
                stop_loss=1.0900,
                take_profit=1.1100,
                unrealized_pnl=25.0,
                status="open",
                created_at=datetime.utcnow() - timedelta(minutes=10)
            ),
            Position(
                user_id=sample_user.id,
                account_id=mt4_account.id,
                broker="MT4",
                symbol="GBPUSD",
                side="SELL",
                quantity=0.15,
                entry_price=1.2500,
                current_price=1.2475,
                stop_loss=1.2600,
                take_profit=1.2400,
                unrealized_pnl=37.5,
                status="open",
                created_at=datetime.utcnow() - timedelta(minutes=5)
            )
        ]
        
        for position in sample_positions:
            db.add(position)
        
        db.commit()
        print(f"✅ Created {len(sample_positions)} sample positions")
        
    except Exception as e:
        print(f"❌ Error creating sample positions: {e}")
        db.rollback()
    finally:
        db.close()


def seed_database():
    """Seed database with initial data."""
    print("🌱 Seeding database with initial data...")
    
    create_admin_user()
    create_sample_user()
    create_sample_accounts()
    create_sample_signals()
    create_sample_trades()
    create_sample_positions()
    
    print("✅ Database seeding completed successfully!")


def reset_database():
    """Reset database: drop tables, recreate, and seed."""
    print("🔄 Resetting database...")
    
    drop_tables()
    create_tables()
    seed_database()
    
    print("✅ Database reset completed successfully!")


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration and seeding tool")
    parser.add_argument("--create-tables", action="store_true", help="Create database tables")
    parser.add_argument("--drop-tables", action="store_true", help="Drop all database tables")
    parser.add_argument("--seed", action="store_true", help="Seed database with sample data")
    parser.add_argument("--reset", action="store_true", help="Reset database (drop, create, seed)")
    parser.add_argument("--admin-only", action="store_true", help="Create only admin user")
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    elif args.drop_tables:
        drop_tables()
    elif args.create_tables:
        create_tables()
    elif args.seed:
        create_tables()  # Ensure tables exist
        seed_database()
    elif args.admin_only:
        create_tables()  # Ensure tables exist
        create_admin_user()
    else:
        print("No action specified. Use --help for available options.")
        print("\nCommon usage:")
        print("  python migrate.py --reset     # Complete database reset")
        print("  python migrate.py --seed      # Seed with sample data")
        print("  python migrate.py --admin-only # Create admin user only")


if __name__ == "__main__":
    main()