from pydantic import BaseModel
from typing import Optional

class DepartmentResponse(BaseModel):
    id: int
    dept_name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True