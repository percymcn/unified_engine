from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.models import Account, User
from app.models.schemas import Account as AccountSchema, AccountCreate, AccountUpdate
from app.routers.auth import get_current_user
from app.core.event_emitter import emit_account_event

router = APIRouter()

@router.get("/", response_model=List[AccountSchema])
async def get_accounts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all accounts for current user"""
    accounts = db.query(Account).filter(
        Account.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return accounts

@router.post("/", response_model=AccountSchema)
async def create_account(
    account: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new trading account"""
    db_account = Account(
        **account.dict(),
        user_id=current_user.id
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    # Emit event
    await emit_account_event("created", db_account.id, {
        "broker": db_account.broker.value,
        "account_type": db_account.account_type.value
    })
    
    return db_account

@router.get("/{account_id}", response_model=AccountSchema)
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific account"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return account

@router.put("/{account_id}", response_model=AccountSchema)
async def update_account(
    account_id: int,
    account_update: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update account"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    for field, value in account_update.dict(exclude_unset=True).items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    return account

@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete account"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    db.delete(account)
    db.commit()
    return {"message": "Account deleted successfully"}

@router.post("/{account_id}/sync")
async def sync_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync account with broker"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # TODO: Implement broker-specific sync logic
    account.is_connected = True
    account.last_sync = datetime.utcnow()
    db.commit()
    
    return {"message": "Account synced successfully"}

@router.get("/{account_id}/balance")
async def get_account_balance(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get account balance from broker"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # TODO: Implement broker-specific balance fetch
    return {
        "account_id": account.account_id,
        "balance": account.balance,
        "equity": account.equity,
        "margin": account.margin,
        "free_margin": account.free_margin,
        "last_sync": account.last_sync
    }