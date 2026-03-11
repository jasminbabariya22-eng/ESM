from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.schemas.risk_approval import RiskApprovalRequest
from app.services.risk_approval import approve_risk

router = APIRouter(prefix="/approval", tags=["Approval"], dependencies=[Depends(get_current_user)])

@router.post("/approve")
def approve_risk_api(
    data: RiskApprovalRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    risk = approve_risk(db, data, current_user["id"])

    return success_response(
        message="Approval updated successfully"
    )