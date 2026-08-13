from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.workflow.persistence.models import BPMNDefinition
from app.workflow_management.schemas import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowDefinitionResponse,
    ValidationResponse
)
from app.workflow_management.services import WorkflowManagementService

router = APIRouter(prefix="/workflow/definitions", tags=["Workflow Management Platform"])


# 1. GET /workflow/definitions
@router.get("", response_model=Dict[str, Any])
def list_workflow_definitions(
    status: Optional[str] = Query(None, description="Filter by status: 'Draft', 'Published', 'Active', 'Archived'"),
    spec_id: Optional[str] = Query(None, description="Filter by specification ID"),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        query = db.query(BPMNDefinition)
        if status:
            query = query.filter(BPMNDefinition.status == status)
        if spec_id:
            query = query.filter(BPMNDefinition.spec_id == spec_id)
            
        definitions = query.order_by(BPMNDefinition.spec_id.asc(), BPMNDefinition.version.desc()).all()
        
        result = []
        for d in definitions:
            result.append({
                "id": d.id,
                "spec_id": d.spec_id,
                "name": d.name or d.spec_id,
                "version": d.version,
                "description": d.description,
                "xml_content": d.xml_content,
                "is_active": d.is_active,
                "status": d.status,
                "tags": d.tags,
                "created_by": d.created_by,
                "created_on": d.created_on,
                "updated_on": getattr(d, "updated_on", d.created_on),
                "published_on": getattr(d, "published_on", None)
            })
            
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 2. GET /workflow/definitions/{id}
@router.get("/{id}")
def get_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        d = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not d:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
            
        return success_response(data={
            "id": d.id,
            "spec_id": d.spec_id,
            "name": d.name or d.spec_id,
            "version": d.version,
            "description": d.description,
            "xml_content": d.xml_content,
            "is_active": d.is_active,
            "status": d.status,
            "tags": d.tags,
            "created_by": d.created_by,
            "created_on": d.created_on,
            "updated_on": getattr(d, "updated_on", d.created_on),
            "published_on": getattr(d, "published_on", None)
        })
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 3. POST /workflow/definitions
@router.post("")
def create_workflow_definition(
    payload: WorkflowCreateRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if version 1 for this spec_id already exists
        exists = db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == payload.spec_id,
            BPMNDefinition.version == 1
        ).first()
        
        if exists:
            raise HTTPException(status_code=400, detail=f"Draft Version 1 for specification ID '{payload.spec_id}' already exists.")

        # Supply a default skeleton XML if none is passed
        xml_content = payload.xml_content
        if not xml_content:
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
            <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                              xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                              xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                              xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                              xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                              id="Definitions_1"
                              targetNamespace="http://bpmn.io/schema/bpmn">
              <bpmn:process id="{payload.spec_id}" isExecutable="true">
                <bpmn:startEvent id="StartEvent_1" name="Start"/>
              </bpmn:process>
              <bpmndi:BPMNDiagram id="BPMNDiagram_1">
                <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{payload.spec_id}">
                  <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
                    <dc:Bounds x="173" y="102" width="36" height="36"/>
                  </bpmndi:BPMNShape>
                </bpmndi:BPMNPlane>
              </bpmndi:BPMNDiagram>
            </bpmn:definitions>
            """

        new_def = BPMNDefinition(
            spec_id=payload.spec_id,
            name=payload.name,
            version=1,
            description=payload.description or "Workflow Draft Definition",
            xml_content=xml_content,
            is_active=False,
            status="Draft",
            tags=payload.tags,
            created_by=current_user["id"],
            created_on=datetime.utcnow()
        )
        db.add(new_def)
        db.commit()
        db.refresh(new_def)
        
        return success_response(data={"id": new_def.id, "spec_id": new_def.spec_id}, message="Workflow Draft created successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 4. PUT /workflow/definitions/{id}
@router.put("/{id}")
def update_workflow_definition(
    id: int,
    payload: WorkflowUpdateRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        # Draft versions can be updated in-place. Published versions are read-only.
        if definition.status != "Draft" and definition.version != 1:
            raise HTTPException(status_code=400, detail="Only Draft / Version 1 specifications can be edited in-place.")

        if payload.name:
            definition.name = payload.name
        if payload.description:
            definition.description = payload.description
        if payload.xml_content:
            definition.xml_content = payload.xml_content
        if payload.tags:
            definition.tags = payload.tags
            
        definition.updated_on = datetime.utcnow()
        db.commit()
        
        return success_response(message="Draft workflow updated successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 5. DELETE /workflow/definitions/{id}
@router.delete("/{id}")
def delete_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        # Active production workflows cannot be deleted directly
        if definition.is_active:
            raise HTTPException(status_code=400, detail="Active production workflow versions cannot be deleted. Deactivate it first.")

        db.delete(definition)
        db.commit()
        return success_response(message="Workflow version deleted successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 6. POST /workflow/definitions/{id}/validate
@router.post("/{id}/validate")
def validate_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        errors = WorkflowManagementService.validate_bpmn(definition.xml_content, definition.spec_id)
        is_valid = len([e for e in errors if e.severity == "Error"]) == 0
        
        return success_response(data={
            "is_valid": is_valid,
            "errors": [e.dict() for e in errors]
        })
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 7. POST /workflow/definitions/{id}/publish
@router.post("/{id}/publish")
def publish_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        published = WorkflowManagementService.publish_workflow(db, id, current_user["id"])
        return success_response(
            data={"id": published.id, "version": published.version}, 
            message=f"Workflow successfully published as Version {published.version}"
        )
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 8. POST /workflow/definitions/{id}/activate
@router.post("/{id}/activate")
def activate_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        # Deactivate all versions of this spec_id
        db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == definition.spec_id
        ).update({"is_active": False, "status": "Published"})

        # Mark this version active
        definition.is_active = True
        definition.status = "Active"
        db.commit()
        
        return success_response(message=f"Workflow version {definition.version} activated successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 9. POST /workflow/definitions/{id}/duplicate
@router.post("/{id}/duplicate")
def duplicate_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        cloned = WorkflowManagementService.duplicate_workflow(db, id, current_user["id"])
        return success_response(
            data={"id": cloned.id, "spec_id": cloned.spec_id},
            message=f"Cloned into new draft specification '{cloned.spec_id}' successfully"
        )
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 10. POST /workflow/definitions/import
@router.post("/import")
def import_workflow_bpmn(
    spec_id: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        xml_bytes = file.file.read()
        xml_content = xml_bytes.decode("utf-8")
        
        # Validate XML structure
        errors = WorkflowManagementService.validate_bpmn(xml_content, spec_id)
        critical_errors = [e for e in errors if e.severity == "Error"]
        if critical_errors:
            raise HTTPException(status_code=400, detail=f"Imported BPMN is structurally invalid: {[e.message for e in critical_errors]}")

        # Check duplicate Version 1 draft
        exists = db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == spec_id,
            BPMNDefinition.version == 1
        ).first()

        if exists:
            raise HTTPException(status_code=400, detail=f"Draft Version 1 for specification ID '{spec_id}' already exists.")

        new_def = BPMNDefinition(
            spec_id=spec_id,
            name=name,
            version=1,
            description=description or "Imported BPMN specification",
            xml_content=xml_content,
            is_active=False,
            status="Draft",
            tags=tags,
            created_by=current_user["id"],
            created_on=datetime.utcnow()
        )
        db.add(new_def)
        db.commit()
        db.refresh(new_def)
        
        return success_response(data={"id": new_def.id, "spec_id": new_def.spec_id}, message="BPMN imported successfully as Draft Version 1")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 11. GET /workflow/definitions/{id}/export
@router.get("/{id}/export")
def export_workflow_bpmn(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
            
        headers = {
            "Content-Disposition": f"attachment; filename={definition.spec_id}_v{definition.version}.bpmn"
        }
        return Response(content=definition.xml_content, media_type="application/xml", headers=headers)
    except Exception as e:
        return error_response(message=str(e), status_code=400)
