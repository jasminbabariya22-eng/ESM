from pydantic import BaseModel


class LoginRequest(BaseModel):
    log_id: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


# from pydantic import BaseModel
# from typing import Optional


# class LoginRequest(BaseModel):
#     log_id: str
#     password: str

# class LoginResponse(BaseModel):
#     id: int
#     password: str
#     first_name: str
#     last_name: str
#     logid: str
#     department_id: Optional[int]
#     role_id: Optional[int]
#     user_type_id: Optional[int]
#     user_type: str
#     access_token: str