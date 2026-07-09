from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.security import create_access_token
from app.core.response import success_response
from app.core.security import verify_password

from app.models.user_role_map import UserRoleMap


# Authentication APIs
router = APIRouter(prefix="/auth", tags=["Authentication"])

# This API is used for login and returns user details along with access token
@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.log_id == data.log_id,
        User.is_deleted == 0,
        User.status == 'Active'
    ).first()

    print("Entered Password:", data.password)
    print("DB Password:", user.password)
    print("Verify:", verify_password(data.password, user.password))

    if not user or not verify_password(data.password,user.password):
        raise HTTPException(status_code=401,detail="Invalid credentials")
    
    menu_ids = db.query(UserRoleMap.menu_id).filter(
        UserRoleMap.role_id == user.role_id
    ).all()

    menu_list = [menu.menu_id for menu in menu_ids]

    access_token = create_access_token(
        data={
            "id": user.id,
            "logid": user.log_id,
            "role_id": user.role_id,
            "dept_id": user.dept_id,
            "user_type_name": user.user_type.name
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
        "menuids": menu_list,
        "access_token": access_token,
        "token_type": "bearer"
    })