from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RiskDescriptionCreate(BaseModel):
    risk_description: Optional[str] = None

    inherent_risk_likelihood_id: Optional[int] = None
    inherent_risk_impact_id: Optional[int] = None

    mitigation: Optional[str] = None

    current_risk_likelihood_id: Optional[int] = None
    current_risk_impact_id: Optional[int] = None
    
    
class RiskDescriptionUpdate(BaseModel):
    risk_description: Optional[str] = None
    mitigation: Optional[str] = None

    inherent_risk_likelihood_id: Optional[int] = None
    inherent_risk_impact_id: Optional[int] = None

    current_risk_likelihood_id: Optional[int] = None
    current_risk_impact_id: Optional[int] = None
    

class RiskDescriptionHybridResponse(BaseModel):
    risk_description_id: int
    risk_register_id: int
    risk_id: Optional[str]

    risk_name: Optional[str]

    risk_description: Optional[str]

    inherent_risk_likelihood_id: Optional[int]
    inherent_risk_impact_id: Optional[int]

    mitigation: Optional[str]

    current_risk_likelihood_id: Optional[int]
    current_risk_impact_id: Optional[int]

    is_deleted: int
    created_on: Optional[datetime]

    class Config:
        from_attributes = True