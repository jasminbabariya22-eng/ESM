from pydantic import BaseModel


class LoginRequest(BaseModel):
    log_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str