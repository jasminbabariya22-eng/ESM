from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# -------- CREATE --------
class UserCreate(BaseModel):
    #id: int = 0
    log_id: str
    password: str
    first_name: str
    last_name: str
    email: EmailStr
    country: str
    status: str
    address: str
    contact_no: str
    role_id: Optional[int] = None
    dept_id: Optional[int] = None
    user_type_id: Optional[int] = None


# -------- UPDATE --------
class UserUpdate(BaseModel):
    log_id: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    country: Optional[str] = None
    status: Optional[str] = None
    role_id: Optional[int] = None
    dept_id: Optional[int] = None
    user_type_id: Optional[int] = None


# -------- RESPONSE --------
class UserResponse(BaseModel):
    id: int
    log_id: str
    password: str
    first_name: str
    last_name: str
    email: str
    country: str
    status: str
    role_id: Optional[int]
    dept_id: Optional[int]
    user_type_id: Optional[int]
    is_deleted: int
    created_on: Optional[datetime]
    
class UserHybridResponse(BaseModel):
    id: int
    log_id: str
    password: str
    first_name: str
    last_name: str
    email: str
    country: str
    status: str

    department_id: Optional[int]
    department_name: Optional[str]

    role_id: Optional[int]
    role_name: Optional[str]

    user_type_id: Optional[int]
    user_type_name: Optional[str]

    is_deleted: int
    created_on: Optional[datetime]


    class Config:
        from_attributes = True