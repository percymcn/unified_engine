from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from typing import Optional

from app.db.database import get_db
from app.models.models import User, UserSession
from app.models.schemas import UserCreate, User as UserSchema, Token, TokenData, LoginRequest
from app.core.config import settings
from app.core.event_emitter import emit_user_event
from app.core.rate_limiter import limiter, AUTH_RATE_LIMIT, EMAIL_RATE_LIMIT
from app.core.token_blacklist import add_token_to_blacklist, is_token_blacklisted
from app.services.email_service import (
    generate_verification_token,
    verify_email_token,
)
from app.services.resend_email_service import (
    send_verification_email,
    send_welcome_email,
    send_password_reset_email
)

router = APIRouter()
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt"""
    # Ensure password is a string and encode to bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        raise ValueError("Password cannot be longer than 72 bytes")
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Check if token is blacklisted (logged out)
    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


# Optional security scheme for endpoints that work with or without auth
security_optional = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Get current user if authenticated, otherwise return None.

    Use this for endpoints that work both with and without authentication,
    such as public pricing pages that show personalized info when logged in.
    """
    if credentials is None:
        return None

    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
    except JWTError:
        return None

    return get_user_by_username(db, username=token_data.username)


@router.post("/register", response_model=UserSchema)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate password length (bcrypt limit is 72 bytes)
    if not isinstance(user.password, str):
        logger.error("Register: password is not a string", extra={"password_type": type(user.password).__name__})
        raise HTTPException(
            status_code=400,
            detail="Invalid password format"
        )
    
    password_bytes = user.password.encode('utf-8')
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be longer than 72 bytes. Please use a shorter password."
        )
    
    logger.info(f"Registering user: {user.username}, email: {user.email}")
    
    # Check if user already exists
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    db_user = get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Create new user - ensure we hash ONLY the password string
    password_str = str(user.password)  # Explicitly convert to string
    hashed_password = get_password_hash(password_str)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Send verification email (non-blocking)
    try:
        token = generate_verification_token(db_user.email, db_user.id)
        email_sent = await send_verification_email(db_user.email, db_user.username, token)
        if email_sent:
            logger.info(f"Verification email sent to {db_user.email}")
        else:
            logger.warning(f"Failed to send verification email to {db_user.email} - SMTP not configured")
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")

    # Emit event
    await emit_user_event("signup", db_user.id, {
        "email": db_user.email,
        "username": db_user.username
    })

    logger.info(f"User registered successfully: {db_user.id}, username: {db_user.username}")
    return db_user

@router.post("/login", response_model=Token)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request,
    login_data: Optional[LoginRequest] = Body(None),
    username: Optional[str] = None,
    password: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Login user and return access token

    Accepts JSON body (preferred) or query parameters (backward compatibility).
    JSON body format: {"username": str, "password": str}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try to get JSON body first
    try:
        body = await request.json()
        if body and isinstance(body, dict) and "username" in body and "password" in body:
            username = body["username"]
            password = body["password"]
            logger.info(f"Login attempt via JSON body for username: {username}")
        elif login_data:
            username = login_data.username
            password = login_data.password
            logger.info(f"Login attempt via Pydantic body for username: {username}")
    except Exception:
        # No JSON body, will try query params
        pass
    
    # Fallback to query params if no body provided
    if not username or not password:
        if username is None or password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required. Provide as JSON body: {'username': str, 'password': str} or as query parameters."
            )
    
    user = authenticate_user(db, username, password)
    if not user:
        logger.warning(f"Login failed for username: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Emit event
    await emit_user_event("login", user.id, {
        "username": user.username
    })
    
    logger.info(f"Login successful for user: {user.id}, username: {user.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """Logout user and invalidate the token"""
    # Add token to blacklist so it can't be reused
    token = credentials.credentials
    blacklisted = await add_token_to_blacklist(token)
    if blacklisted:
        return {"message": "Successfully logged out", "token_revoked": True}
    else:
        # Even if blacklisting fails, tell user logout succeeded
        # They should still clear the token client-side
        return {"message": "Successfully logged out", "token_revoked": False}

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "user_id": current_user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.put("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's active sessions"""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).all()
    
    return sessions

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session"""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    session.is_active = False
    db.commit()
    
    return {"message": "Session revoked"}


@router.post("/verify-email")
async def verify_email(token: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Verify user email with token from verification email.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Decode and validate token
    payload = verify_email_token(token)
    if not payload:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )

    user_id = payload.get("user_id")
    email = payload.get("sub")

    # Find user
    user = db.query(User).filter(User.id == user_id, User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.is_verified:
        return {"message": "Email already verified", "already_verified": True}

    # Mark as verified
    user.is_verified = True
    db.commit()

    # Send welcome email
    try:
        await send_welcome_email(user.email, user.username)
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")

    logger.info(f"Email verified for user {user.id}")
    return {"message": "Email verified successfully", "verified": True}


@router.post("/resend-verification")
@limiter.limit(EMAIL_RATE_LIMIT)
async def resend_verification_email(
    request: Request,
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Resend verification email to user.
    """
    import logging
    logger = logging.getLogger(__name__)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent"}

    if user.is_verified:
        return {"message": "Email already verified", "already_verified": True}

    # Generate and send new verification email
    try:
        token = generate_verification_token(user.email, user.id)
        email_sent = await send_verification_email(user.email, user.username, token)
        if email_sent:
            logger.info(f"Verification email resent to {user.email}")
        else:
            logger.warning(f"SMTP not configured - could not resend verification")
    except Exception as e:
        logger.error(f"Error resending verification email: {e}")

    return {"message": "If the email exists, a verification link has been sent"}


def generate_password_reset_token(email: str, user_id: int) -> str:
    """Generate a JWT token for password reset with unique JTI for one-time use"""
    import secrets
    expires = datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour
    jti = secrets.token_urlsafe(16)  # Unique token ID for one-time use tracking
    to_encode = {
        "sub": email,
        "user_id": user_id,
        "type": "password_reset",
        "jti": jti,  # JWT ID for blacklisting after use
        "exp": expires
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[dict]:
    """Verify a password reset token and return payload if valid"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload
    except JWTError:
        return None


@router.post("/forgot-password")
@limiter.limit(EMAIL_RATE_LIMIT)
async def forgot_password(
    request: Request,
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Request a password reset email.
    Always returns success message to prevent email enumeration.
    """
    import logging
    logger = logging.getLogger(__name__)

    user = db.query(User).filter(User.email == email).first()

    # Always return same message regardless of whether user exists (security)
    if user:
        try:
            token = generate_password_reset_token(user.email, user.id)
            email_sent = await send_password_reset_email(user.email, user.username, token)
            if email_sent:
                logger.info(f"Password reset email sent to {user.email}")
            else:
                logger.warning(f"SMTP not configured - could not send password reset email")
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")

    return {"message": "If an account exists with that email, a password reset link has been sent"}


@router.post("/reset-password")
@limiter.limit(AUTH_RATE_LIMIT)
async def reset_password(
    request: Request,
    token: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Reset password using the token from the email.
    Token can only be used once - subsequent attempts will fail.
    """
    import logging
    from app.cache.redis_client import redis_client
    logger = logging.getLogger(__name__)

    # Verify the token
    payload = verify_password_reset_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check if token has already been used (one-time use)
    jti = payload.get("jti")
    if jti:
        used_key = f"password_reset_used:{jti}"
        try:
            already_used = await redis_client.get(used_key)
            if already_used:
                logger.warning(f"Attempt to reuse password reset token: {jti[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This reset link has already been used"
                )
        except Exception as e:
            if "already been used" in str(e):
                raise
            logger.warning(f"Redis check failed, proceeding: {e}")

    user_id = payload.get("user_id")
    email = payload.get("sub")

    user = db.query(User).filter(User.id == user_id, User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Mark token as used BEFORE updating password (prevents race condition)
    if jti:
        try:
            await redis_client.set(used_key, "1", ex=3600)  # Keep for 1 hour (token TTL)
        except Exception as e:
            logger.warning(f"Failed to mark token as used: {e}")

    # Update password
    try:
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        logger.info(f"Password reset successfully for user {user.id}")
        return {"message": "Password reset successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


async def verify_api_key(api_key: str = Header(None, alias="X-API-Key"), db: Session = Depends(get_db)) -> User:
    """Verify API key against database"""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    # Verify against database
    from app.routers.api_keys import verify_api_key_from_db
    user = await verify_api_key_from_db(api_key, db)

    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )