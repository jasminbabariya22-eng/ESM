from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.log_id == data.log_id,
        User.is_deleted == 0
    ).first()

    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={
            "id": user.id,
            "logid": user.log_id,
            "role_id": user.role_id,
            "dept_id": user.dept_id,
        }
    )

    return {
        "id": user.id,
        "password": user.password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "logid": user.log_id,
        "department_id": user.dept_id,
        "role_id": user.role_id,
        "user_type_id": user.user_type_id,
        "user_type": "Admin",                           # you can fetch from role table later
        "access_token": access_token
    }