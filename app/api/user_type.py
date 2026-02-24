from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.user_type import UserType
from app.schemas.user_type import (
    UserTypeCreate,
    UserTypeUpdate,
    UserTypeResponse
)
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/user_types", 
                   tags=["User Types"],
                   dependencies=[Depends(get_current_user)]
                   )


# CREATE
@router.post("/", response_model=UserTypeResponse)
def create_user_type(data: UserTypeCreate, db: Session = Depends(get_db)):
    dept = UserType(
        name=data.name,
        description=data.description,
        is_deleted=0,
        created_on=datetime.utcnow()
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


# GET ALL
@router.get("/", response_model=List[UserTypeResponse])
def get_user_types(db: Session = Depends(get_db)):
    return db.query(UserType).filter(UserType.is_deleted == 0).all()


# GET BY ID
@router.get("/{user_type_id}", response_model=UserTypeResponse)
def get_user_type(user_type_id: int, db: Session = Depends(get_db)):
    dept = db.query(UserType).filter(
        UserType.id == user_type_id,
        UserType.is_deleted == 0
    ).first()

    if not dept:
        raise HTTPException(status_code=404, detail="User Type not found")

    return dept


# UPDATE
@router.put("/{user_type_id}", response_model=UserTypeResponse)
def update_user_type(user_type_id: int, data: UserTypeUpdate, db: Session = Depends(get_db)):
    dept = db.query(UserType).filter(UserType.id == user_type_id).first()

    if not dept:
        raise HTTPException(status_code=404, detail="User Type not found")

    update_data = data.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(dept, key, value)

    db.commit()
    db.refresh(dept)
    return dept


# SOFT DELETE
@router.delete("/{user_type_id}")
def delete_user_type(user_type_id: int, db: Session = Depends(get_db)):
    dept = db.query(UserType).filter(UserType.id == user_type_id).first()

    if not dept:
        raise HTTPException(status_code=404, detail="User Type not found")

    dept.is_deleted = 1
    db.commit()

    return {"message": "User Type deleted successfully"}