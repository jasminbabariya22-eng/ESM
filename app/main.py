from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.api.auth import router as auth_router
from app.api.user import router as user_router
#from app.schemas.user import UserResponse
from typing import List

from app.api.department import router as dept_router
from app.api.role import router as role_router
from app.api.user_type import router as user_type_router

from app.api.risk_register import router as risk_router

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

app = FastAPI()
app.include_router(auth_router)
app.include_router(user_router)

app.include_router(dept_router)
app.include_router(role_router)
app.include_router(user_type_router)

app.include_router(risk_router)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# @app.get("/users", response_model=List[UserResponse])
# def get_users(db: Session = Depends(get_db)):
#     return db.query(User).limit(5).all()