from pydantic import BaseModel
from typing import List

from app.schemas.risk_register import RiskRegisterCreate
from app.schemas.risk_description import RiskDescriptionCreate
from app.schemas.risk_treatment import RiskTreatmentCreate


class RiskSaveRequest(BaseModel):
    risk_register: RiskRegisterCreate
    risk_description: RiskDescriptionCreate
    risk_treatments: List[RiskTreatmentCreate]


class RiskUpdateRequest(BaseModel):
    risk_register_id: int
    risk_register: RiskRegisterCreate
    risk_description: RiskDescriptionCreate
    risk_treatments: List[RiskTreatmentCreate]