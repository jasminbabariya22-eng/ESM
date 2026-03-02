from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


def build_error_response(status_code: int, message: str, details=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "Error": {
                "Success": False,
                "Error_message": message,
                "Code": status_code
            }
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return build_error_response(exc.status_code, exc.detail)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return build_error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Validation Error"
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return build_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal Server Error"
    )