from datetime import datetime
from sqlalchemy import and_, or_
from app.models.workflow_visibility import WorkflowVisibility
from app.models.risk_register import RiskRegister
from app.models.user import User

class WorkflowVisibilityService:
    @staticmethod
    def sync_visibility(db, instance_id: int, entity_type: str, entity_id: int):
        """
        Calculates and syncs visibility permissions for a workflow instance.
        """
        # 1. Determine the owner and department of the entity
        owner_id = None
        dept_id = None
        co_owner_id = None
        
        if entity_type == "Risk":
            risk = db.query(RiskRegister).filter(RiskRegister.risk_register_id == entity_id).first()
            if not risk:
                return
            owner_id = risk.risk_owner_id
            dept_id = risk.dept_id
            co_owner_id = risk.risk_co_owner_id

        # 2. Deactivate previous task visibility rows for this instance
        db.query(WorkflowVisibility).filter(
            WorkflowVisibility.instance_id == instance_id,
            WorkflowVisibility.visibility == 1
        ).update({"visibility": 0})
        db.flush()

        # 3. Always grant visibility to the Risk Owner and Co-owner
        if owner_id:
            WorkflowVisibilityService._add_visibility(db, instance_id, user_id=owner_id)
        if co_owner_id and co_owner_id != 0:
            WorkflowVisibilityService._add_visibility(db, instance_id, user_id=co_owner_id)

        # 4. Query active READY tasks from workflow database
        from app.workflow.persistence.models import SpiffHumanTask, SpiffWorkflowInstance
        
        # Check dialect: SQLite tests share schemas in one DB; Postgres production has separate sessions
        if db.bind.dialect.name == "sqlite":
            wf_db = db
        else:
            from app.workflow.workflow_session import WorkflowSessionLocal
            wf_db = WorkflowSessionLocal()

        try:
            wf_instance = wf_db.query(SpiffWorkflowInstance).filter(
                SpiffWorkflowInstance.instance_id == instance_id
            ).first()

            if wf_instance and wf_instance.status == "Running":
                active_tasks = wf_db.query(SpiffHumanTask).filter(
                    SpiffHumanTask.instance_id == instance_id,
                    SpiffHumanTask.status == "READY"
                ).all()

                for task in active_tasks:
                    if task.role_code == "RISK_OWNER":
                        continue
                        
                    # Query users with this role_code from main DB
                    query = db.query(User).join(User.role).filter(
                        User.role.has(name=task.role_code),
                        User.is_deleted == 0
                    )
                    
                    # If role is department-specific, filter by department
                    if task.role_code == "FUNCTION_HEAD" and dept_id is not None:
                        query = query.filter(User.dept_id == dept_id)
                        
                    users = query.all()
                    for user in users:
                        WorkflowVisibilityService._add_visibility(
                            db, instance_id, user.id, user.role_id, user.user_type_id
                        )
        finally:
            if db.bind.dialect.name != "sqlite":
                wf_db.close()

        db.flush()

    @staticmethod
    def _add_visibility(db, instance_id: int, user_id: int, role_id: int = None, user_type_id: int = None):
        existing = db.query(WorkflowVisibility).filter(
            WorkflowVisibility.instance_id == instance_id,
            WorkflowVisibility.user_id == user_id,
            WorkflowVisibility.visibility == 1
        ).first()
        
        if not existing:
            new_vis = WorkflowVisibility(
                instance_id=instance_id,
                user_id=user_id,
                role_id=role_id,
                user_type_id=user_type_id,
                visibility=1,
                time=datetime.utcnow()
            )
            db.add(new_vis)
