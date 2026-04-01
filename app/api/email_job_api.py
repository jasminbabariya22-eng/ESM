from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.models.email_job_mst import EmailJobMst

# IMPORTANT: router must exist
router = APIRouter(prefix="/email-job", tags=["Email Job"])


@router.post("/create")
def create_email_job(
    email_server_id: int,
    email_to: str,
    email_subject: str,
    email_body: str,
    db: Session = Depends(get_db)
):
    job = EmailJobMst(
        email_server_id=email_server_id,
        email_to=email_to,
        email_subject=email_subject,
        email_body=email_body,
        send_status=None,
        next_attempt_at=datetime.now(),
        created_on=datetime.now(),
        is_deleted=0
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "message": "Email job created successfully",
        "email_job_id": job.email_job_id
    }