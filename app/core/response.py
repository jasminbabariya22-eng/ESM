from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def success_response(data=None, message="OK", status_code=200):
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "data": data,
            "Error": {
                "Success": True,
                "Error_message": message,
                "Code": status_code
            }
        })
    )


def error_response(message="Error", status_code=400):
    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "Error": {
                "Success": False,
                "Error_message": message,
                "Code": status_code
            }
        }
    )