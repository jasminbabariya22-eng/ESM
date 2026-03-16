from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.risk_action_followup import RiskActionFollowup
from app.schemas.risk_action_followup import (
    RiskActionFollowupCreate,
    RiskActionFollowupUpdate
)

from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from sqlalchemy.orm import joinedload
from app.models.user import User
from app.models.mst_status import Status

router = APIRouter(prefix="/risk-followup", tags=["Risk Followup"], dependencies=[Depends(get_current_user)])


def build_followup_response(obj):

    return {
        "followup_id": obj.followup_id,
        "reference_id": obj.reference_id,
        "module_name": obj.module_name,
        "remark": obj.remark,
        "progress": obj.progress,
        "status": obj.status,
        "next_followup_date": obj.next_followup_date,
        "created_on": obj.created_on,
        "created_by": obj.created_by
    }


def build_followup_response_for_create(obj):

    return {
        "followup_id": obj.followup_id,
        "reference_id": obj.reference_id,
        "module_name": obj.module_name,
        "remark": obj.remark,
        "progress": obj.progress,
        "status": obj.status,
        "status_name": obj.status_master.status_name if obj.status_master else None,
        "next_followup_date": obj.next_followup_date,
        "created_on": obj.created_on,
        "created_by": obj.created_by,
        "created_by_name": obj.created_user.log_id if obj.created_user else None
    }
    

# -------------------------
# CREATE
# -------------------------

@router.post("/")
def create_followup(
    payload: RiskActionFollowupCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:

        followup = RiskActionFollowup(**payload.dict())

        followup.created_by = current_user["id"]

        db.add(followup)
        db.commit()

        # reload with relationships
        followup = (
            db.query(RiskActionFollowup)
            .options(
                joinedload(RiskActionFollowup.created_user)
                .load_only(User.log_id),
                
                joinedload(RiskActionFollowup.status_master)
                .load_only(Status.status_name)
            )
            .filter(RiskActionFollowup.followup_id == followup.followup_id)
            .first()
        )

        return success_response(build_followup_response_for_create(followup))

    except Exception as e:
        db.rollback()
        return error_response(str(e), 400)


# -------------------------
# GET ALL
# -------------------------

@router.get("/")
def get_all_followups(db: Session = Depends(get_db)):

    try:
        data = db.query(RiskActionFollowup).all()

        return success_response([build_followup_response(f) for f in data])
    
    except Exception as e:
        return error_response(str(e), 400)


# -------------------------
# GET BY ID
# -------------------------

@router.get("/{followup_id}")
def get_followup(followup_id: int, db: Session = Depends(get_db)):
    
    try:
        data = db.query(RiskActionFollowup).filter(
            RiskActionFollowup.followup_id == followup_id
        ).first()

        if not data:
            raise HTTPException(status_code=404, detail="Followup not found")

        return success_response(build_followup_response(data))
    
    except Exception as e:
        return error_response(str(e), 400)
    
# Get by reference id (Based on Treatmnent ID or Risk Register ID or Risk Description ID)
@router.get("/reference_id/{reference_id}")
def get_followup_by_reference_id(reference_id: int, db: Session = Depends(get_db)):
    
    try:
        data = db.query(RiskActionFollowup).filter(
            RiskActionFollowup.reference_id == reference_id
        ).first()

        if not data:
            raise HTTPException(status_code=404, detail="Followup not found")

        return success_response(build_followup_response(data))
    
    except Exception as e:
        return error_response(str(e), 400)


# -------------------------
# UPDATE
# -------------------------

@router.put("/{followup_id}")
def update_followup(
    followup_id: int,
    payload: RiskActionFollowupUpdate,
    db: Session = Depends(get_db)
):
    try:
        followup = db.query(RiskActionFollowup).filter(
            RiskActionFollowup.followup_id == followup_id
        ).first()

        if not followup:
            raise HTTPException(status_code=404, detail="Followup not found")

        for key, value in payload.dict(exclude_unset=True).items():
            setattr(followup, key, value)

        db.commit()

        return success_response({
            "followup_id": followup_id,
            "message": "Followup updated successfully"
        })
        
    except Exception as e:
        db.rollback()
        return error_response(str(e), 400)


# -------------------------
# DELETE
# -------------------------

# @router.delete("/{followup_id}")
# def delete_followup(followup_id: int, db: Session = Depends(get_db)):
    
#     try:
#         followup = db.query(RiskActionFollowup).filter(
#             RiskActionFollowup.followup_id == followup_id
#         ).first()

#         if not followup:
#             raise HTTPException(status_code=404, detail="Followup not found")

#         db.delete(followup)
#         db.commit()

#         return success_response({
#             "followup_id": followup_id,
#             "message": "Followup deleted successfully"
#         })
        
#     except Exception as e:
#         db.rollback()
#         return error_response(str(e), 400)