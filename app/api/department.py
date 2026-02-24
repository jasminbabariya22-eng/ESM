from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.department import Department
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse
)
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/departments", 
                   tags=["Departments"],
                   dependencies=[Depends(get_current_user)]
                   )

# CREATE
@router.post("/", response_model=DepartmentResponse)
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    dept = Department(
        dept_name=data.dept_name,
        description=data.description,
        is_deleted=0,
        created_on=datetime.utcnow()
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


# GET ALL

@router.get("/", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).filter(Department.is_deleted == 0).all()


# GET BY ID
@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db)):
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.is_deleted == 0
    ).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    return dept


# UPDATE
@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: int, data: DepartmentUpdate, db: Session = Depends(get_db)):
    dept = db.query(Department).filter(Department.id == dept_id).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    update_data = data.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(dept, key, value)

    db.commit()
    db.refresh(dept)
    return dept


# SOFT DELETE
@router.delete("/{dept_id}")
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    dept = db.query(Department).filter(Department.id == dept_id).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    dept.is_deleted = 1
    db.commit()

    return {"message": "Department deleted successfully"}