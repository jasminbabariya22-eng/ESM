from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.log_id == data.log_id,
        User.is_deleted == 0
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # If passwords stored plain text 
    if user.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={
            "sub": user.log_id,
            "user_id": user.id,
            "role_id": user.role_id,
            "dept_id": user.dept_id
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }