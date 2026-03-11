from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.risk_schema import RiskSaveRequest, RiskUpdateRequest, RiskDetailResponse
from app.core.response import success_response, error_response

from app.services.risk_service import create_update_risk
from app.services.risk_service import get_risk_by_user,get_risk_by_dept,get_risk_by_risk_id


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



# -----------------------------
# GET BY DEPARTMENT ID
# -----------------------------

@router.get("/risks")
def get_my_dept_risks_by_dept_id(
    
    dept_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        risks = get_risk_by_dept(db, dept_id)

        return success_response(data=risks)
    except Exception as e:
        return error_response(message=str(e),status_code=500)
    
    
    

# -----------------------------
# GET BY Risk ID
# -----------------------------

@router.get("/risks_by_id/{risk_id}")
def get_my_dept_risks_by_risk_id(
    
    risk_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        risks = get_risk_by_risk_id(db, risk_id)

        return success_response(data=risks)
    except Exception as e:
        return error_response(message=str(e),status_code=500)