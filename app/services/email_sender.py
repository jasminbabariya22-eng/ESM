import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from sqlalchemy import text
import traceback


def send_email(db: Session, job):

    server = db.execute(text("""
        SELECT *
        FROM ers.email_server
        WHERE email_server_id = :id
        AND is_deleted = 0
    """), {"id": job.email_server_id}).fetchone()

    if not server:
        return False

    try:
        msg = MIMEMultipart()

        # FROM
        msg["From"] = server.outgoing_email_user

        # -------- TO ----------
        to_list = [x.strip() for x in job.email_to.split(",")] if job.email_to else []

        # -------- CC ----------
        cc_list = [x.strip() for x in job.email_cc.split(",")] if job.email_cc else []

        # -------- BCC ----------
        bcc_list = [x.strip() for x in job.email_bcc.split(",")] if job.email_bcc else []

        # Add headers
        msg["To"] = ", ".join(to_list)
        msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = job.email_subject

        # Email body
        msg.attach(MIMEText(job.email_body or "", "html"))

        # Combine all receivers (VERY IMPORTANT)
        all_recipients = to_list + cc_list + bcc_list

        smtp = smtplib.SMTP(server.outgoing_server_ip, server.outgoing_email_port)

        if server.outgoing_email_encryption == 1:
            smtp.starttls()

        smtp.login(server.outgoing_email_user, server.outgoing_email_password)

        smtp.sendmail(
            server.outgoing_email_user,
            all_recipients,
            msg.as_string()
        )

        smtp.quit()

        return True

    except Exception as e:
        print("Email send error:")
        traceback.print_exc()
        return False
    
    
