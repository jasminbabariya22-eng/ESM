import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.email_sender import send_email


print("======================================")
print(" Email Worker Started Successfully ")
print(" Running every 10 second...")
print("======================================\n")


def email_worker():

    while True:

        db: Session = SessionLocal()

        try:
            jobs = db.execute(text("""
                SELECT *
                FROM ers.email_job_mst
                WHERE
                    is_deleted = 0
                    AND (
                        send_status IS NULL
                        OR send_status = 'FAILED'
                        OR send_status = 'New'
                    )
                    AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                ORDER BY email_job_id
                LIMIT 10
            """)).fetchall()

            if not jobs:
                print(f"[{datetime.now()}] No pending emails...")
                db.close()
                time.sleep(10)
                continue

            print(f"[{datetime.now()}] Found {len(jobs)} pending email(s)")

            for job in jobs:
                print(f"Sending Email Job ID: {job.email_job_id}")

                success = send_email(db, job)

                new_attempt = job.send_attempts + 1

                if success:
                    print(" Email sent successfully")

                    db.execute(text("""
                        UPDATE ers.email_job_mst
                        SET send_status = 'SUCCESS',
                            send_attempts = :attempt
                        WHERE email_job_id = :id
                    """), {"attempt": new_attempt, "id": job.email_job_id})

                else:
                    print(" Email failed")

                    if new_attempt >= job.total_attempts:
                        db.execute(text("""
                            UPDATE ers.email_job_mst
                            SET send_status = 'FAILED_FINAL',
                                send_attempts = :attempt
                            WHERE email_job_id = :id
                        """), {"attempt": new_attempt, "id": job.email_job_id})

                    else:
                        db.execute(text("""
                            UPDATE ers.email_job_mst
                            SET send_status = 'FAILED',
                                send_attempts = :attempt,
                                next_attempt_at = NOW() + (:delay || ' milliseconds')::interval
                            WHERE email_job_id = :id
                        """), {
                            "attempt": new_attempt,
                            "delay": job.attempt_delay,
                            "id": job.email_job_id
                        })

            db.commit()

        except Exception as e:
            print("Worker error:", e)

        finally:
            db.close()

        time.sleep(10)


if __name__ == "__main__":
    email_worker()