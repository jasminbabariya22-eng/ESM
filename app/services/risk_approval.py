from datetime import datetime, timezone
from app.models.risk_register import RiskRegister
from app.models.mst_status import Status


def approve_risk(db, data, user_id):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == data.risk_register_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        raise Exception("Risk not found")

    # Get status name
    status_obj = db.query(Status).filter(
        Status.id == data.approval_status_id,
        Status.is_deleted == 0
    ).first()

    if not status_obj:
        raise Exception("Invalid status id")

    # ✅ NO VALIDATION — DIRECT UPDATE

    if data.approval_level == 1:
        risk.risk_function_head_approval_status = data.approval_status_id
        risk.risk_function_head_approval_remark = data.remark
        risk.risk_function_head_approval_by = user_id
        risk.risk_function_head_approval_on = datetime.now(timezone.utc)

    elif data.approval_level == 2:
        risk.risk_head_approval_status = data.approval_status_id
        risk.risk_head_approval_remark = data.remark
        risk.risk_head_approval_by = user_id
        risk.risk_head_approved_on = datetime.now(timezone.utc)

    elif data.approval_level == 3:
        risk.risk_manager_approval_status = data.approval_status_id
        risk.risk_manager_approval_remark = data.remark
        risk.risk_manager_approval_by = user_id
        risk.risk_manager_approved_on = datetime.now(timezone.utc)

    else:
        raise Exception("Invalid approval level")

    db.commit()

    return risk, status_obj.status_name