import os
import logging
from typing import List, Optional, Any
from datetime import datetime

from app.core.logger import logger
from app.workflow.workflow_session import WorkflowSessionLocal

# Import SpiffWorkflow runtime and persistence components
from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.runtime.engine import SpiffWorkflowEngine
from app.workflow.runtime.bpmn_execution import BPMNExecutionLayer
from app.workflow.persistence.repository import SpiffWorkflowRepository
from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffHumanTask, BPMNDefinition, WorkflowEntityConfig
from app.workflow.runtime.bpmn_utils import get_candidate_role_from_xml
from app.models.user import User
from app.models.role import UserRole
import app.workflow.activities

# Shared constants (matching legacy constants for compilation compatibility)
ROLE_RISK_OWNER = "RISK_OWNER"
ROLE_FUNCTIONAL_HEAD = "FUNCTION_HEAD"
ROLE_RISK_MANAGER = "RISK_MANAGER"
ROLE_RISK_HEAD = "RISK_HEAD"

ACTION_SUBMIT = "SUBMIT"
ACTION_APPROVE = "APPROVE"
ACTION_REJECT = "REJECT"


class WorkflowService:
    """
    WorkflowService acts as a Process-Agnostic Adapter pattern over the new SpiffWorkflow engine.
    Resolves specifications, definitions, role validations, and gateway routes dynamically from BPMN.
    """
    def __init__(self, db: Optional[Any] = None):
        # Initialize connection session.
        # If db is the main database session, discard it and use WorkflowSessionLocal to connect to workflow_erm database.
        from app.core.database import engine as main_engine
        self.main_db = None
        if db is not None and db.bind == main_engine:
            self.main_db = db
            self.db = WorkflowSessionLocal()
            self._own_db = True
        else:
            if db is not None:
                self.db = db
                self._own_db = False
                self.main_db = db
            else:
                self.db = WorkflowSessionLocal()
                self._own_db = True
        
        # Build core engine dependencies
        self.parser = SpiffBPMNParser()
        self.engine = SpiffWorkflowEngine()
        self.repository = SpiffWorkflowRepository(self.db)
        self.execution_layer = BPMNExecutionLayer(self.parser, self.engine, self.repository)

    def __del__(self):
        if getattr(self, "_own_db", False):
            try:
                self.db.close()
            except Exception:
                pass

    def get_entity_workflow_config(self, entity_type: str) -> WorkflowEntityConfig:
        """
        Retrieves the active workflow configuration for a given entity type.
        """
        config = self.db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == entity_type,
            WorkflowEntityConfig.is_active == True
        ).first()
        if not config:
            raise ValueError(f"No active workflow configuration found for entity type '{entity_type}'")
        return config

    def _get_definition_for_entity(self, entity_type: str) -> BPMNDefinition:
        """
        Loads the active process definition matching the entity_type dynamically from the DB.
        """
        config = self.get_entity_workflow_config(entity_type)

        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == config.specification_id,
            BPMNDefinition.is_active == True
        ).order_by(BPMNDefinition.version.desc(), BPMNDefinition.id.desc()).first()

        if not definition:
            raise ValueError(f"BPMN definition for specification '{config.specification_id}' is inactive or does not exist.")

        return definition


    def start_workflow(
        self,
        workflow_name: str,
        entity_type: str,
        entity_id: int,
        user_id: int
    ) -> Any:
        logger.info(f"Starting SpiffWorkflow for entity type='{entity_type}', id={entity_id} by user={user_id}")
        
        # Resolve creator's role dynamically from database
        from app.core.database import SessionLocal
        with SessionLocal() as main_db:
            user_record = main_db.query(User).filter(User.id == user_id).first()
            user_role_name = user_record.role.name if user_record and user_record.role else "RISK_OWNER"

        # Resolve active definition record dynamically
        definition = self._get_definition_for_entity(entity_type)

        # 1. Initialize context variables
        context = WorkflowContext(
            variables={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "workflow_name": workflow_name,
                "created_by": user_id,
                "approved": True
            },
            user_id=user_id,
            user_role=user_role_name
        )
        
        # 2. Start process execution (enters initial state)
        result = self.execution_layer.start_workflow(
            xml_content=definition.xml_content,
            spec_id=definition.spec_id,
            definition_db_id=definition.id,
            context=context,
            db_session=self.db
        )
        
        # 3. Fetch and return instance model
        return self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

    def _log_history_and_activity(
        self,
        instance_id: int,
        from_state: Optional[str],
        to_state: Optional[str],
        action_name: str,
        user_id: int,
        role_code: str,
        remarks: Optional[str],
        variables: dict = None
    ):
        import json
        from app.workflow.models.history import WorkflowHistory
        from app.workflow.persistence.models import SpiffActivityHistory
        
        # 1. Log transition to WorkflowHistory (Approval Audit Trails)
        history = WorkflowHistory(
            instance_id=instance_id,
            from_state_code=from_state,
            to_state_code=to_state,
            action_name=action_name,
            performed_by=user_id,
            performed_role=role_code,
            remarks=remarks,
            performed_on=datetime.utcnow()
        )
        self.db.add(history)
        
        # 2. Log activity execution to SpiffActivityHistory (Activity Steps Logs)
        activity_name = f"{action_name} task '{from_state or 'START'}'"
        activity_log = SpiffActivityHistory(
            instance_id=instance_id,
            activity_id=from_state or "StartEvent",
            activity_name=activity_name,
            activity_type="UserTask" if from_state else "StartEvent",
            status="COMPLETED",
            variables=json.dumps(variables or {}),
            timestamp=datetime.utcnow()
        )
        self.db.add(activity_log)
        self.db.flush()

    def submit(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int,
        remarks: str = None
    ) -> Any:
        logger.info(f"Executing submit action for entity type='{entity_type}', id={entity_id} by user={user_id}")
        
        # Check if workflow instance already exists
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

        if not instance:
            config = self.get_entity_workflow_config(entity_type)
            definition = self._get_definition_for_entity(entity_type)
            # Create a brand new workflow instance (enters START state)
            instance = self.start_workflow(
                workflow_name=f"{entity_type} Approval Workflow",
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id
            )
            self._log_history_and_activity(
                instance_id=instance.instance_id,
                from_state=None,
                to_state=instance.current_task_code,
                action_name="Create Risk",
                user_id=user_id,
                role_code="RISK_OWNER",
                remarks="Initial Risk Registration"
            )
            
            # Find the active human task (enters PENDING_FH state)
            active_task = self.db.query(SpiffHumanTask).filter(
                SpiffHumanTask.instance_id == instance.instance_id,
                SpiffHumanTask.status == "READY"
            ).first()

            logger.info(
                f"Workflow config resolved:\n"
                f"entity_type={entity_type}\n"
                f"entity_id={entity_id}\n"
                f"config_id={config.config_id}\n"
                f"bpmn_definition_id={definition.id}\n"
                f"spec_id={definition.spec_id}\n"
                f"workflow_instance_id={instance.instance_id}\n"
                f"human_task_id={active_task.task_id if active_task else None}\n"
                f"role={active_task.role_code if active_task else None}"
            )
            self.db.commit()
            from app.workflow.services.visibility_service import WorkflowVisibilityService
            WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
            return instance

        # If instance already exists, use the definition associated with it
        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        if not definition:
            raise ValueError(f"BPMN definition with ID {instance.bpmn_definition_id} not found for workflow instance {instance.instance_id}")

        config = self.db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == entity_type,
            WorkflowEntityConfig.is_active == True
        ).first()

        # Resolve creator's role dynamically from database
        db_to_use = self.main_db if self.main_db is not None else self.db
        user_record = db_to_use.query(User).filter(User.id == user_id).first()
        user_role_name = user_record.role.name if user_record and user_record.role else "RISK_OWNER"

        # Determine the active task dynamically from the engine
        current_task_code = instance.current_task_code or "DRAFT"

        # Validate candidate role dynamically from XML definition
        candidate_role = get_candidate_role_from_xml(definition.xml_content, current_task_code)
        if candidate_role and user_role_name != candidate_role:
            raise PermissionError(f"Authorization failure: User role '{user_role_name}' does not match candidate group '{candidate_role}'")

        # Resume workflow execution loop generically
        result = self.execution_layer.resume_workflow(
            xml_content=definition.xml_content,
            spec_id=definition.spec_id,
            entity_type=entity_type,
            entity_id=entity_id,
            task_spec_id=current_task_code,
            payload={
                "approved": True,
                "user_id": user_id,
                "role_code": user_role_name,
                "remarks": remarks
            },
            db_session=self.db
        )
        
        # Mark index human task as completed if it exists
        draft_task = self.db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.task_spec_id == current_task_code,
            SpiffHumanTask.status == "READY"
        ).first()
        
        if draft_task:
            draft_task.status = "COMPLETED"
            draft_task.completed_on = datetime.utcnow()
            self.db.flush()

        self._log_history_and_activity(
            instance_id=instance.instance_id,
            from_state=current_task_code,
            to_state=instance.current_task_code,
            action_name="Submit",
            user_id=user_id,
            role_code=user_role_name,
            remarks=remarks,
            variables={"approved": True}
        )

        active_task = self.db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.status == "READY"
        ).first()

        logger.info(
            f"Workflow config resolved:\n"
            f"entity_type={entity_type}\n"
            f"entity_id={entity_id}\n"
            f"config_id={config.config_id if config else None}\n"
            f"bpmn_definition_id={definition.id}\n"
            f"spec_id={definition.spec_id}\n"
            f"workflow_instance_id={instance.instance_id}\n"
            f"human_task_id={active_task.task_id if active_task else None}\n"
            f"role={active_task.role_code if active_task else None}"
        )

        self.db.commit()
        from app.workflow.services.visibility_service import WorkflowVisibilityService
        WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
        return instance


    def approve(
        self,
        entity_type: str,
        entity_id: int,
        role_code: str,
        user_id: int,
        remarks: str = None
    ) -> Any:
        logger.info(f"Executing approve action for entity type='{entity_type}', id={entity_id} by user={user_id} with role='{role_code}'")
        
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance:
            raise ValueError(f"Workflow instance not found for entity type='{entity_type}', id={entity_id}")
            
        current_task_code = instance.current_task_code
        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        if not definition:
            raise ValueError(f"BPMN definition with ID {instance.bpmn_definition_id} not found for workflow instance {instance.instance_id}")

        # Check that active task exists in DB and is READY
        human_task = self.db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.task_spec_id == current_task_code,
            SpiffHumanTask.status == "READY"
        ).first()

        if not human_task:
            raise ValueError("Active workflow task could not be found")
        
        # Retrieve candidate role configuration from BPMN XML
        candidate_role = get_candidate_role_from_xml(definition.xml_content, current_task_code)
        if candidate_role and role_code != candidate_role:
            raise PermissionError(f"Authorization failure: User role '{role_code}' does not match candidate group '{candidate_role}'")

        # Resume workflow with generic approval payload
        self.execution_layer.resume_workflow(
            xml_content=definition.xml_content,
            spec_id=definition.spec_id,
            entity_type=entity_type,
            entity_id=entity_id,
            task_spec_id=current_task_code,
            payload={
                "approved": True,
                "user_id": user_id,
                "role_code": role_code,
                "remarks": remarks
            },
            db_session=self.db
        )
        
        # Mark index human task as completed
        human_task.status = "COMPLETED"
        human_task.completed_on = datetime.utcnow()
        self.db.flush()

        self._log_history_and_activity(
            instance_id=instance.instance_id,
            from_state=current_task_code,
            to_state=instance.current_task_code,
            action_name="Approve",
            user_id=user_id,
            role_code=role_code,
            remarks=remarks,
            variables={"approved": True}
        )
            
        config = self.db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == entity_type,
            WorkflowEntityConfig.is_active == True
        ).first()

        logger.info(
            f"Workflow config resolved:\n"
            f"entity_type={entity_type}\n"
            f"entity_id={entity_id}\n"
            f"config_id={config.config_id if config else None}\n"
            f"bpmn_definition_id={definition.id}\n"
            f"spec_id={definition.spec_id}\n"
            f"workflow_instance_id={instance.instance_id}\n"
            f"human_task_id={human_task.task_id if human_task else None}\n"
            f"role={role_code}"
        )

        self.db.commit()
        from app.workflow.services.visibility_service import WorkflowVisibilityService
        WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
        return instance

    def reject(
        self,
        entity_type: str,
        entity_id: int,
        role_code: str,
        user_id: int,
        remarks: str = None
    ) -> Any:
        logger.info(f"Executing reject action for entity type='{entity_type}', id={entity_id} by user={user_id} with role='{role_code}'")
        
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance:
            raise ValueError(f"Workflow instance not found for entity type='{entity_type}', id={entity_id}")
            
        current_task_code = instance.current_task_code
        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        if not definition:
            raise ValueError(f"BPMN definition with ID {instance.bpmn_definition_id} not found for workflow instance {instance.instance_id}")

        # Check that active task exists in DB and is READY
        human_task = self.db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.task_spec_id == current_task_code,
            SpiffHumanTask.status == "READY"
        ).first()

        if not human_task:
            raise ValueError("Active workflow task could not be found")
        
        # Retrieve candidate role configuration from BPMN XML
        candidate_role = get_candidate_role_from_xml(definition.xml_content, current_task_code)
        if candidate_role and role_code != candidate_role:
            raise PermissionError(f"Authorization failure: User role '{role_code}' does not match candidate group '{candidate_role}'")

        # Resume workflow with generic rejection payload
        self.execution_layer.resume_workflow(
            xml_content=definition.xml_content,
            spec_id=definition.spec_id,
            entity_type=entity_type,
            entity_id=entity_id,
            task_spec_id=current_task_code,
            payload={
                "approved": False,
                "user_id": user_id,
                "role_code": role_code,
                "remarks": remarks
            },
            db_session=self.db
        )
        
        # Mark human task status as REJECTED in index
        human_task.status = "REJECTED"
        human_task.completed_on = datetime.utcnow()
        self.db.flush()

        self._log_history_and_activity(
            instance_id=instance.instance_id,
            from_state=current_task_code,
            to_state=instance.current_task_code,
            action_name="Reject",
            user_id=user_id,
            role_code=role_code,
            remarks=remarks,
            variables={"approved": False}
        )
            
        config = self.db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == entity_type,
            WorkflowEntityConfig.is_active == True
        ).first()

        logger.info(
            f"Workflow config resolved:\n"
            f"entity_type={entity_type}\n"
            f"entity_id={entity_id}\n"
            f"config_id={config.config_id if config else None}\n"
            f"bpmn_definition_id={definition.id}\n"
            f"spec_id={definition.spec_id}\n"
            f"workflow_instance_id={instance.instance_id}\n"
            f"human_task_id={human_task.task_id if human_task else None}\n"
            f"role={role_code}"
        )

        self.db.commit()
        from app.workflow.services.visibility_service import WorkflowVisibilityService
        WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
        return instance

    def validate_instance_active(
        self,
        entity_type: str,
        entity_id: int
    ) -> None:
        logger.info(f"Validating workflow instance state for entity type='{entity_type}', id={entity_id}")
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance:
            raise Exception("No active workflow state or transition found for this risk")
            
        if instance.status != "Running":
            raise Exception("Task not found or already completed")

    def get_current_role(
        self,
        entity_type: str,
        entity_id: int
    ) -> Optional[str]:
        logger.info(f"Determining required role for entity type='{entity_type}', id={entity_id}")
        
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance or instance.status != "Running":
            return None
            
        current_task_code = instance.current_task_code
        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        if not definition:
            raise ValueError(f"BPMN definition with ID {instance.bpmn_definition_id} not found for workflow instance {instance.instance_id}")
        
        return get_candidate_role_from_xml(definition.xml_content, current_task_code)

    def force_approve(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int,
        remarks: str = None
    ) -> List[int]:
        logger.info(f"Executing force_approve for entity type='{entity_type}', id={entity_id} by user={user_id}")
        
        # Resolve creator's role dynamically from database
        db_to_use = self.main_db if self.main_db is not None else self.db
        user_record = db_to_use.query(User).filter(User.id == user_id).first()
        user_role_name = user_record.role.name if user_record and user_record.role else "RISK_OWNER"

        approved_levels = []
        from app.core.constants import ROLE_TO_APPROVAL_LEVEL

        while True:
            # Determine the active task dynamically from the engine
            role_code = self.get_current_role(entity_type, entity_id)
            if not role_code:
                break
                
            instance = self.db.query(SpiffWorkflowInstance).filter(
                SpiffWorkflowInstance.entity_type == entity_type,
                SpiffWorkflowInstance.entity_id == entity_id
            ).first()
            
            definition = self.db.query(BPMNDefinition).filter(
                BPMNDefinition.id == instance.bpmn_definition_id
            ).first()

            # Check if this role can be force-approved by the current user
            if not check_task_permission(self.db, definition.spec_id, instance.current_task_code, user_role_name, "FORCE_APPROVE"):
                break

            level = ROLE_TO_APPROVAL_LEVEL.get(role_code)
            if level and level not in approved_levels:
                approved_levels.append(level)

            # Perform the approval step
            self.approve(
                entity_type=entity_type,
                entity_id=entity_id,
                role_code=role_code,
                user_id=user_id,
                remarks=remarks
            )
            
        return approved_levels


def check_task_permission(db, spec_id: str, task_spec_id: str, role_code: str, action: str) -> bool:
    from app.workflow.persistence.models import WorkflowTaskPermission
    
    permission = db.query(WorkflowTaskPermission).filter(
        WorkflowTaskPermission.spec_id == spec_id,
        WorkflowTaskPermission.task_spec_id == task_spec_id,
        WorkflowTaskPermission.role_code == role_code,
        WorkflowTaskPermission.is_active == True
    ).first()
    
    if permission:
        # Check if the requested action is in the allowed actions list
        allowed_actions = [a.strip().upper() for a in permission.actions.split(",")]
        return action.upper() in allowed_actions
        
    # Default fallback behavior for backward compatibility with existing tests/runs
    if action.upper() in ["APPROVE", "REJECT"]:
        return True
    if action.upper() == "FORCE_APPROVE":
        return role_code in ["RISK_MANAGER", "RISK_HEAD"]
        
    return False

