from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    log_id: str
    password: str

class LoginResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    logid: str
    department_id: Optional[int]
    role_id: Optional[int]
    user_type_id: Optional[int]
    user_type: str
    access_token: str