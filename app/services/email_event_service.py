from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.core.config import settings

from app.core.email_templates import build_email_template

from app.models.email_job_mst import EmailJobMst
from app.models.risk_register import RiskRegister

SCHEMA = settings.DB_SCHEMA

def get_emails_by_user_ids(db, user_ids):
    user_ids = list(set([uid for uid in user_ids if uid]))

    if not user_ids:
        print("No user IDs")
        return []

    result = db.execute(text("""
        SELECT email
        FROM ers.mst_users
        WHERE id = ANY(:ids)
        AND is_deleted = 0
    """), {"ids": user_ids}).fetchall()

    emails = [r.email for r in result if r.email]

    print("Emails fetched:", emails)

    return emails


# def get_department_head(db, dept_id):
#     result = db.execute(text("""
#         SELECT head_id
#         FROM mst_department
#         WHERE id = :id
#     """), {"id": dept_id}).fetchone()

#     return result.head_id if result else None


# ROLE BASED (BY NAME FROM DB)
def get_users_by_role_name(db, role_name):
    result = db.execute(text("""
        SELECT u.email
        FROM ers.mst_users u
        JOIN ers.mst_user_role r ON r.id = u.role_id
        WHERE r.name = :role_name
        AND u.is_deleted = 0
        AND r.is_deleted = 0
    """), {"role_name": role_name}).fetchall()

    return [r.email for r in result if r.email]


def create_email_job(db, to_list, cc_list, subject, body, created_by=1):
    
    if not to_list:
        print("No TO emails found. Skipping email job.")
        return

    job = EmailJobMst(
        email_server_id=1,
        email_to=",".join(set(to_list)),
        email_cc=",".join(set(cc_list)),
        email_subject=subject,
        email_type = "HTML",
        email_body=body,
        send_status="New",
        next_attempt_at=datetime.now(),
        created_on=datetime.now(),
        created_by = created_by,   # Assuming the email is triggered by the risk owner. Adjust as needed.
        is_deleted=0
    )

    db.add(job)
    db.commit()
    
    print("Email job inserted")


# EVENT 1: RISK CREATED

def send_risk_created_email(db: Session, risk_register_id: int):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_register_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        return

    to_emails = get_emails_by_user_ids(db, [risk.risk_owner_id])

    fh = get_users_by_role_name(db, "FUNCTION_HEAD")
    rm = get_users_by_role_name(db, "RISK_MANAGER")
    rh = get_users_by_role_name(db, "RISK_HEAD")

    cc_emails = list(set(fh + rm + rh) - set(to_emails))

    subject = f"[ERS] New Risk Created - {risk.risk_id}"

    content = f"""
    <p>Dear User,</p>

    <p>A new risk has been created in the system. Details are as follows:</p>

    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
        <tr><td><b>Risk ID</b></td><td>{risk.risk_id}</td></tr>
        <tr><td><b>Risk Name</b></td><td>{risk.risk_name}</td></tr>
        <tr><td><b>Financial Year</b></td><td>{risk.financial_year}</td></tr>
    </table>

    <p>Please review the risk in the system.</p>

    <p>Regards,<br>ERS Team</p>
    """

    body = build_email_template("New Risk Created", content)

    create_email_job(db, to_emails, cc_emails, subject, body, created_by=risk.risk_owner_id)


# EVENT 2: FUNCTION HEAD APPROVAL

def send_function_head_approval_email(db: Session, risk_register_id: int):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_register_id
    ).first()

    if not risk:
        return

    owner = get_emails_by_user_ids(db, [risk.risk_owner_id])
    rm = get_users_by_role_name(db, "RISK_MANAGER")
    rh = get_users_by_role_name(db, "RISK_HEAD")

    to_emails = list(set(owner + rm + rh))

    fh = get_users_by_role_name(db, "FUNCTION_HEAD")
    cc_emails = list(set(fh) - set(to_emails))

    subject = f"[ERS] Risk Approved by Function Head - {risk.risk_id}"

    content = f"""
    <p>Dear User,</p>

    <p>The following risk has been approved by the Function Head:</p>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr><td><b>Risk ID</b></td><td>{risk.risk_id}</td></tr>
        <tr><td><b>Risk Name</b></td><td>{risk.risk_name}</td></tr>
    </table>

    <p>Please proceed with further action.</p>

    <p>Regards,<br>ERS Team</p>
    """

    body = build_email_template("Function Head Approval", content)

    create_email_job(db, to_emails, cc_emails, subject, body, created_by=risk.risk_function_head_approval_by)


# EVENT 3: RISK MANAGER ACTION

def send_risk_manager_email(db: Session, risk_register_id: int):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_register_id
    ).first()

    if not risk:
        return

    owner = get_emails_by_user_ids(db, [risk.risk_owner_id])
    fh = get_users_by_role_name(db, "FUNCTION_HEAD")
    rh = get_users_by_role_name(db, "RISK_HEAD")

    to_emails = list(set(owner + fh + rh))

    rm = get_users_by_role_name(db, "RISK_MANAGER")
    cc_emails = list(set(rm) - set(to_emails))

    subject = f"[ERS] Risk Updated by Risk Manager - {risk.risk_id}"

    content = f"""
    <p>Dear User,</p>

    <p>The Risk Manager has updated the following risk:</p>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr><td><b>Risk ID</b></td><td>{risk.risk_id}</td></tr>
        <tr><td><b>Risk Name</b></td><td>{risk.risk_name}</td></tr>
    </table>

    <p>Please review the updates.</p>

    <p>Regards,<br>ERS Team</p>
    """

    body = build_email_template("Risk Manager Update", content)

    create_email_job(db, to_emails, cc_emails, subject, body, created_by=risk.risk_manager_approval_by)


# EVENT 4: RISK HEAD ACTION

def send_risk_head_email(db: Session, risk_register_id: int):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_register_id
    ).first()

    if not risk:
        return

    owner = get_emails_by_user_ids(db, [risk.risk_owner_id])
    fh = get_users_by_role_name(db, "FUNCTION_HEAD")
    rm = get_users_by_role_name(db, "RISK_MANAGER")

    to_emails = list(set(owner + fh + rm))

    rh = get_users_by_role_name(db, "RISK_HEAD")
    cc_emails = list(set(rh) - set(to_emails))

    subject = f"[ERS] Risk Updated by Risk Head - {risk.risk_id}"

    content = f"""
    <p>Dear User,</p>

    <p>The Risk Head has completed action on the following risk:</p>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr><td><b>Risk ID</b></td><td>{risk.risk_id}</td></tr>
        <tr><td><b>Risk Name</b></td><td>{risk.risk_name}</td></tr>
    </table>

    <p>Please review the final status.</p>

    <p>Regards,<br>ERS Team</p>
    """

    body = build_email_template("Risk Head Action", content)

    create_email_job(db, to_emails, cc_emails, subject, body, created_by=risk.risk_head_approval_by)
    
    
# EVENT 5: SEND TREATMENT EMAIL AFTER FULL APPROVAL

def send_treatment_email_after_approval(db: Session, risk_register_id: int):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_register_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        print("Risk not found")
        return

    # Condition: Risk Head Approved OR All Approved

    if not (
        risk.risk_head_approval_status == 1 or
        (
            risk.risk_function_head_approval_status == 1 and
            risk.risk_manager_approval_status == 1 and
            risk.risk_head_approval_status == 1
        )
    ):
        print("Approval not completed")
        return

    # ---------------- GET TREATMENTS ----------------
    treatments = db.execute(text(f"""
        SELECT risk_treatment_id, risk_description_id, risk_id, action_owner_id, action_plan, target_date, progress
        FROM {SCHEMA}.risk_treatment
        WHERE risk_id = :risk_id
        AND is_deleted = 0
    """), {"risk_id": risk.risk_id}).fetchall()

    if not treatments:
        print("No treatments found")
        return

    # ---------------- TO (ACTION OWNERS) ----------------
    action_owner_ids = [t.action_owner_id for t in treatments]

    to_emails = get_emails_by_user_ids(db, action_owner_ids)

    # ---------------- CC ----------------
    fh = get_users_by_role_name(db, "FUNCTION_HEAD")
    rm = get_users_by_role_name(db, "RISK_MANAGER")
    rh = get_users_by_role_name(db, "RISK_HEAD")
    owner = get_emails_by_user_ids(db, [risk.risk_owner_id])

    cc_emails = list(set(fh + rm + rh + owner) - set(to_emails))

    # ---------------- EMAIL BODY (PROFESSIONAL) ----------------

    treatment_rows = ""
    for t in treatments:
        treatment_rows += f"""
        <tr>
            <td>{t.action_plan}</td>
            <td>{t.target_date}</td>
            <td>{t.progress}%</td>
        </tr>
        """

    subject = f"[ERS] Action Required: Treatments for Risk {risk.risk_id}"

    body = f"""
    <html>
    <body style="font-family: Arial; background:#f4f6f8; padding:20px;">
        <table width="100%" style="background:white; padding:20px; border-radius:8px;">
            <tr>
                <td>
                    <h2 style="color:#2c3e50;">Risk Treatment Assignment</h2>

                    <p>Dear User,</p>

                    <p>
                        The risk <b>{risk.risk_name}</b> (ID: <b>{risk.risk_id}</b>) 
                        has been fully approved. Please find below the assigned treatments.
                    </p>

                    <table border="1" cellpadding="8" cellspacing="0" width="100%" style="border-collapse:collapse;">
                        <tr style="background:#2c3e50; color:white;">
                            <th>Action</th>
                            <th>Target Date</th>
                            <th>Progress</th>
                        </tr>
                        {treatment_rows}
                    </table>

                    <p style="margin-top:20px;">
                        Kindly take necessary action within the timeline.
                    </p>

                    <p>Regards,<br>ERS System</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    create_email_job(db, to_emails, cc_emails, subject, body, created_by=risk.risk_head_approval_by)

    # print("Treatment Email Triggered")