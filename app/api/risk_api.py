from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.risk_schema import RiskSaveRequest, RiskUpdateRequest
from app.services.risk_service import save_risk, update_risk

from app.core.response import success_response, error_response
from app.core.dependencies import get_current_user
from app.models.risk_register import RiskRegister
from app.models.department import Department


router = APIRouter(prefix="/risk", tags=["Risk"])

@router.post("/save")
def create_risk(data: RiskSaveRequest, db: Session = Depends(get_db)):

    risk = save_risk(db, data)

    return {
        "message": "Risk created successfully",
        "risk_id": risk.risk_register_id
    }
    
@router.put("/update/{risk_id}")
def edit_risk(risk_id: int, data: RiskUpdateRequest, db: Session = Depends(get_db)):

    risk = update_risk(db, risk_id, data)

    if not risk:
        return {"message": "Risk not found"}

    return {"message": "Risk updated successfully"}


@router.get("/user/{user_id}")
def get_risk_by_user(user_id: int, db: Session = Depends(get_db)):

    risks = db.query(RiskRegister).filter(
        RiskRegister.risk_owner_id == user_id,
        RiskRegister.is_deleted == 0
    ).all()

    return risks