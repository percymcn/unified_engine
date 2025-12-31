from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import Position, Account, User
from app.models.schemas import Position as PositionSchema, PositionCreate
from app.routers.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[PositionSchema])
async def get_positions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all positions for current user"""
    positions = db.query(Position).join(Account).filter(
        Account.user_id == current_user.id,
        Position.is_active == True
    ).offset(skip).limit(limit).all()
    return positions

@router.post("/", response_model=PositionSchema)
async def create_position(
    position: PositionCreate,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new position"""
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
    
    db_position = Position(
        **position.dict(),
        account_id=account_id
    )
    db.add(db_position)
    db.commit()
    db.refresh(db_position)
    return db_position

@router.get("/{position_id}", response_model=PositionSchema)
async def get_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific position"""
    position = db.query(Position).join(Account).filter(
        Position.id == position_id,
        Account.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    return position

@router.post("/{position_id}/close")
async def close_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Close position"""
    position = db.query(Position).join(Account).filter(
        Position.id == position_id,
        Account.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    position.is_active = False
    position.close_time = datetime.utcnow()
    db.commit()
    
    return {"message": "Position closed successfully"}

@router.get("/account/{account_id}", response_model=List[PositionSchema])
async def get_account_positions(
    account_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get positions for specific account"""
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
    
    positions = db.query(Position).filter(
        Position.account_id == account_id,
        Position.is_active == True
    ).offset(skip).limit(limit).all()
    return positions