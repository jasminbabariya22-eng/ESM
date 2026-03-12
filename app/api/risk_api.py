from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.risk_schema import RiskSaveRequest, RiskUpdateRequest, RiskDetailResponse
from app.core.response import success_response, error_response

from app.schemas.risk_treatment import RiskRegisterResponse,RiskDescriptionResponse

from app.services.risk_service import create_update_risk
from app.services.risk_service import get_risk_by_user,get_risk_by_dept,get_risk_by_risk_id, get_risk_by_description_id


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
        return error_response(message=str(e),status_code=400)
    
    
    

# -----------------------------
# GET BY Risk ID
# -----------------------------

@router.get("/risks_by_id/{risk_id}")
def get_my_dept_risks_by_risk_id(
    
    risk_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        risks = get_risk_by_risk_id(db, risk_id)
        if not risks:
            return error_response(message="Risk not found", status_code=404)
        
        return success_response(data=risks)
    
    except Exception as e:
        return error_response(message=str(e),status_code=400)
    
    
# -----------------------------
# GET BY Risk Description ID
# -----------------------------

@router.get("/risk_by_description/{description_id}")
def get_risk_by_description(
    description_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:

        risk_description = get_risk_by_description_id(db, description_id)

        if not risk_description:
            return error_response(message="Risk Description not found", status_code=404)

        return success_response(
            data=RiskDescriptionResponse.model_validate({
                "risk_description": risk_description,
                "treatments": risk_description.treatments
            })
        )

    except Exception as e:
        return error_response(message=str(e), status_code=400)