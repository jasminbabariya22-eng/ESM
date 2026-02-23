from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from typing import List
from datetime import datetime

router = APIRouter(prefix="/users", tags=["Users"])


# --------------------------------
# 1️⃣ CREATE USER
# --------------------------------
@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):

    db_user = User(
        **user.dict(),
        is_deleted=0,
        created_on=datetime.utcnow()   
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


# --------------------------------
# 2️⃣ GET USER BY ID
# --------------------------------
@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# --------------------------------
# 3️⃣ SOFT DELETE USER
# --------------------------------
@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_deleted = 1
    db.commit()

    return {"message": "User deleted successfully"}


# --------------------------------
# 4️⃣ UPDATE USER
# --------------------------------
@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    return user