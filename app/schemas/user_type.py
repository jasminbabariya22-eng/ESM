from pydantic import BaseModel
from typing import Optional

class UserTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True