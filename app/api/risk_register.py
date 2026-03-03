from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success_response

from app.models.risk_register import RiskRegister
from app.schemas.risk_register import (
    RiskRegisterCreate,
    RiskRegisterUpdate,
    RiskRegisterHybridResponse,
)

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

# CREATE
@router.post("/")
def create_risk(
    risk: RiskRegisterCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_risk = RiskRegister(
        **risk.dict(),
        created_by=current_user["id"],
        created_on=datetime.utcnow(),
        is_deleted=0
    )

    db.add(db_risk)
    db.commit()
    db.refresh(db_risk)

    return success_response(build_hybrid_response(db_risk))

# Get ALL
@router.get("/")
def get_risks(db: Session = Depends(get_db)):
    risks = db.query(RiskRegister).filter(
        RiskRegister.is_deleted == 0
    ).all()

    response_list = [build_hybrid_response(r) for r in risks]
    return success_response(response_list)

# Get by ID
@router.get("/{risk_id}")
def get_risk(risk_id: int, db: Session = Depends(get_db)):
    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    return success_response(build_hybrid_response(risk))

# UPDATE
@router.put("/{risk_id}")
def update_risk(
    risk_id: int,
    risk_update: RiskRegisterUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    update_data = risk_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(risk, key, value)

    risk.modified_by = current_user["id"]
    risk.modified_on = datetime.utcnow()

    db.commit()
    db.refresh(risk)

    return success_response(build_hybrid_response(risk))

# SOFT DELETE
@router.delete("/{risk_id}")
def delete_risk(risk_id: int, db: Session = Depends(get_db)):
    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_id
    ).first()

    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    risk.is_deleted = 1
    db.commit()

    return success_response({
        "risk_register_id": risk.risk_register_id,
        "message": "Risk deleted successfully"
    })