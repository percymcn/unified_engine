#!/usr/bin/env python3
"""
Script to create admin user for the Unified Trading Engine
"""
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

try:
    from sqlalchemy.orm import Session
    from app.db.database import get_db, engine, Base
    from app.models.models import User
    from app.core.security import get_password_hash
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please make sure you're in the unified_engine directory and dependencies are installed")
    sys.exit(1)

def create_admin_user():
    """Create an admin user"""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.email == "admin@tradingengine.com").first()
        
        if admin_user:
            print("❌ Admin user already exists")
            return
        
        # Create admin user
        admin_user = User(
            email="admin@tradingengine.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print("📧 Email: admin@tradingengine.com")
        print("🔑 Password: admin123")
        print("⚠️ Please change the password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()