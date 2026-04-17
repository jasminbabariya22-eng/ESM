from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.responses import StreamingResponse

from sqlalchemy.inspection import inspect

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.risk_schema import RiskSaveRequest
from app.core.response import success_response, error_response

from app.services.risk_service import create_update_risk
from app.services.risk_service import get_risk_by_user,get_risk_by_dept,get_risk_by_risk_id, get_risk_by_description_id,get_risk_data_excel, get_followups_by_reference_id, get_risk_by_id


router = APIRouter(prefix="/risk", tags=["Risk"])


# for the model to dict
def model_to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


# CREATE OR UPDATE RISK
@router.post("/save")
def save_risk_api(
    data: RiskSaveRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        result = create_update_risk(db, data, current_user)

        risk_register = result["risk_register"]
        risk_description = result["risk_description"]
        treatments = result["risk_treatments"]

        if risk_description:
            risk_description["treatments"] = treatments
            risk_register["risk_descriptions"] = [risk_description]
        else:
            risk_register["risk_descriptions"] = []

        return success_response(
            data=[risk_register],
            message="Success"
        )

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
    try:

        risks = get_risk_by_user(db, current_user["id"])

        return success_response(data=risks)
    
    except Exception as e:
        return error_response(message=str(e), status_code=400)



# -----------------------------
# GET BY ID (Assign)
# -----------------------------

@router.get("/assign")
def get_risks_by_id(
    
    id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        risks = get_risk_by_id(db, id)

        return success_response(data=risks)
    except Exception as e:
        return error_response(message=str(e),status_code=400)
    

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


        return success_response(data=risk_description)

    except Exception as e:
        return error_response(message=str(e), status_code=400)
    
    
    
    
# ------------------------------------------------------------
# This API is use to export all information of registered risk in excel sheet
# Department wise sheet will be created for all department.
# Argument = Department ID, Optional
# -------------------------------------------------------------

@router.get(
    "/export-data",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Excel file"
        }
    }
)
def export_risk_excel(
    dept_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:

        risk_data = get_risk_data_excel(db,dept_id)

        if not risk_data:
            return error_response(message="Risk data not found", status_code=404)

        return StreamingResponse(
            risk_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=risk_report.xlsx"
            }
        )

    except Exception as e:
        return error_response(message=str(e), status_code=400)
    
    
    
# -----------------------------
# GET BY Refrence ID
# -----------------------------

@router.get("/refrence/{reference_id}")
def get_reference_by_reference_id(
    reference_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        reference = get_followups_by_reference_id(db, reference_id)
        if not reference:
            return error_response(message="Reference not found", status_code=404)
        
        return success_response(data=reference)
    
    except Exception as e:
        return error_response(message=str(e),status_code=400)