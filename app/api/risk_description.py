from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success_response

from app.models.risk_description import RiskDescription
from app.schemas.risk_description import (
    RiskDescriptionCreate,
    RiskDescriptionUpdate,
    RiskDescriptionHybridResponse,
)

router = APIRouter(
    prefix="/risk-description",
    tags=["Risk Description"],
    dependencies=[Depends(get_current_user)]
)

def build_hybrid_response(desc):
    return {
        "risk_description_id": desc.risk_description_id,
        "risk_register_id": desc.risk_register_id,
        "risk_id": desc.risk_id,
        "risk_name": desc.risk_register.risk_name if desc.risk_register else None,

        "risk_description": desc.risk_description,

        "inherent_risk_likelihood_id": desc.inherent_risk_likelihood_id,
        "inherent_risk_impact_id": desc.inherent_risk_impact_id,

        "mitigation": desc.mitigation,

        "current_risk_likelihood_id": desc.current_risk_likelihood_id,
        "current_risk_impact_id": desc.current_risk_impact_id,

        "is_deleted": desc.is_deleted,
        "created_on": desc.created_on
    }

# CREATE
@router.post("/")
def create_description(
    desc: RiskDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_desc = RiskDescription(
        **desc.dict(),
        created_by=current_user["id"],
        created_on=datetime.utcnow(),
        is_deleted=0
    )

    db.add(db_desc)
    db.commit()
    db.refresh(db_desc)

    return success_response(build_hybrid_response(db_desc))

# Get ALL
@router.get("/")
def get_descriptions(db: Session = Depends(get_db)):
    descriptions = db.query(RiskDescription).filter(
        RiskDescription.is_deleted == 0
    ).all()

    response_list = [build_hybrid_response(d) for d in descriptions]
    return success_response(response_list)

# Get BY ID
@router.get("/{desc_id}", response_model=RiskDescriptionHybridResponse)
def get_description(desc_id: int, db: Session = Depends(get_db)):
    desc = db.query(RiskDescription).filter(
        RiskDescription.risk_description_id == desc_id,
        RiskDescription.is_deleted == 0
    ).first()

    if not desc:
        raise HTTPException(status_code=404, detail="Risk Description not found")

    return success_response(build_hybrid_response(desc))

# UPDATE
@router.put("/{desc_id}", response_model=RiskDescriptionHybridResponse)
def update_description(
    desc_id: int,
    desc_update: RiskDescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    desc = db.query(RiskDescription).filter(
        RiskDescription.risk_description_id == desc_id,
        RiskDescription.is_deleted == 0
    ).first()

    if not desc:
        raise HTTPException(status_code=404, detail="Risk Description not found")

    update_data = desc_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(desc, key, value)

    desc.modified_by = current_user["id"]
    desc.modified_on = datetime.utcnow()

    db.commit()
    db.refresh(desc)

    return success_response(build_hybrid_response(desc))

# SOFT DELETE
@router.delete("/{desc_id}")
def delete_description(desc_id: int, db: Session = Depends(get_db)):
    desc = db.query(RiskDescription).filter(
        RiskDescription.risk_description_id == desc_id
    ).first()

    if not desc:
        raise HTTPException(status_code=404, detail="Risk Description not found")

    desc.is_deleted = 1
    db.commit()

    return success_response({
        "risk_description_id": desc.risk_description_id,
        "message": "Risk Description deleted successfully"
    })