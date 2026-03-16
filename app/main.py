from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.api.auth import router as auth_router
from app.api.user import router as user_router
#from app.schemas.user import UserResponse
from typing import List

# Import logging
from fastapi import Request
from app.core.logger import logger
import time
import json
from starlette.responses import Response
from fastapi.responses import JSONResponse

from app.api.department import router as dept_router
from app.api.role import router as role_router
from app.api.user_type import router as user_type_router

from app.api.risk_register import router as risk_registery_router
from app.api.risk_description import router as risk_description_router
from app.api.risk_treatment import router as risk_treatment_router

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

from app.api.Status import router as status_router
from app.api.risk_api import router as risk_router
from app.api.risk_download_excel import router as risk_excel_router

from app.api.risk_action_followup import router as risk_action_followup_router
from app.api.approval import router as approval_router

app = FastAPI()

# Authenticate and get current user
app.include_router(auth_router)
app.include_router(user_router)

# Include Master Data APIs
app.include_router(dept_router)
app.include_router(role_router)
app.include_router(user_type_router)

# Full Risk Register APIs
app.include_router(risk_router)

# Risk Excel Download API
app.include_router(risk_excel_router)

# Approval and Status APIs
app.include_router(status_router)
app.include_router(risk_action_followup_router)
app.include_router(approval_router)


# Risk Register APIs
app.include_router(risk_registery_router)
app.include_router(risk_description_router)
app.include_router(risk_treatment_router)


app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


## Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Read request body safely
    request_body = await request.body()
    try:
        request_body_text = request_body.decode("utf-8") if request_body else ""
    except UnicodeDecodeError:
        request_body_text = "<binary request>"

    # Hide password if present
    if "password" in request_body_text:
        request_body_text = "HIDDEN"

    logger.info(
        f"REQUEST | {request.method} {request.url} | BODY: {request_body_text}"
    )

    # Process request
    response = await call_next(request)

    # Capture response body
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    try:
        response_body_text = response_body.decode("utf-8")
    except UnicodeDecodeError:
        response_body_text = "<binary request>"

    process_time = time.time() - start_time

    logger.info(
        f"RESPONSE | {request.method} {request.url} | "
        f"STATUS: {response.status_code} | "
        f"TIME: {process_time:.4f}s | "
        f"BODY: {response_body_text}"
    )

    # Re-create response (important!)
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )
    


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"ERROR | {request.method} {request.url} | MESSAGE: {str(exc)}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )