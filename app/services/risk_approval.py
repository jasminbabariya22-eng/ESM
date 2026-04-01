from datetime import datetime, timezone
from app.models.risk_register import RiskRegister
from app.models.mst_status import Status

from app.services.risk_service import *


def approve_risk(db, data, user_id):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == data.risk_register_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        raise Exception("Risk not found")

    # Convert status to 1 or -1
    if data.approval_status_id == 1:
        final_status = 1
        status_name = "Approved"
    elif data.approval_status_id == 2:
        final_status = -1
        status_name = "Rejected"
    else:
        raise Exception("Invalid approval status")

    if data.approval_level == 1:
        risk.risk_function_head_approval_status = final_status
        risk.risk_function_head_approval_remark = data.remark
        risk.risk_function_head_approval_by = user_id
        risk.risk_function_head_approval_on = datetime.now(timezone.utc)

    elif data.approval_level == 2:
        risk.risk_head_approval_status = final_status
        risk.risk_head_approval_remark = data.remark
        risk.risk_head_approval_by = user_id
        risk.risk_head_approved_on = datetime.now(timezone.utc)

    elif data.approval_level == 3:
        risk.risk_manager_approval_status = final_status
        risk.risk_manager_approval_remark = data.remark
        risk.risk_manager_approval_by = user_id
        risk.risk_manager_approved_on = datetime.now(timezone.utc)

    else:
        raise Exception("Invalid approval level")

    db.commit()

    return risk, status_name

        # ---------------- Status logic ----------------

    # def get_status_id(name):
    #     s = db.query(Status).filter(Status.status_name == name, Status.is_deleted == 0).first()
    #     return s.id if s else None

    # approved_id = get_status_id("Approved")
    # rejected_id = get_status_id("Rejected")
    # pending_id  = get_status_id("Pending")

    # fh = risk.risk_function_head_approval_status
    # rh = risk.risk_head_approval_status
    # rm = risk.risk_manager_approval_status

    # if rejected_id in [fh, rh, rm]:
    #     risk.risk_status = rejected_id

    # elif fh == approved_id and rh == approved_id and rm == approved_id:
    #     risk.risk_status = approved_id

    # elif approved_id in [fh, rh, rm]:
    #     risk.risk_status = pending_id

    # db.commit()

    # return risk, status_obj.status_name