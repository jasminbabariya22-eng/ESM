import pytest
from datetime import datetime, timezone
from app.models.risk_register import RiskRegister
from app.models.mst_status import Status
from app.models.user import User
from app.models.role import UserRole
from app.models.user_type import UserType
from app.models.department import Department
from app.workflow.persistence.models import BPMNDefinition, SpiffWorkflowInstance, SpiffHumanTask, WorkflowEntityConfig
from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.services.workflow_service import (
    WorkflowService,
    ROLE_FUNCTIONAL_HEAD,
    ROLE_RISK_MANAGER,
    ROLE_RISK_HEAD
)
from app.services.risk_approval import approve_risk
from app.schemas.risk_approval import RiskApprovalRequest

def test_dynamic_approval_flow(db_session):
    # 1. Create seed data
    dept = Department(dept_name="Finance", dept_short_name="FIN")
    db_session.add(dept)
    db_session.flush()

    role = UserRole(name=ROLE_FUNCTIONAL_HEAD, description="Functional Head Role")
    db_session.add(role)
    db_session.flush()

    utype = UserType(name="Functional Head", description="FH")
    db_session.add(utype)
    db_session.flush()

    user = User(
        log_id="fh_user",
        password="password",
        first_name="FH",
        last_name="User",
        email="fh@example.com",
        dept_id=dept.id,
        role_id=role.id,
        user_type_id=utype.id,
        status="Active"
    )
    db_session.add(user)
    db_session.flush()

    status_approved = Status(id=7, status_name="Approved", type="approval")
    status_rejected = Status(id=8, status_name="Rejected", type="approval")
    status_pending_act = Status(id=1, status_name="Pending for Action", type="risk")
    db_session.add(status_approved)
    db_session.add(status_rejected)
    db_session.add(status_pending_act)
    db_session.query(BPMNDefinition).filter(BPMNDefinition.spec_id == "RiskApprovalWorkflow").delete()
    db_session.flush()

    # 2. Add BPMN definition to DB
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                      xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                      xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                      id="Definitions_1"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="RiskApprovalWorkflow" isExecutable="true">
        <bpmn:startEvent id="StartEvent" name="Workflow Start">
          <bpmn:outgoing>Flow_1</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent" targetRef="PENDING_FH" />
        <bpmn:userTask id="PENDING_FH" name="Pending Functional Head" camunda:candidateGroups="FUNCTION_HEAD">
          <bpmn:incoming>Flow_1</bpmn:incoming>
          <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_2" sourceRef="PENDING_FH" targetRef="APPROVED" />
        <bpmn:endEvent id="APPROVED" name="Workflow Approved">
          <bpmn:incoming>Flow_2</bpmn:incoming>
        </bpmn:endEvent>
      </bpmn:process>
    </bpmn:definitions>
    """
    definition = BPMNDefinition(
        spec_id="RiskApprovalWorkflow",
        name="Risk Approval Process",
        version=1,
        xml_content=xml_content,
        is_active=True,
        status="Active"
    )
    db_session.add(definition)
    db_session.flush()

    config = WorkflowEntityConfig(
        entity_type="Risk",
        specification_id="RiskApprovalWorkflow",
        is_active=True
    )
    db_session.add(config)
    db_session.flush()

    # 3. Create Risk Register
    risk = RiskRegister(
        risk_id="R-1",
        risk_name="Test Risk",
        dept_id=dept.id,
        risk_owner_id=user.id,
        risk_status=status_pending_act.id,
        is_active=1,
        is_deleted=0,
        created_by=user.id,
        created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk)
    db_session.flush()

    # 4. Start workflow
    service = WorkflowService()
    service.db = db_session
    service.repository.db = db_session
    service.execution_layer.persistence_repo.db = db_session

    definition = db_session.query(BPMNDefinition).filter(BPMNDefinition.spec_id == "RiskApprovalWorkflow").first()
    print("LOADED DEFINITION XML:", definition.xml_content)

    instance = service.start_workflow(
        workflow_name="Risk Approval Workflow",
        entity_type="Risk",
        entity_id=risk.risk_register_id,
        user_id=user.id
    )
    db_session.flush()

    assert instance is not None
    assert instance.current_task_code == "PENDING_FH"

    # Verify a READY human task is generated in DB
    human_task = db_session.query(SpiffHumanTask).filter(
        SpiffHumanTask.instance_id == instance.instance_id,
        SpiffHumanTask.status == "READY"
    ).first()
    assert human_task is not None
    assert human_task.role_code == ROLE_FUNCTIONAL_HEAD

    # 5. Test approve_risk without task_id
    req = RiskApprovalRequest(
        risk_register_id=risk.risk_register_id,
        approval_status_id=7, # Approved
        remark="Dynamic task approval test"
    )

    res_risk, app_status_id, app_status_name, r_status_id, r_status_name, resolved_level = approve_risk(
        db=db_session,
        data=req,
        user_id=user.id
    )

    assert app_status_id == 7
    assert resolved_level == 1
    assert res_risk.risk_function_head_approval_status == 1 # Approved status mapping value
    assert res_risk.risk_function_head_approval_remark == "Dynamic task approval test"


def test_multiple_risks_and_validation_errors(db_session):
    # 1. Create seed data
    dept = db_session.query(Department).first()
    if not dept:
        dept = Department(dept_name="Finance", dept_short_name="FIN")
        db_session.add(dept)
        db_session.flush()

    role = db_session.query(UserRole).filter(UserRole.name == ROLE_FUNCTIONAL_HEAD).first()
    if not role:
        role = UserRole(name=ROLE_FUNCTIONAL_HEAD, description="Functional Head Role")
        db_session.add(role)
        db_session.flush()

    utype = db_session.query(UserType).filter(UserType.name == "Functional Head").first()
    if not utype:
        utype = UserType(name="Functional Head", description="FH")
        db_session.add(utype)
        db_session.flush()

    user = db_session.query(User).filter(User.log_id == "fh_user").first()
    if not user:
        user = User(
            log_id="fh_user",
            password="password",
            first_name="FH",
            last_name="User",
            email="fh@example.com",
            dept_id=dept.id,
            role_id=role.id,
            user_type_id=utype.id,
            status="Active"
        )
        db_session.add(user)
        db_session.flush()
    user_id = user.id

    status_approved = db_session.query(Status).filter(Status.id == 7).first()
    if not status_approved:
        status_approved = Status(id=7, status_name="Approved", type="approval")
        db_session.add(status_approved)
    status_pending_act = db_session.query(Status).filter(Status.id == 1).first()
    if not status_pending_act:
        status_pending_act = Status(id=1, status_name="Pending for Action", type="risk")
        db_session.add(status_pending_act)
    db_session.flush()

    db_session.query(BPMNDefinition).filter(BPMNDefinition.spec_id == "RiskApprovalWorkflow").delete()
    db_session.flush()

    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                      xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                      xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                      id="Definitions_1"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="RiskApprovalWorkflow" isExecutable="true">
        <bpmn:startEvent id="StartEvent" name="Workflow Start">
          <bpmn:outgoing>Flow_1</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent" targetRef="PENDING_FH" />
        <bpmn:userTask id="PENDING_FH" name="Pending Functional Head" camunda:candidateGroups="FUNCTION_HEAD">
          <bpmn:incoming>Flow_1</bpmn:incoming>
          <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_2" sourceRef="PENDING_FH" targetRef="APPROVED" />
        <bpmn:endEvent id="APPROVED" name="Workflow Approved">
          <bpmn:incoming>Flow_2</bpmn:incoming>
        </bpmn:endEvent>
      </bpmn:process>
    </bpmn:definitions>
    """
    definition = BPMNDefinition(
        spec_id="RiskApprovalWorkflow",
        name="Risk Approval Process",
        version=1,
        xml_content=xml_content,
        is_active=True,
        status="Active"
    )
    db_session.add(definition)
    db_session.flush()

    config = WorkflowEntityConfig(
        entity_type="Risk",
        specification_id="RiskApprovalWorkflow",
        is_active=True
    )
    db_session.add(config)
    db_session.flush()

    # Create 3 Risks
    risks = []
    instances = []
    service = WorkflowService()
    service.db = db_session
    service.repository.db = db_session
    service.execution_layer.persistence_repo.db = db_session

    for i in range(1, 4):
        risk = RiskRegister(
            risk_id=f"R-MULTI-{i}",
            risk_name=f"Multi Test Risk {i}",
            dept_id=dept.id,
            risk_owner_id=user_id,
            risk_status=status_pending_act.id,
            is_active=1,
            is_deleted=0,
            created_by=user_id,
            created_on=datetime.now(timezone.utc)
        )
        db_session.add(risk)
        db_session.flush()
        risks.append(risk)

        instance = service.start_workflow(
            workflow_name=f"Risk Approval Workflow {i}",
            entity_type="Risk",
            entity_id=risk.risk_register_id,
            user_id=user_id
        )
        db_session.flush()
        instances.append(instance)

    # Verify all 3 are in PENDING_FH state
    assert instances[0].current_task_code == "PENDING_FH"
    assert instances[1].current_task_code == "PENDING_FH"
    assert instances[2].current_task_code == "PENDING_FH"

    instance_ids = [inst.instance_id for inst in instances]
    risk_register_ids = [r.risk_register_id for r in risks]

    # Approve only Risk 2 (risks[1])
    req2 = RiskApprovalRequest(
        risk_register_id=risk_register_ids[1],
        approval_status_id=7,
        remark="Approving second risk only"
    )

    res_risk, app_status_id, app_status_name, r_status_id, r_status_name, resolved_level = approve_risk(
        db=db_session,
        data=req2,
        user_id=user_id
    )

    assert app_status_id == 7
    assert resolved_level == 1
    assert res_risk.risk_function_head_approval_status == 1

    # Check database state: Instance B should be advanced
    inst0 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == instance_ids[0]).first()
    inst1 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == instance_ids[1]).first()
    inst2 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == instance_ids[2]).first()

    assert inst0.current_task_code == "PENDING_FH"
    assert inst0.status == "Running"

    assert inst2.current_task_code == "PENDING_FH"
    assert inst2.status == "Running"

    assert inst1.status == "Completed"

    # TEST 3: Wrong/non-existing Risk
    req_nonexistent = RiskApprovalRequest(
        risk_register_id=99999,
        approval_status_id=7,
        remark="Try nonexistent"
    )
    with pytest.raises(Exception, match="Risk not found"):
        approve_risk(db=db_session, data=req_nonexistent, user_id=user_id)

    # TEST 5: Already completed task (since the instance status is Completed)
    req_already_completed = RiskApprovalRequest(
        risk_register_id=risk_register_ids[1],
        approval_status_id=7,
        remark="Try already completed risk"
    )
    with pytest.raises(Exception, match="Task not found or already completed"):
        approve_risk(db=db_session, data=req_already_completed, user_id=user_id)

    # TEST 4: Risk has workflow instance but no active human task
    human_task3 = db_session.query(SpiffHumanTask).filter(
        SpiffHumanTask.instance_id == instance_ids[2],
        SpiffHumanTask.status == "READY"
    ).first()
    assert human_task3 is not None
    human_task3.status = "COMPLETED"
    db_session.flush()

    req_no_human_task = RiskApprovalRequest(
        risk_register_id=risk_register_ids[2],
        approval_status_id=7,
        remark="Try risk with no active human task"
    )
    with pytest.raises(Exception, match="Active workflow task could not be found"):
        approve_risk(db=db_session, data=req_no_human_task, user_id=user_id)


def test_dynamic_workflow_config_suite(db_session):
    # Setup seed data
    # Department
    dept = Department(dept_name="Finance", dept_short_name="FIN")
    db_session.add(dept)
    db_session.flush()

    # User Roles
    role_fh = UserRole(name="FUNCTION_HEAD", description="Functional Head Role")
    role_rm = UserRole(name="RISK_MANAGER", description="Risk Manager Role")
    role_rh = UserRole(name="RISK_HEAD", description="Risk Head Role")
    db_session.add_all([role_fh, role_rm, role_rh])
    db_session.flush()

    # User Types
    utype_fh = UserType(name="Functional Head", description="FH")
    utype_rm = UserType(name="Risk Manager", description="RM")
    utype_rh = UserType(name="Risk Head", description="RH")
    db_session.add_all([utype_fh, utype_rm, utype_rh])
    db_session.flush()

    # Users
    user_fh = User(log_id="fh_user", password="pwd", first_name="FH", last_name="U", email="fh@example.com", dept_id=dept.id, role_id=role_fh.id, user_type_id=utype_fh.id, status="Active")
    user_rm = User(log_id="rm_user", password="pwd", first_name="RM", last_name="U", email="rm@example.com", dept_id=dept.id, role_id=role_rm.id, user_type_id=utype_rm.id, status="Active")
    user_rh = User(log_id="rh_user", password="pwd", first_name="RH", last_name="U", email="rh@example.com", dept_id=dept.id, role_id=role_rh.id, user_type_id=utype_rh.id, status="Active")
    db_session.add_all([user_fh, user_rm, user_rh])
    db_session.flush()

    # Statuses
    status_approved = Status(id=7, status_name="Approved", type="approval")
    status_rejected = Status(id=8, status_name="Rejected", type="approval")
    status_pending_act = Status(id=1, status_name="Pending for Action", type="risk")
    db_session.add_all([status_approved, status_rejected, status_pending_act])
    db_session.flush()

    # BPMN definitions
    bpmn_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                      xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                      xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                      id="Definitions_1"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="RiskApprovalWorkflow" isExecutable="true">
        <bpmn:startEvent id="StartEvent" name="Workflow Start">
          <bpmn:outgoing>Flow_1</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent" targetRef="PENDING_FH" />
        <bpmn:userTask id="PENDING_FH" name="Pending Functional Head" camunda:candidateGroups="FUNCTION_HEAD">
          <bpmn:incoming>Flow_1</bpmn:incoming>
          <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_2" sourceRef="PENDING_FH" targetRef="PENDING_RM" />
        <bpmn:userTask id="PENDING_RM" name="Pending Risk Manager" camunda:candidateGroups="RISK_MANAGER">
          <bpmn:incoming>Flow_2</bpmn:incoming>
          <bpmn:outgoing>Flow_3</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_3" sourceRef="PENDING_RM" targetRef="PENDING_RH" />
        <bpmn:userTask id="PENDING_RH" name="Pending Risk Head" camunda:candidateGroups="RISK_HEAD">
          <bpmn:incoming>Flow_3</bpmn:incoming>
          <bpmn:outgoing>Flow_4</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_4" sourceRef="PENDING_RH" targetRef="APPROVED" />
        <bpmn:endEvent id="APPROVED" name="Workflow Approved">
          <bpmn:incoming>Flow_4</bpmn:incoming>
        </bpmn:endEvent>
      </bpmn:process>
    </bpmn:definitions>
    """
    definition = BPMNDefinition(
        spec_id="RiskApprovalWorkflow",
        name="Risk Approval Process",
        version=1,
        xml_content=bpmn_xml,
        is_active=True,
        status="Active"
    )
    db_session.add(definition)
    db_session.flush()

    # Active dynamic configuration mapping
    config = WorkflowEntityConfig(
        entity_type="Risk",
        specification_id="RiskApprovalWorkflow",
        is_active=True
    )
    db_session.add(config)
    db_session.flush()

    # Service configuration
    service = WorkflowService()
    service.db = db_session
    service.repository.db = db_session
    service.execution_layer.persistence_repo.db = db_session

    # TEST 1 & 2: Create separate risks and verify separate workflow instances are created
    # Create Risk 5201
    risk_5201 = RiskRegister(
        risk_id="R-5201",
        risk_name="Risk 5201",
        dept_id=dept.id,
        risk_owner_id=user_fh.id,
        risk_status=status_pending_act.id,
        is_active=1,
        is_deleted=0,
        created_by=user_fh.id,
        created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk_5201)
    db_session.flush()

    # Submit/start workflow for Risk 5201
    instance_5201 = service.submit(
        entity_type="Risk",
        entity_id=risk_5201.risk_register_id,
        user_id=user_fh.id,
        remarks="Submitting 5201"
    )
    db_session.flush()
    id_5201 = instance_5201.instance_id

    # Create Risk 5202
    risk_5202 = RiskRegister(
        risk_id="R-5202",
        risk_name="Risk 5202",
        dept_id=dept.id,
        risk_owner_id=user_fh.id,
        risk_status=status_pending_act.id,
        is_active=1,
        is_deleted=0,
        created_by=user_fh.id,
        created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk_5202)
    db_session.flush()

    # Submit/start workflow for Risk 5202
    instance_5202 = service.submit(
        entity_type="Risk",
        entity_id=risk_5202.risk_register_id,
        user_id=user_fh.id,
        remarks="Submitting 5202"
    )
    db_session.flush()
    id_5202 = instance_5202.instance_id

    assert instance_5201 is not None
    assert instance_5202 is not None
    assert id_5201 != id_5202
    assert instance_5201.current_task_code == "PENDING_FH"
    assert instance_5202.current_task_code == "PENDING_FH"

    # TEST 3 & 4: Approve Risk 5201 as FH. Only Risk 5201 workflow/task is updated.
    # Risk 5202 remains unchanged.
    req_5201 = RiskApprovalRequest(
        risk_register_id=risk_5201.risk_register_id,
        approval_status_id=7, # Approved
        remark="FH approved 5201"
    )
    res_risk_5201, _, _, _, _, resolved_level_5201 = approve_risk(
        db=db_session,
        data=req_5201,
        user_id=user_fh.id
    )
    db_session.flush()

    assert resolved_level_5201 == 1 # FH approval level is 1
    
    # Check that 5201 progressed to RM
    inst_5201 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5201).first()
    assert inst_5201.current_task_code == "PENDING_RM"
    
    # Check that 5202 remains at FH
    inst_5202 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5202).first()
    assert inst_5202.current_task_code == "PENDING_FH"

    # Now approve Risk 5202 as FH.
    req_5202 = RiskApprovalRequest(
        risk_register_id=risk_5202.risk_register_id,
        approval_status_id=7,
        remark="FH approved 5202"
    )
    approve_risk(db=db_session, data=req_5202, user_id=user_fh.id)
    db_session.flush()

    inst_5202 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5202).first()
    assert inst_5202.current_task_code == "PENDING_RM"

    # TEST 5: Have multiple risks at different approval levels.
    # 5201 -> RM
    # 5202 -> RM (let's advance 5202 to RH)
    # Create 5203 -> RM
    # Create 5204 -> FH
    # Approve Risk 5202 as RM (making it RH). Only 5202 changes.
    
    # Let's advance 5202 to PENDING_RH by approving as RM
    req_5202_rm = RiskApprovalRequest(
        risk_register_id=risk_5202.risk_register_id,
        approval_status_id=7,
        remark="RM approved 5202"
    )
    approve_risk(db=db_session, data=req_5202_rm, user_id=user_rm.id)
    db_session.flush()

    # Create Risk 5203
    risk_5203 = RiskRegister(
        risk_id="R-5203", risk_name="Risk 5203", dept_id=dept.id, risk_owner_id=user_fh.id,
        risk_status=status_pending_act.id, is_active=1, is_deleted=0,
        created_by=user_fh.id, created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk_5203)
    db_session.flush()
    instance_5203 = service.submit(entity_type="Risk", entity_id=risk_5203.risk_register_id, user_id=user_fh.id, remarks="Submitting 5203")
    id_5203 = instance_5203.instance_id
    # Advance 5203 to RM
    req_5203_fh = RiskApprovalRequest(risk_register_id=risk_5203.risk_register_id, approval_status_id=7, remark="FH approved 5203")
    approve_risk(db=db_session, data=req_5203_fh, user_id=user_fh.id)
    db_session.flush()

    # Create Risk 5204
    risk_5204 = RiskRegister(
        risk_id="R-5204", risk_name="Risk 5204", dept_id=dept.id, risk_owner_id=user_fh.id,
        risk_status=status_pending_act.id, is_active=1, is_deleted=0,
        created_by=user_fh.id, created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk_5204)
    db_session.flush()
    instance_5204 = service.submit(entity_type="Risk", entity_id=risk_5204.risk_register_id, user_id=user_fh.id, remarks="Submitting 5204")
    db_session.flush()
    id_5204 = instance_5204.instance_id

    # At this point:
    # 5201 -> PENDING_RM
    # 5202 -> PENDING_RH
    # 5203 -> PENDING_RM
    # 5204 -> PENDING_FH
    inst_5201 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5201).first()
    inst_5202 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5202).first()
    inst_5203 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5203).first()
    inst_5204 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5204).first()

    assert inst_5201.current_task_code == "PENDING_RM"
    assert inst_5202.current_task_code == "PENDING_RH"
    assert inst_5203.current_task_code == "PENDING_RM"
    assert inst_5204.current_task_code == "PENDING_FH"

    # Now approve Risk 5202 as RH (moves it to APPROVED / Completed)
    req_5202_rh = RiskApprovalRequest(
        risk_register_id=risk_5202.risk_register_id,
        approval_status_id=7,
        remark="RH approved 5202"
    )
    approve_risk(db=db_session, data=req_5202_rh, user_id=user_rh.id)
    db_session.flush()

    # Verify that only Risk 5202 is Completed/Approved
    inst_5202 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5202).first()
    assert inst_5202.status == "Completed"

    # Verify all others are unchanged
    inst_5201 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5201).first()
    inst_5203 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5203).first()
    inst_5204 = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id_5204).first()

    assert inst_5201.current_task_code == "PENDING_RM"
    assert inst_5201.status == "Running"
    assert inst_5203.current_task_code == "PENDING_RM"
    assert inst_5203.status == "Running"
    assert inst_5204.current_task_code == "PENDING_FH"
    assert inst_5204.status == "Running"

    # TEST 6: Remove/disable workflow configuration for Risk. Attempt to submit.
    config.is_active = False
    db_session.flush()

    risk_5205 = RiskRegister(
        risk_id="R-5205", risk_name="Risk 5205", dept_id=dept.id, risk_owner_id=user_fh.id,
        risk_status=status_pending_act.id, is_active=1, is_deleted=0,
        created_by=user_fh.id, created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk_5205)
    db_session.flush()

    with pytest.raises(ValueError, match="No active workflow configuration found for entity type 'Risk'"):
        service.submit(entity_type="Risk", entity_id=risk_5205.risk_register_id, user_id=user_fh.id)

    # Verify no workflow instance was created
    inst_5205 = db_session.query(SpiffWorkflowInstance).filter(
        SpiffWorkflowInstance.entity_type == "Risk",
        SpiffWorkflowInstance.entity_id == risk_5205.risk_register_id
    ).first()
    assert inst_5205 is None

    # TEST 7: Configure a different BPMN workflow for Risk. Create/submit a new Risk.
    new_bpmn_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                      id="Definitions_2"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="FutureRiskWorkflow" isExecutable="true">
        <bpmn:startEvent id="StartEvent" name="Start">
          <bpmn:outgoing>Flow_1</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent" targetRef="PENDING_RH" />
        <bpmn:userTask id="PENDING_RH" name="Pending Risk Head" camunda:candidateGroups="RISK_HEAD">
          <bpmn:incoming>Flow_1</bpmn:incoming>
        </bpmn:userTask>
      </bpmn:process>
    </bpmn:definitions>
    """
    new_definition = BPMNDefinition(
        spec_id="FutureRiskWorkflow",
        name="Future Risk Process",
        version=1,
        xml_content=new_bpmn_xml,
        is_active=True,
        status="Active"
    )
    db_session.add(new_definition)
    db_session.flush()

    # Re-enable mapping but configured to use "FutureRiskWorkflow"
    config.specification_id = "FutureRiskWorkflow"
    config.is_active = True
    db_session.flush()

    # Submit Risk 5205 now
    instance_5205 = service.submit(
        entity_type="Risk",
        entity_id=risk_5205.risk_register_id,
        user_id=user_fh.id,
        remarks="Submitting 5205 with new workflow"
    )
    db_session.flush()
    id_5205 = instance_5205.instance_id

    assert instance_5205 is not None
    assert instance_5205.bpmn_definition_id == new_definition.id
    # Since new process starts with PENDING_RH:
    assert instance_5205.current_task_code == "PENDING_RH"


def test_phase3_visibility_permissions(db_session):
    from app.workflow.persistence.models import WorkflowTaskPermission, SpiffWorkflowInstance, BPMNDefinition
    from app.models.workflow_visibility import WorkflowVisibility
    from app.models.user import User
    from app.models.role import UserRole
    from app.models.user_type import UserType
    from app.models.mst_status import Status
    from app.models.department import Department
    from app.models.risk_register import RiskRegister
    from app.workflow.services.workflow_service import WorkflowService
    from app.services.risk_approval import approve_risk
    from app.schemas.risk_approval import RiskApprovalRequest
    from datetime import datetime, timezone
    import pytest

    service = WorkflowService(db=db_session)

    # 1. Setup departments, roles, user types, statuses
    dept = Department(dept_name="Finance Test", dept_short_name="FIN-TEST", is_deleted=0)
    db_session.add(dept)
    db_session.flush()

    role_fh = UserRole(name="FUNCTION_HEAD", description="FH")
    role_rm = UserRole(name="RISK_MANAGER", description="RM")
    role_rh = UserRole(name="RISK_HEAD", description="RH")
    db_session.add_all([role_fh, role_rm, role_rh])
    db_session.flush()

    utype_fh = UserType(name="Functional Head", description="FH")
    utype_rm = UserType(name="Risk Manager", description="RM")
    utype_rh = UserType(name="Risk Head", description="RH")
    db_session.add_all([utype_fh, utype_rm, utype_rh])
    db_session.flush()

    user_owner = User(log_id="owner_user", password="pwd", first_name="Owner", last_name="U", email="owner@example.com", dept_id=dept.id, role_id=role_fh.id, user_type_id=utype_fh.id, status="Active")
    user_fh = User(log_id="fh_user_p3", password="pwd", first_name="FH", last_name="U", email="fh_p3@example.com", dept_id=dept.id, role_id=role_fh.id, user_type_id=utype_fh.id, status="Active")
    user_rm = User(log_id="rm_user_p3", password="pwd", first_name="RM", last_name="U", email="rm_p3@example.com", dept_id=dept.id, role_id=role_rm.id, user_type_id=utype_rm.id, status="Active")
    user_rh = User(log_id="rh_user_p3", password="pwd", first_name="RH", last_name="U", email="rh_p3@example.com", dept_id=dept.id, role_id=role_rh.id, user_type_id=utype_rh.id, status="Active")
    db_session.add_all([user_owner, user_fh, user_rm, user_rh])
    db_session.flush()

    status_approved = Status(id=77, status_name="Approved", type="approval")
    status_rejected = Status(id=78, status_name="Rejected", type="approval")
    status_pending_act = Status(id=71, status_name="Pending for Action", type="risk")
    db_session.add_all([status_approved, status_rejected, status_pending_act])
    db_session.flush()

    # BPMN definitions
    bpmn_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                      id="Definitions_P3"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="Phase3Workflow" isExecutable="true">
        <bpmn:startEvent id="StartEvent" name="Workflow Start">
          <bpmn:outgoing>Flow_1</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent" targetRef="PENDING_FH" />
        <bpmn:userTask id="PENDING_FH" name="Pending Functional Head" camunda:candidateGroups="FUNCTION_HEAD">
          <bpmn:incoming>Flow_1</bpmn:incoming>
          <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_2" sourceRef="PENDING_FH" targetRef="PENDING_RM" />
        <bpmn:userTask id="PENDING_RM" name="Pending Risk Manager" camunda:candidateGroups="RISK_MANAGER">
          <bpmn:incoming>Flow_2</bpmn:incoming>
          <bpmn:outgoing>Flow_3</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_3" sourceRef="PENDING_RM" targetRef="APPROVED" />
        <bpmn:endEvent id="APPROVED" name="Workflow Approved">
          <bpmn:incoming>Flow_3</bpmn:incoming>
        </bpmn:endEvent>
      </bpmn:process>
    </bpmn:definitions>
    """
    definition = BPMNDefinition(
        spec_id="Phase3Workflow",
        name="Phase 3 Process",
        version=1,
        xml_content=bpmn_xml,
        is_active=True,
        status="Active"
    )
    db_session.add(definition)
    db_session.flush()

    # Dynamic mapping config
    config = WorkflowEntityConfig(
        entity_type="Risk",
        specification_id="Phase3Workflow",
        is_active=True
    )
    db_session.add(config)
    db_session.flush()

    # Seed permissions table
    p1 = WorkflowTaskPermission(spec_id="Phase3Workflow", task_spec_id="PENDING_FH", role_code="FUNCTION_HEAD", actions="APPROVE,REJECT", is_active=True)
    p2 = WorkflowTaskPermission(spec_id="Phase3Workflow", task_spec_id="PENDING_RM", role_code="RISK_MANAGER", actions="APPROVE,REJECT", is_active=True)
    p3 = WorkflowTaskPermission(spec_id="Phase3Workflow", task_spec_id="PENDING_RM", role_code="RISK_HEAD", actions="FORCE_APPROVE", is_active=True)
    db_session.add_all([p1, p2, p3])
    db_session.flush()

    # 2. Create and Submit a Risk
    risk = RiskRegister(
        risk_id="R-9999", risk_name="Risk Phase 3", dept_id=dept.id, risk_owner_id=user_owner.id,
        risk_status=status_pending_act.id, is_active=1, is_deleted=0,
        created_by=user_owner.id, created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk)
    db_session.flush()

    instance = service.submit(entity_type="Risk", entity_id=risk.risk_register_id, user_id=user_owner.id, remarks="Starting P3")
    db_session.flush()
    inst_id = instance.instance_id

    # 3. Verify Visibility: Owner + FH should have active visibility
    vis_records = db_session.query(WorkflowVisibility).filter(
        WorkflowVisibility.instance_id == inst_id,
        WorkflowVisibility.visibility == 1
    ).all()
    user_ids_visible = {v.user_id for v in vis_records}
    assert user_owner.id in user_ids_visible
    assert user_fh.id in user_ids_visible
    assert user_rm.id not in user_ids_visible

    # 4. Attempt unauthorized action: FH tries to FORCE_APPROVE at PENDING_FH (not allowed in p1)
    req_unauth = RiskApprovalRequest(risk_register_id=risk.risk_register_id, action="FORCE_APPROVE", remark="FH forcing")
    with pytest.raises(Exception, match="Action FORCE_APPROVE is not permitted for role FUNCTION_HEAD at task PENDING_FH"):
        approve_risk(db=db_session, data=req_unauth, user_id=user_fh.id)

    # 5. Call valid action: FH approves PENDING_FH (advances to PENDING_RM)
    req_valid = RiskApprovalRequest(risk_register_id=risk.risk_register_id, action="APPROVE", remark="FH approving")
    approve_risk(db=db_session, data=req_valid, user_id=user_fh.id)
    db_session.flush()

    # 6. Verify Visibility updated: FH removed, RM added
    vis_records = db_session.query(WorkflowVisibility).filter(
        WorkflowVisibility.instance_id == inst_id,
        WorkflowVisibility.visibility == 1
    ).all()
    user_ids_visible = {v.user_id for v in vis_records}
    assert user_owner.id in user_ids_visible
    assert user_fh.id not in user_ids_visible
    assert user_rm.id in user_ids_visible

    # 7. Call force approve as Risk Head (who has FORCE_APPROVE on PENDING_RM in p3)
    req_force = RiskApprovalRequest(risk_register_id=risk.risk_register_id, action="FORCE_APPROVE", remark="RH forcing RM")
    approve_risk(db=db_session, data=req_force, user_id=user_rh.id)
    db_session.flush()

    # Verify workflow completed
    inst_check = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == inst_id).first()
    assert inst_check.status == "Completed"

    # Verify visibility deactivated (except owner)
    vis_records = db_session.query(WorkflowVisibility).filter(
        WorkflowVisibility.instance_id == inst_id,
        WorkflowVisibility.visibility == 1
    ).all()
    user_ids_visible = {v.user_id for v in vis_records}
    assert user_owner.id in user_ids_visible
    assert user_rm.id not in user_ids_visible




