from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone
from fastapi.responses import Response

from app.core.database import get_db
from app.models.risk_action_followup import RiskActionFollowup
from app.schemas.risk_action_followup import (
    RiskActionFollowupCreate,
    RiskActionFollowupUpdate
)

from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response


from app.models.user import User
from app.models.mst_status import Status
from app.models.risk_treatment import RiskTreatment
from app.models.risk_register import RiskRegister

router = APIRouter(prefix="/risk-followup", tags=["Risk Followup"], dependencies=[Depends(get_current_user)])


# def build_followup_response(obj):

#     return {
#         "followup_id": obj.followup_id,
#         "reference_id": obj.reference_id,
#         "module_name": obj.module_name,
#         "remark": obj.remark,
#         "progress": obj.progress,
#         "status": obj.status,
#         "next_followup_date": obj.next_followup_date,
#         "created_on": obj.created_on,
#         "created_by": obj.created_by
#     }
    
def build_followup_response(obj):
    return {
        "followup_id": obj.followup_id,
        "reference_id": obj.reference_id,
        "module_name": obj.module_name,
        "remark": obj.remark,
        "progress": obj.progress,
        "status": obj.status,
        "risk_status_name": obj.status_master.status_name if obj.status_master else None,
        "next_followup_date": obj.next_followup_date,
        "created_on": obj.created_on,
        "created_by": obj.created_by,
        "risk_owner_name": obj.created_user.log_id if obj.created_user else None,

        
        "file_name": obj.file_name,
        "file_extension": obj.file_extension,
        "file_type": obj.file_type,
        "has_file": True if obj.file_data else False,

        "file_download_url": f"/risk-followup/{obj.followup_id}/download-file" if obj.file_data else None
    }


def build_followup_response_for_create(obj):
    return {
        "followup_id": obj.followup_id,
        "reference_id": obj.reference_id,
        "module_name": obj.module_name,
        "remark": obj.remark,
        "progress": obj.progress,
        "status": obj.status,
        "risk_status_name": obj.status_master.status_name if obj.status_master else None,
        "next_followup_date": obj.next_followup_date,
        "created_on": obj.created_on,
        "created_by": obj.created_by,
        "risk_owner_name": obj.created_user.log_id if obj.created_user else None,

        "file_name": obj.file_name,
        "file_extension": obj.file_extension,
        "file_type": obj.file_type
    }
    
    
def update_risk_progress_from_followup(db, treatment_id):

    followups = db.query(RiskActionFollowup).filter(
        RiskActionFollowup.reference_id == treatment_id
    ).all()

    if not followups:
        return

    PROGRESS_MAP = {
        "0-25%": 12.5,
        "25-50%": 37.5,
        "50-75%": 62.5,
        "75-100%": 87.5,
        "100%": 100
    }

    values = [
        PROGRESS_MAP.get(f.progress, 0)
        for f in followups if f.progress
    ]

    if not values:
        return

    avg_progress = sum(values) / len(values)

    # Update treatment
    treatment = db.query(RiskTreatment).filter(
        RiskTreatment.risk_treatment_id == treatment_id
    ).first()

    if not treatment:
        return

    treatment.progress = round(avg_progress, 2)

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == treatment.risk_register_id
    ).first()

    if risk:
        risk.risk_progress = round(avg_progress, 2)

# -------------------------
# CREATE Followup and file upload
# -------------------------

# Seperate API

# @router.post("/")
# def create_followup(
#     payload: RiskActionFollowupCreate,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     try:

#         followup = RiskActionFollowup(**payload.dict())

#         followup.created_by = current_user["id"]

#         db.add(followup)
#         db.commit()

#         # reload with relationships
#         followup = (
#             db.query(RiskActionFollowup)
#             .options(
#                 joinedload(RiskActionFollowup.created_user)
#                 .load_only(User.log_id),
                
#                 joinedload(RiskActionFollowup.status_master)
#                 .load_only(Status.status_name)
#             )
#             .filter(RiskActionFollowup.followup_id == followup.followup_id)
#             .first()
#         )

#         return success_response(build_followup_response_for_create(followup))

#     except Exception as e:
#         db.rollback()
#         return error_response(str(e), 400)



# @router.post("/{followup_id}/upload-file")
# def upload_followup_file(
#     followup_id: int,
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db)
# ):
#     try:
#         followup = db.query(RiskActionFollowup).filter(
#             RiskActionFollowup.followup_id == followup_id
#         ).first()

#         if not followup:
#             return error_response("Followup not found", 404)

#         # Save file
#         followup.file_name = file.filename
#         followup.file_extension = file.filename.split(".")[-1] if "." in file.filename else None
#         followup.file_type = file.content_type
#         followup.file_data = file.file.read()

#         db.commit()

#         return success_response({
#             "message": "File uploaded successfully",
#             "followup_id": followup_id
#         })

#     except Exception as e:
#         db.rollback()
#         return error_response(str(e), 400)


# Combined API

@router.post("/")
async def create_followup_with_file(
    reference_id: int = Form(...),
    remark: str = Form(...),

    module_name: Optional[str] = Form(None),
    progress: Optional[str] = Form(None),
    status: Optional[int] = Form(None),
    next_followup_date: Optional[datetime] = Form(None),

    file: UploadFile = File(None),   

    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        if not reference_id or not remark:
            return error_response("Reference ID and Remark are required", 400)
        
        if not next_followup_date:
            next_followup_date = datetime.now(timezone.utc)
        
        followup = RiskActionFollowup(
            reference_id=reference_id,
            module_name=module_name,
            remark=remark,
            progress=progress,
            status=status,
            next_followup_date=next_followup_date,
            created_by=current_user["id"]
        )

        if file and file.filename:
            content = await file.read()

            followup.file_name = file.filename
            followup.file_extension = file.filename.rsplit(".", 1)[-1] if "." in file.filename else None
            followup.file_type = file.content_type
            followup.file_data = content

        db.add(followup)
        db.commit()
        db.refresh(followup)  
        
        if progress is not None:
            update_risk_progress_from_followup(db, reference_id)
            db.commit()

        followup = (
            db.query(RiskActionFollowup)
            .options(
                joinedload(RiskActionFollowup.created_user).load_only(User.log_id),
                joinedload(RiskActionFollowup.status_master).load_only(Status.status_name)
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
        data = (
            db.query(RiskActionFollowup)
            .options(
                joinedload(RiskActionFollowup.created_user)
                .load_only(User.log_id),
                
                joinedload(RiskActionFollowup.status_master)
                .load_only(Status.status_name)
            )
            .filter(RiskActionFollowup.followup_id == followup_id)
            .first()
        )

        if not data:
            raise HTTPException(status_code=404, detail="Followup not found")

        return success_response(build_followup_response(data))

    except Exception as e:
        return error_response(str(e), 400)

  
 ## Download File
 
@router.get("/download-file/{followup_id}")
def download_file(followup_id: int, db: Session = Depends(get_db)):
    followup = db.query(RiskActionFollowup).filter(
        RiskActionFollowup.followup_id == followup_id
    ).first()

    if not followup or not followup.file_data:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(
        content=followup.file_data,
        media_type=followup.file_type,
        headers={
            "Content-Disposition": f"attachment; filename={followup.file_name}"
        }
    )     
    

## Combined API (If you want to return either a file or JSON based on whether a file exists)

# from fastapi.responses import Response, JSONResponse

# @router.get("/{followup_id}")
# def get_followup(followup_id: int, db: Session = Depends(get_db)):
#     try:
#         data = (
#             db.query(RiskActionFollowup)
#             .options(
#                 joinedload(RiskActionFollowup.created_user).load_only(User.log_id),
#                 joinedload(RiskActionFollowup.status_master).load_only(Status.status_name)
#             )
#             .filter(RiskActionFollowup.followup_id == followup_id)
#             .first()
#         )

#         if not data:
#             raise HTTPException(status_code=404, detail="Followup not found")

#         # If file exists → return file
#         if data.file_data:
#             return Response(
#                 content=data.file_data,
#                 media_type=data.file_type,
#                 headers={
#                     "Content-Disposition": f"attachment; filename={data.file_name}"
#                 }
#             )

#         # Otherwise → return JSON
#         return JSONResponse(
#             content=success_response(build_followup_response(data))
#         )

#     except Exception as e:
#         return error_response(str(e), 400)



#---------------------
# Get by reference id (Based on Treatmnent ID or Risk Register ID or Risk Description ID)
#--------------------

@router.get("/reference_id/{reference_id}")
def get_followup_by_reference_id(reference_id: int, db: Session = Depends(get_db)):
    
    try:
        data = db.query(RiskActionFollowup).filter(
            RiskActionFollowup.reference_id == reference_id
        ).all()

        if not data:
            raise HTTPException(status_code=404, detail="Followup not found")
    
        response_list = [build_followup_response(d) for d in data]
        return success_response(response_list)
    
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


        if payload.progress is not None:
            update_risk_progress_from_followup(db, followup.reference_id)
    
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