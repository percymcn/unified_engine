# =============================================================================
# PRODUCTION ENVIRONMENT VALIDATION SCRIPT
# =============================================================================
# Run this script to validate production environment before deployment

import os
import re
from urllib.parse import urlparse

def validate_database_url():
    """Validate DATABASE_URL format and security"""
    database_url = os.getenv('DATABASE_URL', '')
    if not database_url:
        return False, "DATABASE_URL is required"
    
    # Check if using PostgreSQL
    if not database_url.startswith('postgresql://'):
        return False, "DATABASE_URL must use PostgreSQL (postgresql://)"
    
    # Check for connection pooling requirements
    if '?sslmode=' not in database_url:
        return False, "DATABASE_URL must include SSL mode for production"
    
    return True, "Database configuration valid"

def validate_redis_url():
    """Validate REDIS_URL format"""
    redis_url = os.getenv('REDIS_URL', '')
    if not redis_url:
        return False, "REDIS_URL is required"
    
    if not redis_url.startswith('redis://'):
        return False, "REDIS_URL must use redis:// format"
    
    return True, "Redis configuration valid"

def validate_urls():
    """Validate frontend and backend URLs"""
    frontend_url = os.getenv('NEXT_PUBLIC_FRONTEND_URL', '')
    backend_url = os.getenv('NEXT_PUBLIC_BACKEND_URL', '')
    
    if not frontend_url or not backend_url:
        return False, "Frontend and backend URLs are required"
    
    # Check HTTPS
    if not frontend_url.startswith('https://'):
        return False, "NEXT_PUBLIC_FRONTEND_URL must use HTTPS"
    
    if not backend_url.startswith('https://'):
        return False, "NEXT_PUBLIC_BACKEND_URL must use HTTPS"
    
    return True, "URL configuration valid"

def validate_oauth():
    """Validate Google OAuth configuration"""
    client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', '')
    
    missing = []
    if not client_id:
        missing.append('GOOGLE_CLIENT_ID')
    if not client_secret:
        missing.append('GOOGLE_CLIENT_SECRET')
    if not redirect_uri:
        missing.append('GOOGLE_REDIRECT_URI')
    
    if missing:
        return False, f"Missing OAuth config: {', '.join(missing)}"
    
    # Validate redirect URI matches frontend domain
    if not redirect_uri.startswith(os.getenv('NEXT_PUBLIC_FRONTEND_URL', '').split('//')[0]):
        return False, "GOOGLE_REDIRECT_URI must match frontend domain"
    
    return True, "OAuth configuration valid"

def validate_security():
    """Validate security configuration"""
    jwt_secret = os.getenv('JWT_SECRET', '')
    encryption_key = os.getenv('ENCRYPTION_KEY', '')
    
    # JWT Secret validation
    if not jwt_secret:
        return False, "JWT_SECRET is required"
    if len(jwt_secret) < 32:
        return False, "JWT_SECRET must be at least 32 characters"
    
    # Encryption Key validation
    if not encryption_key:
        return False, "ENCRYPTION_KEY is required"
    if len(encryption_key) < 32:
        return False, "ENCRYPTION_KEY must be at least 32 characters"
    
    return True, "Security configuration valid"

def validate_required_env_vars():
    """Check all required environment variables are set"""
    required_vars = [
        'DATABASE_URL',
        'REDIS_URL', 
        'NEXT_PUBLIC_FRONTEND_URL',
        'NEXT_PUBLIC_BACKEND_URL',
        'JWT_SECRET',
        'ENCRYPTION_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        return False, f"Missing required environment variables: {', '.join(missing_vars)}"
    
    return True, "All required environment variables are set"

def main():
    """Run all validation checks"""
    print("🔍 Validating TradeFlow Production Environment...")
    print("=" * 60)
    
    validations = [
        ("Required Variables", validate_required_env_vars),
        ("Database", validate_database_url),
        ("Redis", validate_redis_url),
        ("URLs", validate_urls),
        ("OAuth", validate_oauth),
        ("Security", validate_security),
    ]
    
    all_valid = True
    
    for name, validator in validations:
        is_valid, message = validator()
        status = "✅" if is_valid else "❌"
        print(f"{status} {name}: {message}")
        if not is_valid:
            all_valid = False
    
    print("=" * 60)
    
    if all_valid:
        print("🎉 Environment validation PASSED! Ready for production deployment.")
        return 0
    else:
        print("⚠️ Environment validation FAILED! Fix the above issues before deploying.")
        return 1

if __name__ == "__main__":
    exit(main())