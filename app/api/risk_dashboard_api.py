from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.schemas.risk_dashboard import *
from app.services.risk_dashboard_service import *

router = APIRouter(prefix="/risk-dashboard", tags=["Risk Dashboard"])


# KPI
@router.get("/summary", response_model=RiskDashboardSummaryResponse)
def get_dashboard_summary(
    start_date: str = Query(..., description="Start Date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End Date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    try:

        if not start_date or not end_date:
            raise ValueError("Start date and end date are required")

        start_date_obj = datetime.fromisoformat(start_date)
        end_date_obj = datetime.fromisoformat(end_date)

        return success_response(
            get_dashboard_summary_service(db, start_date_obj, end_date_obj)
        )

    except ValueError as e:
        return error_response(str(e), 400)
    

# Department wise Risk Count
@router.get("/department-wise-Bar", response_model=List[DepartmentWiseRiskResponse])
def get_department_wise_risk(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    try:
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

        return success_response(
            department_wise_risk_count(db, start_date, end_date)
        )

    except ValueError as e:
        return error_response(str(e), 400)
    
    
    
# User wise Risk Count

@router.get("/User-wise-Bar", response_model=List[EmployeeWiseRiskResponse])
def get_employee_wise_risk(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    try:
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

        return success_response(
            user_wise_risk_count(db, start_date, end_date)
        )

    except ValueError as e:
        return error_response(str(e), 400)



  
# Staus wise Risk Count

@router.get("/status-wise-pie", response_model=List[StatusWisePieResponse])
def get_status_wise_pie(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    try:
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

        return success_response(
            status_wise_Risk_Count(db, start_date, end_date)
        )

    except ValueError as e:
        return error_response(str(e), 400)
    
    
# Dept wise progress
@router.get("/department-wise-progress-HBar", response_model=DeptartmentwiseprogressResponse)
def get_department_wise_progress(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    try:
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

        return success_response(
            department_wise_progress(db, start_date, end_date)
        )

    except ValueError as e:
        return error_response(str(e), 400)
