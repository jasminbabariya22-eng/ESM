from datetime import datetime
from app.models.risk_register import RiskRegister


def approve_risk(db, data, user_id):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == data.risk_register_id
    ).first()

    if not risk:
        raise Exception("Risk not found")

    # FUNCTION HEAD APPROVAL
    if data.approval_level == 1:

        risk.risk_function_head_approval_status = data.approval_status_id
        risk.risk_function_head_approval_remark = data.remark
        risk.risk_function_head_approval_by = user_id
        risk.risk_function_head_approval_on = datetime.now()

    # RISK HEAD APPROVAL
    elif data.approval_level == 2:

        # Check level 1 approval first
        if risk.risk_function_head_approval_status != 2:
            raise Exception("Function head approval required first")

        risk.risk_head_approval_status = data.approval_status_id
        risk.risk_head_approval_remark = data.remark
        risk.risk_head_approval_by = user_id
        risk.risk_head_approved_on = datetime.now()

    else:
        raise Exception("Invalid approval level")

    db.commit()

    return risk