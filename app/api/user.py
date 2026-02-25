from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from typing import List
from datetime import datetime
from app.schemas.user import UserHybridResponse
from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)]         #router-level protection
)

# --------------------------------
# 1️⃣ CREATE USER
# --------------------------------
@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_user = User(
        **user.dict(),
        created_by=current_user["id"],   # Auto from token
        created_on=datetime.utcnow(),
        is_deleted=0
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


# --------------------------------
# 2️⃣ GET USER BY ID
# --------------------------------
@router.get("/{user_id}", response_model=UserHybridResponse)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == 0
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "log_id": user.log_id,
        "password": user.password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "country": user.country,
        "status": user.status,

        "department_id": user.dept_id,
        "department_name": user.department.dept_name if user.department else None,

        "role_id": user.role_id,
        "role_name": user.role.name if user.role else None,

        "user_type_id": user.user_type_id,
        "user_type_name": user.user_type.name if user.user_type else None,

        "is_deleted": user.is_deleted,
        "created_on": user.created_on,
        
        "photo": user.photo,
        "contact_no": user.contact_no,
        "country_code": user.country_code,
        "std_code": user.std_code,
        "user_city": user.user_city,
    }

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
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == 0
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user, key, value)

    user.modified_by = current_user["id"]
    user.modified_on = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return user

@router.get("/", response_model=List[UserHybridResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_deleted == 0).all()

    response = []

    for user in users:
        response.append({
            "id": user.id,
            "log_id": user.log_id,
            "password": user.password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "country": user.country,
            "status": user.status,

            "department_id": user.dept_id,
            "department_name": user.department.dept_name if user.department else None,

            "role_id": user.role_id,
            "role_name": user.role.name if user.role else None,

            "user_type_id": user.user_type_id,
            "user_type_name": user.user_type.name if user.user_type else None,

            "is_deleted": user.is_deleted,
            "created_on": user.created_on,
            
            "photo": user.photo,
            "contact_no": user.contact_no,
            "country_code": user.country_code,
            "std_code": user.std_code,
            "user_city": user.user_city,
        })

    return response