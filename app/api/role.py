from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.role import UserRole
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse
)
from app.core.dependencies import get_current_user
from app.core.response import success_response

router = APIRouter(prefix="/roles", 
                   tags=["Roles"],
                   dependencies=[Depends(get_current_user)]
                   )


# CREATE
@router.post("/", response_model=RoleResponse)
def create_role(data: RoleCreate, db: Session = Depends(get_db)):
    role = UserRole(
        name=data.name,
        description=data.description,
        is_deleted=0,
        created_on=datetime.utcnow()
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return success_response({
        "id": role.id,
        "name": role.name,
        "description": role.description
    })


# GET ALL
@router.get("/", response_model=List[RoleResponse])
def get_roles(db: Session = Depends(get_db)):
    roles = db.query(UserRole).filter(UserRole.is_deleted == 0).all()
    response = []
    for role in roles:
        response.append({
            "id": role.id,
            "name": role.name,
            "description": role.description
        })
    return success_response(response)


# GET BY ID
@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db)):
    dept = db.query(UserRole).filter(
        UserRole.id == role_id,
        UserRole.is_deleted == 0
    ).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Role not found")

    return success_response({
        "id": dept.id,
        "name": dept.name,
        "description": dept.description
    })

# UPDATE
@router.put("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, data: RoleUpdate, db: Session = Depends(get_db)):
    dept = db.query(UserRole).filter(UserRole.id == role_id).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = data.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(dept, key, value)

    db.commit()
    db.refresh(dept)
    return success_response({
        "id": dept.id,
        "name": dept.name,
        "description": dept.description
    })

# SOFT DELETE
@router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    dept = db.query(UserRole).filter(UserRole.id == role_id).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Role not found")

    dept.is_deleted = 1
    db.commit()

    return success_response(message="Role deleted successfully")