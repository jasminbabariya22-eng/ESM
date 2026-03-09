from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.mst_status import Status

from app.core.response import success_response, error_response


router = APIRouter()

# GET STATUS BY TYPE
@router.get("/types/{status_type}")
def get_status_by_type(status_type: str, db: Session = Depends(get_db)):
    
    try:
        statuses = db.query(Status).filter(
            Status.type == status_type,
            Status.is_deleted == 0
        ).all()

        return success_response([
            {
                "id": s.id,
                "status_name": s.status_name
            }
            for s in statuses
        ])
        
    except Exception as e:
        return error_response(str(e))
    

# Get STATUS BY ID
@router.get("/{status_id}")
def get_status_by_id(status_id: int, db: Session = Depends(get_db)):
    
    try:
        status = db.query(Status).filter(
            Status.id == status_id,
            Status.is_deleted == 0
        ).first()

        if not status:
            return error_response("Status not found")

        return success_response({
            "id": status.id,
            "status_name": status.status_name
        })
        
    except Exception as e:
        return error_response(str(e))


# Get Status by Status Name
@router.get("/name/{status_name}")
def get_status_by_status_name(status_name: str, db: Session = Depends(get_db)):
    
    try:
        status = db.query(Status).filter(
            Status.status_name == status_name,
            Status.is_deleted == 0
        ).first()

        if not status:
            return error_response("Status not found")

        return success_response({
            "id": status.id,
            "status_name": status.status_name
        })
        
    except Exception as e:
        return error_response(str(e))
