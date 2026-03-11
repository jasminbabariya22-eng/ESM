from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.risk_schema import RiskSaveRequest, RiskUpdateRequest, RiskDetailResponse
from app.core.response import success_response, error_response

from app.services.risk_service import create_update_risk
from app.services.risk_service import get_risk_by_user


router = APIRouter(prefix="/risk", tags=["Risk"])


# CREATE OR UPDATE RISK
@router.post("/save")
def save_risk_api(
    data: RiskSaveRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        risk = create_update_risk(db, data, current_user)

        return success_response(data=data, message="Risk saved successfully")
    
    except Exception as e:
        return error_response(str(e), 400)


# # -----------------------------
# # UPDATE RISK
# # -----------------------------

# @router.put("/update/{risk_id}")
# def edit_risk(risk_id: int, data: RiskUpdateRequest, db: Session = Depends(get_db)):

#     risk = update_risk(db, risk_id, data)

#     if not risk:
#         return {"message": "Risk not found"}

#     return {"message": "Risk updated successfully"}


# -----------------------------
# GET BY USER
# -----------------------------

@router.get("/Users")
def get_my_risks(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    risks = get_risk_by_user(db, current_user["id"])

    return success_response(data=risks)


# @router.get("/{risk_id}")
# def get_risk_detail_api(risk_id: int, db: Session = Depends(get_db)):

#     data = get_risk_detail(db, risk_id)

#     if not data:
#         return error_response(message="Risk not found")

#     return success_response(data=data)