from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RiskTreatmentCreate(BaseModel):
    risk_description_id: int
    risk_register_id: Optional[int] = None
    risk_id: Optional[str] = None

    action_plan: str
    action_owner_id: int

    target_date: Optional[datetime] = None
    progress: Optional[float] = None
    action_status_id: Optional[int] = None
    next_followup_date: Optional[datetime] = None
    
class RiskTreatmentUpdate(BaseModel):
    action_plan: Optional[str] = None
    progress: Optional[float] = None
    action_status_id: Optional[int] = None
    target_date: Optional[datetime] = None
    next_followup_date: Optional[datetime] = None
    
class RiskTreatmentHybridResponse(BaseModel):
    risk_treatment_id: int
    risk_description_id: int
    risk_register_id: Optional[int]

    risk_name: Optional[str]
    action_plan: str

    action_owner_id: int
    action_owner_name: Optional[str]

    target_date: Optional[datetime]
    progress: Optional[float]
    action_status_id: Optional[int]
    next_followup_date: Optional[datetime]

    is_deleted: int
    created_on: Optional[datetime]

    class Config:
        from_attributes = True



# for the Get Risk by risk_id
# class RiskRegisterResponse(BaseModel):
#     risk_register: RiskRegisterHybridResponse
#     risk_description: RiskDescriptionHybridResponse
#     treatments: list[RiskTreatmentHybridResponse]

#     class Config:
#         from_attributes = True
        
        

# get by risk_description_id
# class RiskDescriptionResponse(BaseModel):

#     risk_description: RiskDescriptionHybridResponse
#     treatments: list[RiskTreatmentHybridResponse]

#     class Config:
#         from_attributes = True

        
