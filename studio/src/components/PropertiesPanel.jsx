import React, { useEffect, useState } from 'react'

function PropertiesPanel({ 
  selectedElement, 
  modeler, 
  workflow, 
  onUpdateWorkflow,
  activeTab,
  setActiveTab
}) {
  const [elementProps, setElementProps] = useState({
    id: '',
    name: '',
    type: '',
    candidateGroups: '',
    scriptFormat: 'python',
    script: '',
    condition: '',
    timerType: 'duration',
    timerValue: '',
    // Service task custom properties
    customProps: {}
  })

  // Load element details when selected element changes
  useEffect(() => {
    if (!selectedElement) {
      setActiveTab('general')
      return
    }

    setActiveTab('element')
    const bo = selectedElement.businessObject
    
    // Read extension properties
    const customProps = {}
    if (bo.extensionElements && bo.extensionElements.values) {
      // Look for camunda:Properties
      const propertiesContainer = bo.extensionElements.values.find(
        v => v.$type === 'camunda:Properties'
      )
      if (propertiesContainer && propertiesContainer.values) {
        propertiesContainer.values.forEach(p => {
          if (p.name) {
            customProps[p.name] = p.value || ''
          }
        })
      }
    }

    // Read timer definition details
    let timerType = 'duration'
    let timerValue = ''
    if (bo.eventDefinitions) {
      const timerDef = bo.eventDefinitions.find(
        ed => ed.$type === 'bpmn:TimerEventDefinition'
      )
      if (timerDef) {
        if (timerDef.timeDuration) {
          timerType = 'duration'
          timerValue = timerDef.timeDuration.body || ''
        } else if (timerDef.timeDate) {
          timerType = 'date'
          timerValue = timerDef.timeDate.body || ''
        } else if (timerDef.timeCycle) {
          timerType = 'cycle'
          timerValue = timerDef.timeCycle.body || ''
        }
      }
    }

    // Read sequence flow condition details
    let condition = ''
    if (bo.$type === 'bpmn:SequenceFlow' && bo.conditionExpression) {
      condition = bo.conditionExpression.body || ''
    }

    setElementProps({
      id: bo.id || '',
      name: bo.name || '',
      type: bo.$type,
      candidateGroups: bo.get('camunda:candidateGroups') || '',
      scriptFormat: bo.get('camunda:scriptFormat') || 'python',
      script: bo.get('camunda:script') || bo.script || '',
      condition,
      timerType,
      timerValue,
      customProps
    })
  }, [selectedElement])

  // Update properties in BPMN modeler
  const updateBPMNProperty = (name, value) => {
    if (!selectedElement || !modeler) return
    const modeling = modeler.get('modeling')
    
    modeling.updateProperties(selectedElement, {
      [name]: value
    })
    
    setElementProps(prev => ({ ...prev, [name]: value }))
  }

  // Update element Name attribute
  const handleNameChange = (e) => {
    const value = e.target.value
    if (!selectedElement || !modeler) return
    const modeling = modeler.get('modeling')
    modeling.updateLabel(selectedElement, value)
    setElementProps(prev => ({ ...prev, name: value }))
  }

  // Update candidateGroups for User Task
  const handleCandidateGroupsChange = (e) => {
    updateBPMNProperty('camunda:candidateGroups', e.target.value)
  }

  // Update script settings for Script Task
  const handleScriptChange = (e) => {
    const value = e.target.value
    if (!selectedElement || !modeler) return
    const modeling = modeler.get('modeling')
    modeling.updateProperties(selectedElement, {
      'camunda:script': value,
      script: value
    })
    setElementProps(prev => ({ ...prev, script: value }))
  }

  // Update custom camunda:Property extensions
  const updateCustomProps = (name, value) => {
    if (!selectedElement || !modeler) return
    const modeling = modeler.get('modeling')
    const moddle = modeler.get('moddle')
    const bo = selectedElement.businessObject

    const updatedProps = { ...elementProps.customProps, [name]: value }
    setElementProps(prev => ({ ...prev, customProps: updatedProps }))

    // Create or retrieve extension elements
    let extensionElements = bo.extensionElements
    if (!extensionElements) {
      extensionElements = moddle.create('bpmn:ExtensionElements', { values: [] })
    }

    // Find or create camunda:Properties container
    let propertiesContainer = extensionElements.values.find(
      v => v.$type === 'camunda:Properties'
    )
    if (!propertiesContainer) {
      propertiesContainer = moddle.create('camunda:Properties', { values: [] })
      extensionElements.values.push(propertiesContainer)
    }

    // Rebuild the properties list
    propertiesContainer.values = Object.entries(updatedProps)
      .filter(([k, v]) => k.trim() !== '')
      .map(([k, v]) => moddle.create('camunda:Property', { name: k, value: v }))

    modeling.updateProperties(selectedElement, {
      extensionElements: extensionElements
    })
  }

  // Update condition details for Sequence Flows
  const handleConditionChange = (e) => {
    const value = e.target.value
    if (!selectedElement || !modeler) return
    const modeling = modeler.get('modeling')
    const moddle = modeler.get('moddle')
    
    const conditionExpression = moddle.create('bpmn:FormalExpression', {
      body: value
    })
    
    modeling.updateProperties(selectedElement, {
      conditionExpression
    })
    setElementProps(prev => ({ ...prev, condition: value }))
  }

  // Update Timer Event Definitions
  const handleTimerChange = (type, value) => {
    if (!selectedElement || !modeler) return
    const modeling = modeler.get('modeling')
    const moddle = modeler.get('moddle')
    const bo = selectedElement.businessObject

    let timerEventDefinition = bo.eventDefinitions?.find(
      ed => ed.$type === 'bpmn:TimerEventDefinition'
    )

    if (!timerEventDefinition) return

    // Clear old definitions
    delete timerEventDefinition.timeDuration
    delete timerEventDefinition.timeDate
    delete timerEventDefinition.timeCycle

    if (value.trim() !== '') {
      const formalExpression = moddle.create('bpmn:FormalExpression', {
        body: value
      })
      if (type === 'duration') {
        timerEventDefinition.timeDuration = formalExpression
      } else if (type === 'date') {
        timerEventDefinition.timeDate = formalExpression
      } else if (type === 'cycle') {
        timerEventDefinition.timeCycle = formalExpression
      }
    }

    modeling.updateProperties(selectedElement, {
      eventDefinitions: bo.eventDefinitions
    })

    setElementProps(prev => ({ ...prev, timerType: type, timerValue: value }))
  }

  return (
    <div className="properties-pane">
      <div className="pane-tabs">
        <button 
          className={`tab-btn ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => setActiveTab('general')}
        >
          Workflow
        </button>
        <button 
          className={`tab-btn ${activeTab === 'element' ? 'active' : ''}`}
          disabled={!selectedElement}
          onClick={() => setActiveTab('element')}
        >
          Activity Configuration
        </button>
      </div>

      <div className="panel-content">
        {activeTab === 'general' ? (
          <div>
            <div className="form-group">
              <label className="form-label">Specification ID</label>
              <input 
                type="text" 
                className="form-control" 
                disabled 
                value={workflow?.spec_id || ''} 
              />
            </div>
            <div className="form-group">
              <label className="form-label">Workflow Name</label>
              <input 
                type="text" 
                className="form-control" 
                value={workflow?.name || ''} 
                onChange={(e) => onUpdateWorkflow('name', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea 
                className="form-control" 
                value={workflow?.description || ''} 
                onChange={(e) => onUpdateWorkflow('description', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Tags (comma-separated)</label>
              <input 
                type="text" 
                className="form-control" 
                value={workflow?.tags || ''} 
                onChange={(e) => onUpdateWorkflow('tags', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Version Status</label>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '8px' }}>
                <span className={`status-badge ${workflow?.status.toLowerCase()}`}>
                  {workflow?.status}
                </span>
                <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                  (Version {workflow?.version})
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <div className="form-group">
              <label className="form-label">BPMN Element ID</label>
              <input 
                type="text" 
                className="form-control" 
                disabled 
                value={elementProps.id} 
              />
            </div>

            <div className="form-group">
              <label className="form-label">Activity Name / Label</label>
              <input 
                type="text" 
                className="form-control" 
                value={elementProps.name} 
                onChange={handleNameChange}
              />
            </div>

            {/* User Task Editor */}
            {elementProps.type === 'bpmn:UserTask' && (
              <div className="form-group">
                <label className="form-label">Candidate Role / Group Code</label>
                <select 
                  className="form-control"
                  value={elementProps.candidateGroups}
                  onChange={handleCandidateGroupsChange}
                >
                  <option value="">Choose User Role...</option>
                  <option value="FUNCTIONAL_HEAD">Functional Head</option>
                  <option value="RISK_MANAGER">Risk Manager</option>
                  <option value="RISK_HEAD">Risk Head</option>
                  <option value="RISK_OWNER">Risk Owner</option>
                </select>
              </div>
            )}

            {/* Service Task Editor */}
            {elementProps.type === 'bpmn:ServiceTask' && (
              <div>
                <div className="form-group" style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: '16px' }}>
                  <label className="form-label">Registered Service Code</label>
                  <select 
                    className="form-control"
                    value={elementProps.name}
                    onChange={handleNameChange}
                  >
                    <option value="">Select Activity Target...</option>
                    <option value="CreateRisk">CreateRisk (Risk Creation service)</option>
                    <option value="ApproveRisk">ApproveRisk (Risk Validation service)</option>
                    <option value="SendEmail">SendEmail (SMTP Sender service)</option>
                    <option value="WebhookActivity">WebhookActivity (HTTP POST dispatch)</option>
                    <option value="UpdateDatabaseActivity">UpdateDatabaseActivity (SQL runner)</option>
                  </select>
                </div>

                {/* Conditional Properties based on selected service task code */}
                {elementProps.name === 'SendEmail' && (
                  <div style={{ marginTop: '16px' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-accent-secondary)', marginBottom: '12px' }}>Email Service Properties</h4>
                    <div className="form-group">
                      <label className="form-label">Email Event Type</label>
                      <select 
                        className="form-control"
                        value={elementProps.customProps.email_type || ''}
                        onChange={(e) => updateCustomProps('email_type', e.target.value)}
                      >
                        <option value="">Select Type...</option>
                        <option value="CREATED">CREATED (Creation alert)</option>
                        <option value="APPROVAL_SEQ">APPROVAL_SEQ (Next level notification)</option>
                        <option value="REJECTED">REJECTED (Risk rejection alert)</option>
                        <option value="FINAL_APPROVED">FINAL_APPROVED (Final approval notification)</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Level Value (Optional)</label>
                      <input 
                        type="number" 
                        className="form-control"
                        placeholder="e.g. 1, 2, 3"
                        value={elementProps.customProps.approval_level || ''}
                        onChange={(e) => updateCustomProps('approval_level', e.target.value)}
                      />
                    </div>
                  </div>
                )}

                {elementProps.name === 'WebhookActivity' && (
                  <div style={{ marginTop: '16px' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-accent-secondary)', marginBottom: '12px' }}>Webhook Config</h4>
                    <div className="form-group">
                      <label className="form-label">Destination URL</label>
                      <input 
                        type="text" 
                        className="form-control"
                        placeholder="https://api.external.com/endpoint"
                        value={elementProps.customProps.url || ''}
                        onChange={(e) => updateCustomProps('url', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">HTTP Method</label>
                      <select 
                        className="form-control"
                        value={elementProps.customProps.method || 'POST'}
                        onChange={(e) => updateCustomProps('method', e.target.value)}
                      >
                        <option value="GET">GET</option>
                        <option value="POST">POST</option>
                        <option value="PUT">PUT</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Custom Payload Expression</label>
                      <textarea 
                        className="form-control"
                        placeholder='{"risk_id": "${risk_id}"}'
                        value={elementProps.customProps.payload || ''}
                        onChange={(e) => updateCustomProps('payload', e.target.value)}
                      />
                    </div>
                  </div>
                )}

                {elementProps.name === 'UpdateDatabaseActivity' && (
                  <div style={{ marginTop: '16px' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-accent-secondary)', marginBottom: '12px' }}>Database Config</h4>
                    <div className="form-group">
                      <label className="form-label">Table Name</label>
                      <input 
                        type="text" 
                        className="form-control"
                        placeholder="ers.mst_users"
                        value={elementProps.customProps.database_table || ''}
                        onChange={(e) => updateCustomProps('database_table', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Columns Mapping</label>
                      <input 
                        type="text" 
                        className="form-control"
                        placeholder="status, modified_by"
                        value={elementProps.customProps.columns || ''}
                        onChange={(e) => updateCustomProps('columns', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Values Expressions</label>
                      <input 
                        type="text" 
                        className="form-control"
                        placeholder="'Active', ${user_id}"
                        value={elementProps.customProps.values || ''}
                        onChange={(e) => updateCustomProps('values', e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Script Task Editor */}
            {elementProps.type === 'bpmn:ScriptTask' && (
              <div className="form-group">
                <label className="form-label">Python Script Execution Code</label>
                <textarea 
                  className="form-control"
                  style={{ fontFamily: 'monospace', fontSize: '13px' }}
                  placeholder="# Enter Python script here&#10;context.set_variable('approved', True)"
                  value={elementProps.script}
                  onChange={handleScriptChange}
                />
              </div>
            )}

            {/* Sequence Flow Condition Editor */}
            {elementProps.type === 'bpmn:SequenceFlow' && (
              <div className="form-group">
                <label className="form-label">Routing Condition Expression</label>
                <input 
                  type="text" 
                  className="form-control"
                  placeholder="e.g. approval_status_id == 7"
                  value={elementProps.condition}
                  onChange={handleConditionChange}
                />
              </div>
            )}

            {/* Timer Editor */}
            {elementProps.id.toLowerCase().includes('timer') || 
             selectedElement.businessObject.eventDefinitions?.some(ed => ed.$type === 'bpmn:TimerEventDefinition') ? (
              <div>
                <div className="form-group">
                  <label className="form-label">Timer Mode</label>
                  <select 
                    className="form-control"
                    value={elementProps.timerType}
                    onChange={(e) => handleTimerChange(e.target.value, elementProps.timerValue)}
                  >
                    <option value="duration">Duration (e.g. PT5M)</option>
                    <option value="date">Date (e.g. ISO Timestamp)</option>
                    <option value="cycle">Cycle (e.g. Cron expression)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Timer Expression Value</label>
                  <input 
                    type="text" 
                    className="form-control"
                    placeholder="e.g. PT10M"
                    value={elementProps.timerValue}
                    onChange={(e) => handleTimerChange(elementProps.timerType, e.target.value)}
                  />
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}

export default PropertiesPanel
