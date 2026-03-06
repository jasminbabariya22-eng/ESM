from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List,Dict
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.models.risk_register import RiskRegister
from app.schemas.risk_register import (
    RiskRegisterCreate,
    RiskRegisterUpdate
)

from app.models.department import Department
from app.models.risk_register_hist import RiskRegisterHist

router = APIRouter(
    prefix="/risk-register",
    tags=["Risk Register"],
    dependencies=[Depends(get_current_user)]
)

def build_hybrid_response(risk):
    return {
        "risk_register_id": risk.risk_register_id,
        "risk_id": risk.risk_id,                    
        "risk_name": risk.risk_name,

        "dept_id": risk.dept_id,
        "department_name": risk.department.dept_name if risk.department else None,

        "risk_owner_id": risk.risk_owner_id,
        "risk_owner_name": (
            f"{risk.risk_owner.first_name} {risk.risk_owner.last_name}"
            if risk.risk_owner else None
        ),

        "financial_year": risk.financial_year,
        "risk_status": risk.risk_status,
        "risk_progress": risk.risk_progress,

        "is_active": risk.is_active,
        "is_deleted": risk.is_deleted,
        "created_on": risk.created_on
    }

# Generate unique risk_id based on department sequence
def generate_risk_id(db: Session, dept_id: int):

    dept = db.query(Department).filter(
        Department.id == dept_id
    ).with_for_update().first()

    if not dept:
        raise Exception("Department not found")

    dept.last_risk_number += 1

    number = dept.last_risk_number

    risk_id = f"{dept.dept_short_name}-{str(number).zfill(4)}"

    return risk_id

# CREATE
@router.post("/")
def create_risk_register(payload: RiskRegisterCreate, db: Session = Depends(get_db)):

    try:

        dept = db.query(Department).filter(
            Department.id == payload.dept_id
        ).first()

        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")

        # Generate department-wise risk id
        risk_id = generate_risk_id(db, dept.id)

        risk = RiskRegister(
            risk_id=risk_id,
            risk_name=payload.risk_name,
            dept_id=payload.dept_id,
            risk_owner_id=payload.risk_owner_id,
            financial_year=payload.financial_year,
            risk_status=payload.risk_status,
            risk_progress=payload.risk_progress,
            created_by=1,
            created_on=datetime.now(timezone.utc),
            is_active=0,
            is_deleted=0
        )

        db.add(risk)
        db.flush()

        hist = RiskRegisterHist(                              # HISTORY TABLE INSERT
            risk_register_id=risk.risk_register_id,
            risk_id=risk.risk_id,
            risk_name=risk.risk_name,
            dept_id=risk.dept_id,
            risk_owner_id=risk.risk_owner_id,
            financial_year=risk.financial_year,
            risk_status=risk.risk_status,
            risk_progress=risk.risk_progress,
            created_by=risk.created_by,
            created_on=datetime.now(timezone.utc),
            is_active=risk.is_active,
            is_deleted=risk.is_deleted
        )

        db.add(hist)

        db.commit()

        return success_response(build_hybrid_response(risk))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Get ALL 
@router.get("/")
def get_All_Risks(db: Session = Depends(get_db)):
    risks = db.query(RiskRegister).filter(
        RiskRegister.is_deleted == 0 and RiskRegister.is_active == 0
    ).all()

    response_list = [build_hybrid_response(r) for r in risks]
    return success_response(response_list)


# Get by risk_id
@router.get("/{risk_id}")
def get_Risk_by_risk__id(risk_id: str, db: Session = Depends(get_db)):
    try:
        if any(char.isdigit() for char in risk_id):            # if user fill complete risk_id with prefix and number

            risk = db.query(RiskRegister).filter(
                RiskRegister.risk_id == risk_id,
                RiskRegister.is_deleted == 0,
                RiskRegister.is_active == 0
            ).first()

            if not risk:
                raise HTTPException(status_code=404, detail="Risk not found")

            return success_response(build_hybrid_response(risk))

        
        else:                                         # if user fill prfix only
            risks = db.query(RiskRegister).filter(
                RiskRegister.risk_id.like(f"{risk_id}%"),
                RiskRegister.is_deleted == 0,
                RiskRegister.is_active == 0
            ).all()

            if not risks:
                raise HTTPException(status_code=404, detail="No risks found")

            return success_response([build_hybrid_response(r) for r in risks])

    except Exception as e:
        return error_response(str(e), 400)


# Get by risk_register_id
@router.get("/Risk_Register_id/{risk_register_id}")
def get_Risk_by_register_id(risk_register_id: int, db: Session = Depends(get_db)):
    try:
        risk = db.query(RiskRegister).filter(
            RiskRegister.risk_register_id == risk_register_id,
            RiskRegister.is_deleted == 0,
            RiskRegister.is_active == 0
        ).first()
        
        return success_response(build_hybrid_response(risk))

    except Exception as e:
        return error_response(str(e), 400)


# UPDATE
@router.put("/{risk_register_id}")
def update_Risk(
    risk_register_id: int,
    payload: RiskRegisterUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        risk = db.query(RiskRegister).filter(
            RiskRegister.risk_register_id == risk_register_id,
            RiskRegister.is_deleted == 0 and RiskRegister.is_active == 0
        ).first()

        if not risk:
            return error_response("Risk not found", 404)

        update_data = payload.dict(exclude_unset=True)      # update fields

        for key, value in update_data.items():
            setattr(risk, key, value)

        risk.modified_by = current_user["id"]
        risk.modified_on = datetime.now(timezone.utc)

        db.flush()                                       # apply update before history insert

        # insert updated record into history table
        hist = RiskRegisterHist(
            risk_register_id=risk.risk_register_id,
            risk_id=risk.risk_id,
            risk_name=risk.risk_name,
            dept_id=risk.dept_id,
            risk_owner_id=risk.risk_owner_id,
            financial_year=risk.financial_year,
            risk_status=risk.risk_status,
            risk_progress=risk.risk_progress,
            created_by=current_user["id"],
            created_on=datetime.now(timezone.utc),
            is_active=risk.is_active,
            is_deleted=0
        )

        db.add(hist)

        db.commit()

        return success_response(
            {"risk_register_id": risk.risk_register_id,
            "message": "Risk updated successfully"}
        )

    except Exception as e:
        db.rollback()
        return error_response(str(e), 400)
    
    

# DELETE (Soft Delete)
@router.delete("/{risk_register_id}")
def delete_risk(risk_register_id: int, db: Session = Depends(get_db)):
    try:
        risk = db.query(RiskRegister).filter(
            RiskRegister.risk_register_id == risk_register_id
        ).first()

        if not risk:
            raise HTTPException(status_code=404, detail="Risk not found")

        # Soft delete main table
        risk.is_deleted = 1
        risk.is_active = 1

        # Insert into history table
        hist = RiskRegisterHist(
            risk_register_id=risk.risk_register_id,
            risk_id=risk.risk_id,
            risk_name=risk.risk_name,
            dept_id=risk.dept_id,
            risk_owner_id=risk.risk_owner_id,
            financial_year=risk.financial_year,
            risk_status=risk.risk_status,
            risk_progress=risk.risk_progress,

            created_by=risk.created_by,             
            created_on=risk.created_on,              
            modified_by=risk.modified_by,
            modified_on=datetime.now(timezone.utc),

            is_active=risk.is_active,
            is_deleted=risk.is_deleted
        )

        db.add(hist)
        db.commit()
        db.refresh(risk)

        return success_response({
            "risk_register_id": risk.risk_register_id,
            "message": "Risk deleted successfully"
        })

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))