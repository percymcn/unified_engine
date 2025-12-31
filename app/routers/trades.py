from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import Trade, Account, User
from app.models.schemas import Trade as TradeSchema, TradeCreate
from app.routers.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[TradeSchema])
async def get_trades(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all trades for current user"""
    trades = db.query(Trade).join(Account).filter(
        Account.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return trades

@router.post("/", response_model=TradeSchema)
async def create_trade(
    trade: TradeCreate,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new trade"""
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    db_trade = Trade(
        **trade.dict(),
        account_id=account_id
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

@router.get("/{trade_id}", response_model=TradeSchema)
async def get_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific trade"""
    trade = db.query(Trade).join(Account).filter(
        Trade.id == trade_id,
        Account.user_id == current_user.id
    ).first()
    
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )
    
    return trade

@router.get("/account/{account_id}", response_model=List[TradeSchema])
async def get_account_trades(
    account_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trades for specific account"""
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    trades = db.query(Trade).filter(
        Trade.account_id == account_id
    ).offset(skip).limit(limit).all()
    return trades