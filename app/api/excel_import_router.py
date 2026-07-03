from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from tempfile import NamedTemporaryFile
import shutil
import os

from app.core.database import get_db
from app.core.response import success_response, error_response
from app.core.dependencies import get_current_user
from app.services.Excel.excel_parser import load_excel
from app.services.Excel.db_import import run_import

router = APIRouter(prefix="/excel", tags=["Excel Import"])


@router.post("/import")
async def import_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
    # current_user = Depends(get_current_user)
):
    # Validate file extension
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx files are allowed."
        )

    temp_path = None

    try:
        with NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:      # Save uploaded file
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name

        registers = load_excel(temp_path)              # Save uploaded file

        result = run_import(db, registers)         # Import into DB

        return {
            "success": True,
            "message": "Excel imported successfully.",
            "summary": {
                "users": len(result["user_map"]),
                "risk_registers": len(result["risk_register_map"]),
                "risk_descriptions": len(result["description_map"]),
                "risk_treatments": len(result["treatment_map"]),
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)