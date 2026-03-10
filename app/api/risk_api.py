from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.risk_schema import RiskSaveRequest, RiskUpdateRequest, RiskDetailResponse
from app.core.response import success_response, error_response

from app.services.risk_service import get_risk_detail, update_risk, create_update_risk
from app.models.risk_register import RiskRegister


router = APIRouter(prefix="/risk", tags=["Risk"])


@router.post("/save")
def save_risk_api(
    data: RiskSaveRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    risk = create_update_risk(db, data, current_user)

    return {
        "message": "Risk saved successfully",
        "risk_register_id": risk.risk_register_id,
        "risk_id": risk.risk_id
    }


# -----------------------------
# UPDATE RISK
# -----------------------------

@router.put("/update/{risk_id}")
def edit_risk(risk_id: int, data: RiskUpdateRequest, db: Session = Depends(get_db)):

    risk = update_risk(db, risk_id, data)

    if not risk:
        return {"message": "Risk not found"}

    return {"message": "Risk updated successfully"}


# -----------------------------
# GET BY USER
# -----------------------------

@router.get("/user/{user_id}")
def get_risk_by_user(user_id: int, db: Session = Depends(get_db)):

    risks = db.query(RiskRegister).filter(
        RiskRegister.risk_owner_id == user_id,
        RiskRegister.is_deleted == 0
    ).all()

    return risks


@router.get("/{risk_id}")
def get_risk_detail_api(risk_id: int, db: Session = Depends(get_db)):

    data = get_risk_detail(db, risk_id)

    if not data:
        return error_response(message="Risk not found")

    return success_response(data=data)