from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

from models import risk_register, risk_description, risk_treatment, risk_approval
from schemas.risk_schema import RiskRequest, ApprovalRequest

router = APIRouter(prefix="/risk", tags=["Risk"])


#Create or Update Risk
@router.post("/")
def create_update_risk(data: RiskRequest, db: Session = Depends(get_db)):

    try:

        # -----------------------------
        # 1️⃣ Risk Register
        # -----------------------------
        if data.risk_register.id == 0:

            reg = risk_register.RiskRegister(
                risk_title=data.risk_register.risk_title,
                risk_status=data.risk_register.risk_status
            )

            db.add(reg)
            db.commit()
            db.refresh(reg)

            risk_id = reg.id

        else:

            reg = db.query(risk_register.RiskRegister).filter(
                risk_register.RiskRegister.id == data.risk_register.id
            ).first()

            reg.risk_title = data.risk_register.risk_title
            reg.risk_status = data.risk_register.risk_status

            db.commit()

            risk_id = reg.id

        # -----------------------------
        # 2️⃣ Risk Description
        # -----------------------------

        if data.risk_description.id == 0:

            desc = risk_description.RiskDescription(
                risk_id=risk_id,
                description=data.risk_description.description
            )

            db.add(desc)

        else:

            desc = db.query(risk_description.RiskDescription).filter(
                risk_description.RiskDescription.id == data.risk_description.id
            ).first()

            desc.description = data.risk_description.description

        db.commit()

        # -----------------------------
        # 3️⃣ Risk Treatment
        # -----------------------------

        db.query(risk_treatment.RiskTreatment).filter(
            risk_treatment.RiskTreatment.risk_id == risk_id
        ).delete()

        for t in data.risk_treatment:

            treatment = risk_treatment.RiskTreatment(
                risk_id=risk_id,
                treatment=t.treatment,
                owner_id=t.owner_id
            )

            db.add(treatment)

        db.commit()

        return {
            "message": "Risk saved successfully",
            "risk_id": risk_id
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    
    
# Get Full Risk Details by Risk ID
@router.get("/{risk_id}")
def get_risk(risk_id: int, db: Session = Depends(get_db)):

    register = db.query(risk_register.RiskRegister).filter(
        risk_register.RiskRegister.id == risk_id
    ).first()

    description = db.query(risk_description.RiskDescription).filter(
        risk_description.RiskDescription.risk_id == risk_id
    ).first()

    treatments = db.query(risk_treatment.RiskTreatment).filter(
        risk_treatment.RiskTreatment.risk_id == risk_id
    ).all()

    return {
        "risk_register": register,
        "risk_description": description,
        "risk_treatment": treatments
    }