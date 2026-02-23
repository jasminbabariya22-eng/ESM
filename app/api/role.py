from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.role import UserRole
from app.schemas.role import RoleResponse
from typing import List

router = APIRouter(prefix="/roles", tags=["Roles"])

@router.get("/", response_model=List[RoleResponse])
def get_roles(db: Session = Depends(get_db)):
    return db.query(UserRole).filter(UserRole.is_deleted == 0).all()