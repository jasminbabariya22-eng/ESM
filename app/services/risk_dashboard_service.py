from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.mst_status import Status
from datetime import datetime, timedelta

from app.models.risk_register import RiskRegister
from app.models.department import Department
from app.models.user import User
from app.models.mst_status import Status

# KPI
def get_dashboard_summary_service(db: Session, start_date: datetime, end_date: datetime):
    result = db.query(
        func.count(RiskRegister.risk_register_id).label("total"),
        
        
        func.count().filter(Status.status_name == "New").label("New"),
        func.count().filter(Status.status_name == "Open").label("Open"),  
        func.count().filter(Status.status_name == "In Progress").label("in_progress"),
        func.count().filter(Status.status_name == "Closed").label("Closed"),
        func.count().filter(Status.status_name == "Pending").label("Pending"),
        func.count().filter(Status.status_name == "Completed").label("Completed"),  
        func.count().filter(Status.status_name == "Approved").label("Approved"),  
        func.count().filter(Status.status_name == "Rejected").label("Rejected")  
    ).join(
        Status, RiskRegister.risk_status == Status.id
    ).filter(
        RiskRegister.is_deleted == 0,
        Status.is_deleted == 0,
        RiskRegister.created_on >= start_date,
        RiskRegister.created_on <= end_date
    ).first()

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total": result.total or 0,
        "New": result.New or 0,
        "Open": result.Open or 0,  
        "Closed": result.Closed or 0,
        "in_progress": result.in_progress or 0,
        "Pending": result.Pending or 0,
        "Completed": result.Completed or 0,  
        "Approved": result.Approved or 0,  
        "Rejected": result.Rejected or 0  
    }
    
    
# Dept wise risk count (Bar Chart)
def department_wise_risk_count(db: Session, start_date: datetime, end_date: datetime):

    results = db.query(
        Department.dept_name.label("department"),
        func.count(RiskRegister.risk_register_id).label("total")
    ).join(
        Department, RiskRegister.dept_id == Department.id
    ).filter(
        RiskRegister.is_deleted == 0,
        Department.is_deleted == 0,
        RiskRegister.created_on >= start_date,
        RiskRegister.created_on < end_date + timedelta(days=1)
    ).group_by(
        Department.dept_name
    ).order_by(
        Department.dept_name
    ).all()

    return [
        {
            "department": row.department,
            "total": row.total
        }
        for row in results
    ]
    
    
    
# User Wise Risk Count (Bar Chart)
def user_wise_risk_count(db: Session, start_date: datetime, end_date: datetime):

    results = db.query(
        func.concat(User.first_name, " ", User.last_name).label("employee_name"),
        func.count(RiskRegister.risk_register_id).label("total")
    ).join(
        RiskRegister, RiskRegister.risk_owner_id == User.id
    ).filter(
        RiskRegister.is_deleted == 0,
        User.is_deleted == 0,
        RiskRegister.created_on >= start_date,
        RiskRegister.created_on < end_date + timedelta(days=1)
    ).group_by(
        User.id
    ).order_by(
        func.count(RiskRegister.risk_register_id).desc()
    ).all()

    return [
        {
            "employee_name": row.employee_name,
            "total": row.total
        }
        for row in results
    ]
    


# Status wise Risk Count (Pie Chart)
def status_wise_Risk_Count(db: Session, start_date: datetime, end_date: datetime):

    results = db.query(
        Status.status_name.label("status"),
        func.count(RiskRegister.risk_register_id).label("total")
    ).join(
        Status, RiskRegister.risk_status == Status.id
    ).filter(
        RiskRegister.is_deleted == 0,
        Status.is_deleted == 0,
        RiskRegister.created_on >= start_date,
        RiskRegister.created_on < end_date + timedelta(days=1)
    ).group_by(
        Status.status_name
    ).order_by(
        func.count(RiskRegister.risk_register_id).desc()
    ).all()

    return [
        {
            "status": row.status,
            "total": row.total
        }
        for row in results
    ]
    

# Dept wise Progress (Horizontal Bar Chart)
def department_wise_progress(db: Session, start_date, end_date):

    results = db.query(
        Department.dept_name.label("department"),
        func.avg(RiskRegister.risk_progress).label("progress")
    ).join(
        Department, RiskRegister.dept_id == Department.id
    ).filter(
        RiskRegister.is_deleted == 0,
        Department.is_deleted == 0,
        RiskRegister.created_on >= start_date,
        RiskRegister.created_on < end_date + timedelta(days=1)
    ).group_by(
        Department.dept_name
    ).order_by(
        func.avg(RiskRegister.risk_progress).desc()
    ).all()

    return [
        {
            "department": row.department,
            "progress": round(row.progress or 0, 2)
        }
        for row in results
    ]