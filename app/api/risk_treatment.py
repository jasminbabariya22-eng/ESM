from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.models.risk_treatment import RiskTreatment
from app.schemas.risk_treatment import (
    RiskTreatmentCreate,
    RiskTreatmentUpdate,
    RiskTreatmentHybridResponse,
)
from app.models.risk_description import RiskDescription
from app.models.risk_register import RiskRegister
from app.models.risk_treatment_hist import RiskTreatmentHist

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
@router.post("/")
def create_risk_treatment(
    payload: RiskTreatmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Fetch risk_description
        risk_Description = db.query(RiskDescription).filter(
            RiskDescription.risk_description_id == payload.risk_description_id,
            RiskDescription.is_deleted == 0
        ).first()

        if not risk_Description:
            raise HTTPException(status_code=404, detail="Risk Description not found")

        # Fetch risk_id from risk_register
        risk_register = risk_Description.risk_register_id
        risk_id = risk_Description.risk_id

        # Insert into risk_treatment
        new_risk_treatment = RiskTreatment(
            risk_Description = payload.risk_description_id,
            risk_register_id = risk_register,
            risk_id = risk_id,
            
            action_plan = payload.action_plan,
            acttion_owner_id = payload.action_owner_id,    # may be change
            targeted_date = payload.target_date,
            progress = payload.progress,
            action_status_id = payload.action_status_id,
            next_followup_date = payload.next_followup_date,
            
            created_on = datetime.now(timezone.utc),
            created_by = current_user["id"],
            
            is_deleted = 0)

        db.add(new_risk_treatment)
        db.commit()
        db.refresh(new_risk_treatment)

        # Insert into history table
        hist = RiskTreatmentHist(
            risk_treatment_id=new_risk_treatment.risk_treatment_id,
            risk_description_id=new_risk_treatment.risk_description_id,
            risk_register_id=new_risk_treatment.risk_register_id,
            risk_id=new_risk_treatment.risk_id,
            
            action_plan=new_risk_treatment.action_plan,
            action_owner_id=new_risk_treatment.action_owner_id,
            
            targeted_date=new_risk_treatment.targeted_date,
            progress=new_risk_treatment.progress,
            
            action_status_id=new_risk_treatment.action_status_id,
            next_followup_date=new_risk_treatment.next_followup_date,

            created_by=new_risk_treatment.created_by,
            created_on=new_risk_treatment.created_on,
            modified_by=new_risk_treatment.modified_by,
            modified_on=new_risk_treatment.modified_on,
            is_deleted=new_risk_treatment.is_deleted
        )

        db.add(hist)
        db.commit()

        return success_response(build_hybrid_response(new_risk_treatment))
    
    except Exception as e:
        db.rollback()
        return error_response(str(e), 400)


# Get ALL
@router.get("/", response_model=List[RiskTreatmentHybridResponse])
def get_treatments(db: Session = Depends(get_db)):
    try:
        treatments = db.query(RiskTreatment).filter(
            RiskTreatment.is_deleted == 0
        ).all()

        response_list = [build_hybrid_response(t) for t in treatments]
        return success_response(response_list)
    
    except Exception as e:
        return error_response(str(e), 400)


# Get BY risk_treatment_id
@router.get("/risk_treatment_id/{risk_treatment_id}", response_model=RiskTreatmentHybridResponse)
def get_treatment(risk_treatment_id: int, db: Session = Depends(get_db)):
    try:
        treatment = db.query(RiskTreatment).filter(
            RiskTreatment.risk_treatment_id == risk_treatment_id,
            RiskTreatment.is_deleted == 0
        ).first()

        if not treatment:
            raise HTTPException(status_code=404, detail="Risk Treatment not found")

        response_list = [build_hybrid_response(treatment)]
        return success_response(response_list)

    except Exception as e:
        return error_response(str(e), 400)
    
# Get BY risk_Description_id
@router.get("/risk_description_id/{risk_description_id}", response_model=RiskTreatmentHybridResponse)
def get_treatment(risk_description_id: int, db: Session = Depends(get_db)):
    try:
        treatment = db.query(RiskTreatment).filter(
            RiskTreatment.risk_description_id == risk_description_id,
            RiskTreatment.is_deleted == 0
        ).first()

        if not treatment:
            raise HTTPException(status_code=404, detail="Risk Description not found")

        response_list = [build_hybrid_response(treatment)]
        return success_response(response_list)

    except Exception as e:
        return error_response(str(e), 400)


# Get by risk_id
@router.get("/{risk_id}")
def get_Risk_Treatment_by_risk_id(risk_id: str, db: Session = Depends(get_db)):
    try:
        if any(char.isdigit() for char in risk_id):            # if user fill complete risk_id with prefix and number

            risk = db.query(RiskTreatment).filter(
                RiskTreatment.risk_id == risk_id,
                RiskTreatment.is_deleted == 0
            ).first()

            if not risk:
                raise HTTPException(status_code=404, detail="Risk Treatment not found")

            response_list = [build_hybrid_response(risk)]
            return success_response(response_list)

        
        else:                                         # if user fill prfix only
            risks = db.query(RiskTreatment).filter(
                RiskTreatment.risk_id.like(f"{risk_id}%"),
                RiskTreatment.is_deleted == 0
            ).all()

            if not risks:
                raise HTTPException(status_code=404, detail="No Risk Treatments found")

            return success_response([build_hybrid_response(r) for r in risks])

    except Exception as e:
        return error_response(str(e), 400)



# UPDATE
@router.put("/{risk_treatment_id}")
def update_Risk_treatment(
    risk_treatment_id: int,
    payload: RiskTreatmentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        risk_tretment = db.query(RiskTreatment).filter(
            RiskTreatment.risk_treatment_id == risk_treatment_id,
            RiskTreatment.is_deleted == 0
        ).first()

        if not risk_tretment:
            return error_response("Risk Treatment not found", 404)

        update_data = payload.dict(exclude_unset=True)      # update fields

        for key, value in update_data.items():
            setattr(risk_tretment, key, value)

        risk_tretment.modified_by = current_user["id"]
        risk_tretment.modified_on = datetime.now(timezone.utc)

        db.flush()                                       # apply update before history insert

        # insert updated record into history table
        hist = RiskTreatmentHist(
            risk_treatment_id=risk_tretment.risk_treatment_id,
            risk_description_id=risk_tretment.risk_description_id,
            risk_register_id=risk_tretment.risk_register_id,
            risk_id=risk_tretment.risk_id,
            
            action_plan=risk_tretment.action_plan,
            action_owner_id=risk_tretment.action_owner_id,
            
            targeted_date=risk_tretment.targeted_date,
            progress=risk_tretment.progress,
            
            action_status_id=risk_tretment.action_status_id,
            next_followup_date=risk_tretment.next_followup_date,

            created_by=risk_tretment.created_by,
            created_on=risk_tretment.created_on,
            modified_by=risk_tretment.modified_by,
            modified_on=risk_tretment.modified_on,
            is_deleted=risk_tretment.is_deleted
        )

        db.add(hist)

        db.commit()
        db.refresh(risk_tretment)

        return success_response(
            {"risk_register_id": risk_tretment.risk_register_id,
            "message": "Risk updated successfully"}
        )

    except Exception as e:
        db.rollback()
        return error_response(str(e), 400)


# DELETE (Soft Delete)
@router.delete("/{treatment_id}")
def delete_treatment(treatment_id: int, db: Session = Depends(get_db)):
    try:
        treatment = db.query(RiskTreatment).filter(
            RiskTreatment.risk_treatment_id == treatment_id
        ).first()

        if not treatment:
            raise HTTPException(status_code=404, detail="Risk Treatment not found")

        treatment.is_deleted = 1
        
        hist = RiskTreatmentHist(
            risk_treatment_id = treatment.risk_treatment_id,
            risk_description_id = treatment.risk_description_id,
            risk_register_id = treatment.risk_register_id,
            risk_id = treatment.risk_id,
            action_plan = treatment.action_plan,
            action_owner_id = treatment.action_owner_id,
            TabErrorget_date = treatment.target_date,
            progress = treatment.progress,
            action_status_id = treatment.action_status_id,
            newt_followup_date = treatment.next_followup_date,
            crated_by = treatment.created_by,
            created_on = treatment.created_on,
            
            modified_by = treatment.modified_by,
            modified_on = treatment.modified_on,
            
            is_deleted = treatment.is_deleted)
        
        db.add(hist)
        db.commit()
        
        db.refresh(treatment)

        return success_response({
            "risk_treatment_id": treatment.risk_treatment_id,
            "message": "Risk Treatment deleted successfully"
        })
        
    except Exception as e:
        db.rollback()
        return error_response(str(e), 400)
    
# Get Treatment history by treatment id

@router.get("/history/{treatment_id}")
def get_treatment_history(treatment_id: int, db: Session = Depends(get_db)):
    try:
        history_records = db.query(RiskTreatmentHist).filter(
            RiskTreatmentHist.risk_treatment_id == treatment_id
        ).all()

        if not history_records:
            raise HTTPException(status_code=404, detail="History not found")

        return success_response(history_records)

    except Exception as e:
        return error_response(str(e), 400)