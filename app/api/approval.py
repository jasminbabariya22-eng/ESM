from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.schemas.risk_approval import RiskApprovalRequest
from app.services.risk_approval import approve_risk

from datetime import date
from app.models.user import User

router = APIRouter(prefix="/approval", tags=["Approval"], dependencies=[Depends(get_current_user)])


# Get Approval for existing Risk
# @router.post("/approve")
# def approve_risk_api(
#     data: RiskApprovalRequest,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user)
# ):

#     try:
#         risk = approve_risk(db, data, current_user["id"])

#         return success_response(
#             data=data
#         )
        
#     except Exception as e:
#         return error_response(str(e), 400)

@router.post("/approve")
def approve_risk_api(
    data: RiskApprovalRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        risk, status_name = approve_risk(db, data, current_user["id"])

        # ✅ Fetch user login_id
        user_obj = db.query(User).filter(
            User.id == current_user["id"]
        ).first()

        approval_by_name = user_obj.log_id if user_obj else None

        return success_response(
            data={
                "risk_register_id": data.risk_register_id,
                "approval_level": data.approval_level,
                "approval_status_id": data.approval_status_id,
                "risk_status_name": status_name,
                "approval_by_name": approval_by_name,   # ✅ added
                "risk_approval_on": date.today(),
                "remark": data.remark
            }
        )

    except Exception as e:
        return error_response(str(e), 400)