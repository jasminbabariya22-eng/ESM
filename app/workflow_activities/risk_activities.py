from typing import Any, Dict
from sqlalchemy.orm import Session

from app.workflow.runtime.base_activity import BaseActivity
from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.registry import registry

# Import the existing untouched business service methods
from app.services.risk_service import create_update_risk
from app.services.risk_approval import approve_risk
from app.services.email_event_service import (
    send_risk_created_email,
    send_function_approval_email_seq,
    send_risk_rejection_email,
    send_treatment_email_after_approval,
)

@registry.register("CreateRisk")
class CreateRiskActivity(BaseActivity):
    """
    Workflow Activity wrapping the existing RiskService.create_update_risk() method.
    Receives db Session and invokes risk creation logic without touching business rules.
    """
    def __init__(self, db: Session):
        self.db = db

    def validate(self, context: WorkflowContext) -> bool:
        payload = context.get_variable("payload")
        current_user = context.get_variable("current_user")
        return payload is not None and current_user is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        payload = context.get_variable("payload")
        current_user = context.get_variable("current_user")
        
        # Invoke original business service
        result = create_update_risk(self.db, payload, current_user)
        
        # Extract properties to store as process variables
        risk_register_id = result["risk_register"]["risk_register_id"]
        risk_id = result["risk_register"]["risk_id"]
        
        context.set_variable("risk_register_id", risk_register_id)
        context.set_variable("risk_id", risk_id)
        
        return {
            "risk_register_id": risk_register_id,
            "risk_id": risk_id,
            "risk_register": result["risk_register"]
        }

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        risk_register_id = context.get_variable("risk_register_id")
        print(f"[Rollback] CreateRiskActivity compensation: Mark Risk ID {risk_register_id} as draft-abandoned.")
        return {"compensated": True}


@registry.register("ApproveRisk")
class ApproveRiskActivity(BaseActivity):
    """
    Workflow Activity wrapping the legacy ApprovalService.approve_risk() method.
    """
    def __init__(self, db: Session):
        self.db = db

    def validate(self, context: WorkflowContext) -> bool:
        approval_payload = context.get_variable("approval_payload")
        user_id = context.get_variable("user_id")
        return approval_payload is not None and user_id is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        approval_payload = context.get_variable("approval_payload")
        user_id = context.get_variable("user_id")
        
        # Invoke original business approval flow
        (
            risk,
            approval_status_id,
            approval_status_name,
            risk_status_id,
            risk_status_name
        ) = approve_risk(self.db, approval_payload, user_id)
        
        # Update workflow variables for routing rules
        context.set_variable("approval_status_id", approval_status_id)
        context.set_variable("risk_status_name", risk_status_name)
        
        return {
            "risk_register_id": risk.risk_register_id,
            "approval_status_id": approval_status_id,
            "approval_status_name": approval_status_name,
            "risk_status_id": risk_status_id,
            "risk_status_name": risk_status_name
        }

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        risk_register_id = context.get_variable("risk_register_id")
        print(f"[Rollback] ApproveRiskActivity compensation: Reverting approval columns for Risk ID {risk_register_id}")
        return {"compensated": True}


@registry.register("SendEmail")
class SendEmailActivity(BaseActivity):
    """
    Workflow Activity wrapping various existing notification methods under EmailService.
    Identifies the target email template dynamically based on workflow context variables.
    """
    def __init__(self, db: Session):
        self.db = db

    def validate(self, context: WorkflowContext) -> bool:
        email_type = context.get_variable("email_type")
        risk_register_id = context.get_variable("risk_register_id")
        return email_type is not None and risk_register_id is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        email_type = context.get_variable("email_type")
        risk_register_id = context.get_variable("risk_register_id")
        
        # Dispatch dynamically without modification to the business logic
        if email_type == "CREATED":
            send_risk_created_email(self.db, risk_register_id)
        
        elif email_type == "APPROVAL_SEQ":
            level = context.get_variable("approval_level")
            send_function_approval_email_seq(self.db, risk_register_id, level)
            
        elif email_type == "REJECTED":
            rejected_by_role = context.get_variable("rejected_by_role")
            remark = context.get_variable("remark")
            send_risk_rejection_email(self.db, risk_register_id, rejected_by_role, remark)
            
        elif email_type == "FINAL_APPROVED":
            send_treatment_email_after_approval(self.db, risk_register_id)
            
        else:
            raise ValueError(f"Unknown email_type: '{email_type}' specified in context.")
            
        return {"email_triggered": True, "email_type": email_type}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        print("[Rollback] SendEmailActivity compensation: Logging email recall limitation warning.")
        return {"compensated": True}
