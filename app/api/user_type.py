from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeResponse
from typing import List

router = APIRouter(prefix="/user_types", tags=["User Types"])

@router.get("/", response_model=List[UserTypeResponse])
def get_user_types(db: Session = Depends(get_db)):
    return db.query(UserType).filter(UserType.is_deleted == 0).all()