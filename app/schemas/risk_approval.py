from pydantic import BaseModel
from typing import Optional
from app.schemas.risk_register import RiskRegisterCreate, RiskRegisterUpdate, RiskRegisterHybridResponse


class RiskApprovalRequest(BaseModel):

    risk_register_id: int
    approval_level: int
    approval_status_id: int
    remark: Optional[str] = None