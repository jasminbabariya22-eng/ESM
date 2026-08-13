from pydantic import BaseModel
from typing import Optional
from app.schemas.risk_register import RiskRegisterCreate, RiskRegisterUpdate, RiskRegisterHybridResponse


# Schemas for Risk Approval operations, including request model for approval actions
class RiskApprovalRequest(BaseModel):

    risk_register_id: int
    approval_level: Optional[int] = None
    approval_status_id: Optional[int] = None
    remark: Optional[str] = None
    action: Optional[str] = None
    
class ForceApproveRequest(BaseModel):
    risk_register_id: int
    remark: Optional[str] = None