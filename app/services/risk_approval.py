from datetime import datetime, timezone
from app.models.risk_register import RiskRegister
from app.models.mst_status import Status

from app.services.risk_service import *

from app.services.email_event_service import (
    send_function_head_approval_email,
    send_risk_head_email,
    send_risk_manager_email,
    send_treatment_email_after_approval
)


def approve_risk(db, data, user_id):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == data.risk_register_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        raise Exception("Risk not found")

    # Convert 7 / 8 to Approved / Rejected
    if data.approval_status_id == 7:
        status_name_required = "Approved"
        status_req_id = 1
    elif data.approval_status_id == 8:
        status_name_required = "Rejected"
        status_req_id = -1
    else:
        raise Exception("Invalid approval status. Use 7 for Approved and 8 for Rejected")

    # Get status name
    # status_obj = db.query(Status).filter(
    #     Status.status_name == status_name_required,
    #     Status.is_deleted == 0
    # ).first()
    
    # if not status_obj:
    #     raise Exception("Invalid status id")

    if data.approval_level == 1:
        risk.risk_function_head_approval_status = status_req_id
        risk.risk_function_head_approval_remark = data.remark
        risk.risk_function_head_approval_by = user_id
        risk.risk_function_head_approval_on = datetime.now(timezone.utc)

    elif data.approval_level == 2:
        risk.risk_head_approval_status = status_req_id
        risk.risk_head_approval_remark = data.remark
        risk.risk_head_approval_by = user_id
        risk.risk_head_approved_on = datetime.now(timezone.utc)

    elif data.approval_level == 3:
        risk.risk_manager_approval_status = status_req_id
        risk.risk_manager_approval_remark = data.remark
        risk.risk_manager_approval_by = user_id
        risk.risk_manager_approved_on = datetime.now(timezone.utc)

    else:
        raise Exception("Invalid approval level")

        # ---------------- Status logic ----------------

    def get_status_id(name):
        s = db.query(Status).filter(Status.status_name == name, Status.is_deleted == 0).first()
        return s.id if s else None

    function_head = risk.risk_function_head_approval_status
    risk_head = risk.risk_head_approval_status
    risk_manager = risk.risk_manager_approval_status

    pending_id = get_status_id("Pending for Action")
    new_id = get_status_id("New")

    # MAIN LOGIC
    if -1 in [function_head, risk_head, risk_manager]:
        risk.risk_status = pending_id
    else:
        risk.risk_status = new_id

    db.commit()

    # ---------------- EMAIL TRIGGER ----------------
    try:
        if data.approval_level == 1:
            send_function_head_approval_email(db, risk.risk_register_id)

        elif data.approval_level == 2:
            send_risk_head_email(db, risk.risk_register_id)

        elif data.approval_level == 3:
            send_risk_manager_email(db, risk.risk_register_id)
    
    except Exception as e:
        print("Email trigger failed:", e)
        
    send_treatment_email_after_approval(db, risk.risk_register_id)

    return risk, "", ""