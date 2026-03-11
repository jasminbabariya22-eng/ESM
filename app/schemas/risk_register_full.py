from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RiskRegisterCreate(BaseModel):
    risk_register_id: Optional[str] = "0"
    risk_name: str
    dept_id: Optional[str] = "0"
    risk_owner_id: Optional[str] = "0"

    financial_year: Optional[str] = ""
    risk_status: Optional[str] = "0"
    risk_progress: Optional[str] = "0"

    is_active: Optional[str] = "0"
    
class RiskRegisterUpdate(BaseModel):

    risk_name: Optional[str] = ""
    dept_id: Optional[str] = "0"
    risk_owner_id: Optional[str] = "0"

    financial_year: Optional[str] = ""
    risk_status: Optional[str] = "0"
    risk_progress: Optional[str] = "0"

    is_active: Optional[str] = "0"
    
class RiskRegisterHybridResponse(BaseModel):
    risk_register_id: int
    risk_id: str
    risk_name: str

    dept_id: int
    department_name: Optional[str]

    risk_owner_id: int
    risk_owner_name: Optional[str]

    financial_year: Optional[str]
    risk_status: Optional[int]
    risk_progress: Optional[float]

    is_active: int
    is_deleted: int
    created_on: Optional[datetime]

    class Config:
        from_attributes = True
