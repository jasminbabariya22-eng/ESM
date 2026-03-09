from pydantic import BaseModel
from typing import List, Optional

class RiskRegister(BaseModel):
    id: int = 0
    risk_title: str
    risk_status: int

class RiskDescription(BaseModel):
    id: int = 0
    description: str

class RiskTreatment(BaseModel):
    treatment: str
    owner_id: int

class RiskRequest(BaseModel):
    risk_register: RiskRegister
    risk_description: RiskDescription
    risk_treatment: List[RiskTreatment]

class ApprovalRequest(BaseModel):
    risk_id: int
    status: str
    approved_by: int
    remark: Optional[str]