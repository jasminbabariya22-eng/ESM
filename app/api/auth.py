from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.security import create_access_token
from app.core.response import success_response
from app.schemas.auth import LoginResponse
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Authentication"])

# @router.post("/login")
# def login(
#     form_data: OAuth2PasswordRequestForm = Depends(),
#     db: Session = Depends(get_db)
# ):
#     user = db.query(User).filter(
#         User.log_id == form_data.username,
#         User.is_deleted == 0
#     ).first()

#     if not user or user.password != form_data.password:                    # plaintext password pass here
#         raise HTTPException(status_code=401, detail="Invalid credentials")

#     access_token = create_access_token(
#         data={
#             "id": user.id,
#             "logid": user.log_id,
#             "role_id": user.role_id,
#             "dept_id": user.dept_id,
#         }
#     )

#     return {
#         "access_token": access_token,
#         "token_type": "bearer"
#     }

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

    return success_response({
        "id": user.id,
        "password": user.password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "logid": user.log_id,
        "created_on": user.created_on,
        "department_id": user.dept_id,
        "role_id": user.role_id,
        "user_type_id": user.user_type_id,
        "user_type": user.user_type.name if user.user_type else None,
        "access_token": access_token,
        "token_type": "bearer"
    })