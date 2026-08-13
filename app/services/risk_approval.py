from datetime import datetime, timezone

from app.models.risk_register import RiskRegister
from app.models.mst_status import Status
from app.models.risk_register_hist import RiskRegisterHist
from app.services.risk_service import reset_risk_approvals, get_status_id

from app.services.email_event_service import *
from app.workflow.services.workflow_service import WorkflowService
from app.models.user import User
from app.workflow.persistence.models import SpiffWorkflowInstance, BPMNDefinition
from app.models.workflow_visibility import WorkflowVisibility

# Central constants – no more magic numbers or bare role strings
from app.core.constants import (
    ApprovalStatus,
    RoleCode,
    RoleName,
    APPROVAL_LEVEL_TO_ROLE,
    ROLE_TO_APPROVAL_LEVEL,
    REQUEST_STATUS_TO_APPROVAL,
    REQUEST_STATUS_NAMES,
    all_approved,
)

# Keep backward-compatible aliases so nothing else breaks
ROLE_FUNCTIONAL_HEAD = RoleCode.FUNCTIONAL_HEAD
ROLE_RISK_MANAGER    = RoleCode.RISK_MANAGER
ROLE_RISK_HEAD       = RoleCode.RISK_HEAD

def approve_risk(db, data, user_id):

    # ---------------- GET RISK ----------------

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == data.risk_register_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        raise Exception("Risk not found")

    # ---------------- APPROVAL STATUS MAP ----------------

    action_name = None
    if getattr(data, "action", None) is not None:
        action_name = data.action.upper()
    else:
        if data.approval_status_id == 7:
            action_name = "APPROVE"
        elif data.approval_status_id == 8:
            action_name = "REJECT"

    if action_name not in ["APPROVE", "REJECT", "FORCE_APPROVE"]:
        raise Exception("Invalid action. Allowed actions are APPROVE, REJECT, FORCE_APPROVE")

    if action_name == "APPROVE":
        status_req_id = 1
        approval_status_name = "Approved"
    elif action_name == "REJECT":
        status_req_id = -1
        approval_status_name = "Rejected"
    else:
        status_req_id = 1
        approval_status_name = "Approved"

    current_time = datetime.now(timezone.utc)

    # ---------------- WORKFLOW ROLE AND VALIDATION ----------------

    workflow_service = WorkflowService(db=db)
    workflow_service.validate_instance_active(entity_type="Risk", entity_id=risk.risk_register_id)
    
    role_code = workflow_service.get_current_role(entity_type="Risk", entity_id=risk.risk_register_id)

    user_record = db.query(User).filter(User.id == user_id).first()
    user_role_name = user_record.role.name if user_record and user_record.role else None

    if not role_code:
        raise Exception("No active workflow state or transition found for this risk")

    # Dynamic action permission authorization check
    instance = workflow_service.db.query(SpiffWorkflowInstance).filter(
        SpiffWorkflowInstance.entity_type == "Risk",
        SpiffWorkflowInstance.entity_id == risk.risk_register_id
    ).first()
    definition = workflow_service.db.query(BPMNDefinition).filter(
        BPMNDefinition.id == instance.bpmn_definition_id
    ).first()

    from app.workflow.services.workflow_service import check_task_permission
    if not check_task_permission(workflow_service.db, definition.spec_id, instance.current_task_code, user_role_name, action_name):
        raise Exception(f"Action {action_name} is not permitted for role {user_role_name} at task {instance.current_task_code}.")

    if action_name in ["APPROVE", "REJECT"]:
        if user_role_name != role_code:
            raise Exception(f"Action not allowed. User role '{user_role_name}' does not match required task role '{role_code}'")

    if data.approval_level is not None:
        expected_role_code = APPROVAL_LEVEL_TO_ROLE.get(data.approval_level)
        if not expected_role_code:
            raise Exception("Invalid approval level")
        if role_code != expected_role_code:
            raise Exception(f"Action not allowed at this approval level. Current required role is {role_code}")

    role_to_level_map = ROLE_TO_APPROVAL_LEVEL
    resolved_level = data.approval_level if data.approval_level is not None else role_to_level_map.get(role_code)

    # ---------------- LEGACY STATUS COLUMNS UPDATE ----------------

    if action_name in ["APPROVE", "REJECT"]:
        if role_code == ROLE_FUNCTIONAL_HEAD:
            risk.risk_function_head_approval_status = status_req_id
            risk.risk_function_head_approval_remark = data.remark
            risk.risk_function_head_approval_by = user_id
            risk.risk_function_head_approval_on = current_time

        elif role_code == ROLE_RISK_MANAGER:
            risk.risk_manager_approval_status = status_req_id
            risk.risk_manager_approval_remark = data.remark
            risk.risk_manager_approval_by = user_id
            risk.risk_manager_approved_on = current_time

        elif role_code == ROLE_RISK_HEAD:
            risk.risk_head_approval_status = status_req_id
            risk.risk_head_approval_remark = data.remark
            risk.risk_head_approval_by = user_id
            risk.risk_head_approved_on = current_time

    # ---------------- EXECUTE WORKFLOW ACTION ----------------

    if action_name == "APPROVE":
        workflow_service.approve(
            entity_type="Risk",
            entity_id=risk.risk_register_id,
            role_code=role_code,
            user_id=user_id,
            remarks=data.remark
        )
    elif action_name == "REJECT":
        workflow_service.reject(
            entity_type="Risk",
            entity_id=risk.risk_register_id,
            role_code=role_code,
            user_id=user_id,
            remarks=data.remark
        )
    elif action_name == "FORCE_APPROVE":
        approved_levels = workflow_service.force_approve(
            entity_type="Risk",
            entity_id=risk.risk_register_id,
            user_id=user_id,
            remarks=data.remark
        )
        # Update legacy status columns for all levels that were force-approved
        for lvl in approved_levels:
            if lvl == 1:
                risk.risk_function_head_approval_status = 1
                risk.risk_function_head_approval_remark = data.remark
                risk.risk_function_head_approval_by = user_id
                risk.risk_function_head_approval_on = current_time
            elif lvl == 2:
                risk.risk_manager_approval_status = 1
                risk.risk_manager_approval_remark = data.remark
                risk.risk_manager_approval_by = user_id
                risk.risk_manager_approved_on = current_time
            elif lvl == 3:
                risk.risk_head_approval_status = 1
                risk.risk_head_approval_remark = data.remark
                risk.risk_head_approval_by = user_id
                risk.risk_head_approved_on = current_time
        if approved_levels:
            resolved_level = max(approved_levels)

    # ---------------- STATUS QUERY ----------------

    statuses = db.query(Status).filter(
        Status.status_name.in_([
            "Pending for Action"
            # "New"
        ]),
        Status.is_deleted == 0
    ).all()

    status_map = {
        s.status_name: s.id for s in statuses
    }

    pending_id = status_map.get("Pending for Action")
    new_id = status_map.get("New")

    # ---------------- FINAL RISK STATUS ----------------

    approvals = [
        risk.risk_function_head_approval_status,
        risk.risk_manager_approval_status,
        risk.risk_head_approval_status
    ]

    # ---------------- FINAL RISK STATUS ----------------

    approvals = [
        risk.risk_function_head_approval_status,
        risk.risk_head_approval_status,
        risk.risk_manager_approval_status
    ]

    # keep current status by default
    risk_status_name = None

    if ApprovalStatus.REJECTED in [ApprovalStatus(v) if v is not None else ApprovalStatus.PENDING for v in approvals]:
        risk.risk_status = pending_id
        risk_status_name = "Pending for Action"
    else:

        current_status = db.query(Status).filter(
            Status.id == risk.risk_status
        ).first()

        risk_status_name = (
            current_status.status_name
            if current_status else None
        )
        

    # ---------------- HISTORY INSERT ----------------

    hist = RiskRegisterHist(

        risk_register_id=risk.risk_register_id,

        risk_id=risk.risk_id,
        risk_name=risk.risk_name,

        dept_id=risk.dept_id,
        risk_owner_id=risk.risk_owner_id,
        risk_co_owner_id=risk.risk_co_owner_id,

        # target_date=risk.target_date,
        financial_year=risk.financial_year,

        risk_status=risk.risk_status,
        risk_progress=risk.risk_progress,

        # ---------------- FUNCTION HEAD ----------------

        risk_function_head_approval_status=
            risk.risk_function_head_approval_status,

        risk_function_head_approval_remark=
            risk.risk_function_head_approval_remark,

        risk_function_head_approval_on=
            risk.risk_function_head_approval_on,

        risk_function_head_approval_by=
            risk.risk_function_head_approval_by,

        # ---------------- RISK HEAD ----------------

        risk_head_approval_status=
            risk.risk_head_approval_status,

        risk_head_approved_on=
            risk.risk_head_approved_on,

        risk_head_approval_remark=
            risk.risk_head_approval_remark,

        risk_head_approval_by=
            risk.risk_head_approval_by,

        # ---------------- RISK MANAGER ----------------

        risk_manager_approval_status=
            risk.risk_manager_approval_status,

        risk_manager_approved_on=
            risk.risk_manager_approved_on,

        risk_manager_approval_remark=
            risk.risk_manager_approval_remark,

        risk_manager_approval_by=
            risk.risk_manager_approval_by,

        # ---------------- AUDIT ----------------

        created_by=risk.created_by,
        created_on=risk.created_on,

        modified_by=user_id,
        modified_on=current_time,

        is_active=risk.is_active,
        is_deleted=risk.is_deleted
    )

    db.add(hist)
    
    
    # ---- EMAIL NOTIFICATIONS ----
    _level_to_display_name = {
        1: RoleName.FUNCTIONAL_HEAD,
        2: RoleName.RISK_MANAGER,
        3: RoleName.RISK_HEAD,
    }

    if status_req_id == ApprovalStatus.APPROVED:
        if resolved_level is not None:
            send_function_approval_email_seq(db, risk.risk_register_id, resolved_level)
    elif status_req_id == ApprovalStatus.REJECTED:
        rejected_by_role = _level_to_display_name.get(resolved_level, role_code)
        send_risk_rejection_email(
            db=db,
            risk_register_id=risk.risk_register_id,
            rejected_by_role=rejected_by_role,
            remark=data.remark
        )

    if all_approved(
        risk.risk_function_head_approval_status,
        risk.risk_manager_approval_status,
        risk.risk_head_approval_status
    ):
        send_treatment_email_after_approval(db, risk.risk_register_id)
    # ---------------- SINGLE COMMIT ----------------

    db.commit()

    db.refresh(risk)

    return (
        risk,

        data.approval_status_id,
        approval_status_name,

        risk.risk_status,
        risk_status_name,
        resolved_level
    )



#----------------Force Approval--------------------------

def force_approve_risk(db, data, user_id, user_type):
    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == data.risk_register_id,
        RiskRegister.is_deleted == 0
    ).first()

    if not risk:
        raise Exception("Risk not found")
    
    current_time = datetime.now(timezone.utc)
    
    # ---------------- WORKFLOW ROLE AND VALIDATION ----------------
    workflow_service = WorkflowService(db=db)
    workflow_service.validate_instance_active(entity_type="Risk", entity_id=risk.risk_register_id)

    user_record = db.query(User).filter(User.id == user_id).first()
    user_role_name = user_record.role.name if user_record and user_record.role else None

    role_code = workflow_service.get_current_role(entity_type="Risk", entity_id=risk.risk_register_id)
    if not role_code:
        raise Exception("No active workflow state or transition found for this risk")

    # Retrieve definition/spec_id for permission check
    instance = workflow_service.db.query(SpiffWorkflowInstance).filter(
        SpiffWorkflowInstance.entity_type == "Risk",
        SpiffWorkflowInstance.entity_id == risk.risk_register_id
    ).first()
    definition = workflow_service.db.query(BPMNDefinition).filter(
        BPMNDefinition.id == instance.bpmn_definition_id
    ).first()

    from app.workflow.services.workflow_service import check_task_permission
    if not check_task_permission(workflow_service.db, definition.spec_id, instance.current_task_code, user_role_name, "FORCE_APPROVE"):
        raise Exception(f"Action FORCE_APPROVE is not permitted for role {user_role_name} at task {instance.current_task_code}.")

    # Execute the force approval action on workflow service
    approved_levels = workflow_service.force_approve(
        entity_type="Risk",
        entity_id=risk.risk_register_id,
        user_id=user_id,
        remarks=data.remark
    )

    if not approved_levels:
        raise Exception("Risk is already fully approved.")

    # Update legacy status columns for all levels that were force-approved
    for lvl in approved_levels:
        if lvl == 1:
            risk.risk_function_head_approval_status = 1
            risk.risk_function_head_approval_remark = data.remark
            risk.risk_function_head_approval_by = user_id
            risk.risk_function_head_approval_on = current_time
        elif lvl == 2:
            risk.risk_manager_approval_status = 1
            risk.risk_manager_approval_remark = data.remark
            risk.risk_manager_approval_by = user_id
            risk.risk_manager_approved_on = current_time
        elif lvl == 3:
            risk.risk_head_approval_status = 1
            risk.risk_head_approval_remark = data.remark
            risk.risk_head_approval_by = user_id
            risk.risk_head_approved_on = current_time

    # ---------------- STATUS QUERY ----------------
    statuses = db.query(Status).filter(
        Status.status_name.in_(["Pending for Action"]),
        Status.is_deleted == 0
    ).all()
    status_map = {s.status_name: s.id for s in statuses}
    pending_id = status_map.get("Pending for Action")
    
    approvals = [
        risk.risk_function_head_approval_status,
        risk.risk_manager_approval_status,
        risk.risk_head_approval_status
    ]

    risk_status_name = None
    if ApprovalStatus.REJECTED in [ApprovalStatus(v) if v is not None else ApprovalStatus.PENDING for v in approvals]:
        risk.risk_status = pending_id
        risk_status_name = "Pending for Action"
    else:
        current_status = db.query(Status).filter(Status.id == risk.risk_status).first()
        risk_status_name = current_status.status_name if current_status else None
    
    # ---------------- HISTORY INSERT ----------------
    hist = RiskRegisterHist(
        risk_register_id=risk.risk_register_id,
        risk_id=risk.risk_id,
        risk_name=risk.risk_name,
        dept_id=risk.dept_id,
        risk_owner_id=risk.risk_owner_id,
        financial_year=risk.financial_year,
        risk_status=risk.risk_status,
        risk_progress=risk.risk_progress,
        risk_function_head_approval_status=risk.risk_function_head_approval_status,
        risk_function_head_approval_remark=risk.risk_function_head_approval_remark,
        risk_function_head_approval_on=risk.risk_function_head_approval_on,
        risk_function_head_approval_by=risk.risk_function_head_approval_by,
        risk_head_approval_status=risk.risk_head_approval_status,
        risk_head_approved_on=risk.risk_head_approved_on,
        risk_head_approval_remark=risk.risk_head_approval_remark,
        risk_head_approval_by=risk.risk_head_approval_by,
        risk_manager_approval_status=risk.risk_manager_approval_status,
        risk_manager_approved_on=risk.risk_manager_approved_on,
        risk_manager_approval_remark=risk.risk_manager_approval_remark,
        risk_manager_approval_by=risk.risk_manager_approval_by,
        created_by=risk.created_by,
        created_on=risk.created_on,
        modified_by=user_id,
        modified_on=current_time,
        is_active=risk.is_active,
        is_deleted=risk.is_deleted
    )
    db.add(hist)
    
    # ---------------- EMAILS ----------------
    for level in approved_levels:
        send_function_approval_email_seq(
            db,
            risk.risk_register_id,
            level
        )

    if all_approved(
        risk.risk_function_head_approval_status,
        risk.risk_manager_approval_status,
        risk.risk_head_approval_status
    ):
        send_treatment_email_after_approval(
            db,
            risk.risk_register_id
        )
        
    db.commit()
    db.refresh(risk)

    return (
        risk,
        approved_levels,
        risk.risk_status,
        risk_status_name
    )