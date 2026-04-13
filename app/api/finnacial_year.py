from fastapi import APIRouter, Depends
from datetime import datetime
from app.core.database import get_db
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response


router = APIRouter(
    prefix="/financial-year",
    tags=["Financial Year"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/")
def get_financial_year():
    try:
        today = datetime.today()
        year = today.year
        month = today.month

        if month >= 4:
            start_year = year
            end_year = year + 1
        else:
            start_year = year - 1
            end_year = year

        financial_year = f"{start_year}-{end_year}"

        return success_response(
            data={"financial_year": financial_year, "current_data": today.strftime("%Y-%m-%d")}
        )

    except Exception as e:
        return error_response(error=str(e), error_code=400)