from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.risk_treatment import RiskTreatment
from app.schemas.risk_treatment import (
    RiskTreatmentCreate,
    RiskTreatmentUpdate,
    RiskTreatmentHybridResponse,
)

router = APIRouter(
    prefix="/risk-treatment",
    tags=["Risk Treatment"],
    dependencies=[Depends(get_current_user)]
)

def build_hybrid_response(t):
    return {
        "risk_treatment_id": t.risk_treatment_id,
        "risk_description_id": t.risk_description_id,
        "risk_register_id": t.risk_register_id,

        "risk_name": (
            t.risk_description.risk_register.risk_name
            if t.risk_description and t.risk_description.risk_register
            else None
        ),

        "action_plan": t.action_plan,

        "action_owner_id": t.action_owner_id,
        "action_owner_name": (
            f"{t.action_owner.first_name} {t.action_owner.last_name}"
            if t.action_owner else None
        ),

        "target_date": t.target_date,
        "progress": t.progress,
        "action_status_id": t.action_status_id,
        "next_followup_date": t.next_followup_date,

        "is_deleted": t.is_deleted,
        "created_on": t.created_on
    }
    

# CREATE
@router.post("/", response_model=RiskTreatmentHybridResponse)
def create_treatment(
    treatment: RiskTreatmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_treatment = RiskTreatment(
        **treatment.dict(),
        created_by=current_user["id"],
        created_on=datetime.utcnow(),
        is_deleted=0
    )

    db.add(db_treatment)
    db.commit()
    db.refresh(db_treatment)

    return build_hybrid_response(db_treatment)


# Get ALL
@router.get("/", response_model=List[RiskTreatmentHybridResponse])
def get_treatments(db: Session = Depends(get_db)):
    treatments = db.query(RiskTreatment).filter(
        RiskTreatment.is_deleted == 0
    ).all()

    return [build_hybrid_response(t) for t in treatments]


# Get BY ID
@router.get("/{treatment_id}", response_model=RiskTreatmentHybridResponse)
def get_treatment(treatment_id: int, db: Session = Depends(get_db)):
    treatment = db.query(RiskTreatment).filter(
        RiskTreatment.risk_treatment_id == treatment_id,
        RiskTreatment.is_deleted == 0
    ).first()

    if not treatment:
        raise HTTPException(status_code=404, detail="Risk Treatment not found")

    return build_hybrid_response(treatment)


# UPDATE
@router.put("/{treatment_id}", response_model=RiskTreatmentHybridResponse)
def update_treatment(
    treatment_id: int,
    treatment_update: RiskTreatmentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    treatment = db.query(RiskTreatment).filter(
        RiskTreatment.risk_treatment_id == treatment_id,
        RiskTreatment.is_deleted == 0
    ).first()

    if not treatment:
        raise HTTPException(status_code=404, detail="Risk Treatment not found")

    update_data = treatment_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(treatment, key, value)

    treatment.modified_by = current_user["id"]
    treatment.modified_on = datetime.utcnow()

    db.commit()
    db.refresh(treatment)

    return build_hybrid_response(treatment)


# DELETE (Soft Delete)
@router.delete("/{treatment_id}")
def delete_treatment(treatment_id: int, db: Session = Depends(get_db)):
    treatment = db.query(RiskTreatment).filter(
        RiskTreatment.risk_treatment_id == treatment_id
    ).first()

    if not treatment:
        raise HTTPException(status_code=404, detail="Risk Treatment not found")

    treatment.is_deleted = 1
    db.commit()

    return {"message": "Risk Treatment deleted successfully"}