import React, { useEffect, useRef, useState } from 'react'
import BpmnModeler from 'bpmn-js/lib/Modeler'
import camundaModdleDescriptor from 'camunda-bpmn-moddle/resources/camunda'
import 'bpmn-js/dist/assets/diagram-js.css'
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'
import { 
  ArrowLeft, 
  Save, 
  CheckSquare, 
  Play, 
  Download, 
  Undo2, 
  Redo2, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  ChevronDown, 
  ChevronUp, 
  AlertTriangle, 
  X,
  FileCode,
  FolderOpen,
  Loader
} from 'lucide-react'
import PropertiesPanel from './PropertiesPanel'

function Designer({ workflowId, onClose, showToast }) {
  const canvasRef = useRef(null)
  const [modeler, setModeler] = useState(null)
  const [workflow, setWorkflow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  
  // Element selection state
  const [selectedElement, setSelectedElement] = useState(null)
  const [explorerElements, setExplorerElements] = useState([])
  const [activeTab, setActiveTab] = useState('general')

  // Validation state
  const [validationErrors, setValidationErrors] = useState([])
  const [isValidationOpen, setIsValidationOpen] = useState(false)

  // Fetch workflow definition XML
  useEffect(() => {
    const fetchWorkflow = async () => {
      setLoading(true)
      try {
        const response = await fetch(`/workflow/definitions/${workflowId}`)
        const result = await response.json()
        const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
        if (isSuccess) {
          setWorkflow(result.data)
        } else {
          showToast(result?.Error?.Error_message || result?.message || 'Failed to fetch definition details', 'error')
          onClose()
        }
      } catch (error) {
        showToast('Network error while loading definition', 'error')
        onClose()
      } finally {
        setLoading(false)
      }
    }
    fetchWorkflow()
  }, [workflowId])

  // Initialize BPMN.io Modeler
  useEffect(() => {
    if (loading || !workflow || !canvasRef.current) return

    const bpmnModeler = new BpmnModeler({
      container: canvasRef.current,
      keyboard: { bindTo: window },
      moddleExtensions: {
        camunda: camundaModdleDescriptor
      }
    })

    // Import BPMN XML
    bpmnModeler.importXML(workflow.xml_content)
      .then(({ warnings }) => {
        if (warnings && warnings.length) {
          console.warn('BPMN Import Warnings:', warnings)
        }
        bpmnModeler.get('canvas').zoom('fit-viewport')
        updateExplorer(bpmnModeler)
      })
      .catch((err) => {
        showToast(`Failed to parse BPMN diagram XML: ${err.message}`, 'error')
      })

    // Listen to changes to track unsaved status
    bpmnModeler.on('commandStack.changed', () => {
      setHasUnsavedChanges(true)
      updateExplorer(bpmnModeler)
    })

    // Listen to selections
    bpmnModeler.on('selection.changed', (e) => {
      const selection = e.newSelection
      if (selection && selection.length > 0) {
        setSelectedElement(selection[0])
      } else {
        setSelectedElement(null)
      }
    })

    setModeler(bpmnModeler)

    // Alert on page unload if changes are unsaved
    const handleBeforeUnload = (e) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      bpmnModeler.destroy()
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [loading])

  // Update Left Sidebar Explorer tree list
  const updateExplorer = (activeModeler) => {
    if (!activeModeler) return
    try {
      const elementRegistry = activeModeler.get('elementRegistry')
      const elements = elementRegistry.getAll()
        .filter(el => el.type !== 'label' && el.businessObject && el.businessObject.id)
        .map(el => ({
          id: el.businessObject.id,
          name: el.businessObject.name || el.businessObject.id,
          type: el.type,
          element: el
        }))
      setExplorerElements(elements)
    } catch (e) {
      console.error('Explorer failed to index elements:', e)
    }
  }

  // Select element from Explorer list
  const handleSelectExplorerItem = (el) => {
    if (!modeler) return
    const selection = modeler.get('selection')
    selection.select(el.element)
    
    // Zoom/Scroll to element
    const canvas = modeler.get('canvas')
    canvas.scrollToElement(el.element)
  }

  // Update local workflow state
  const handleUpdateWorkflow = (key, value) => {
    setWorkflow(prev => ({ ...prev, [key]: value }))
    setHasUnsavedChanges(true)
  }

  // Modeler Zoom Actions
  const handleZoom = (action) => {
    if (!modeler) return
    const canvas = modeler.get('canvas')
    if (action === 'in') {
      canvas.zoom(canvas.zoom() + 0.1)
    } else if (action === 'out') {
      canvas.zoom(canvas.zoom() - 0.1)
    } else {
      canvas.zoom('fit-viewport')
    }
  }

  // Modeler Undo/Redo Actions
  const handleUndoRedo = (action) => {
    if (!modeler) return
    const commandStack = modeler.get('commandStack')
    if (action === 'undo') {
      commandStack.undo()
    } else {
      commandStack.redo()
    }
  }

  // Save changes to database
  const handleSave = async () => {
    if (!modeler || !workflow) return
    try {
      const { xml } = await modeler.saveXML({ format: true })
      
      const payload = {
        name: workflow.name,
        description: workflow.description,
        tags: workflow.tags,
        xml_content: xml
      }

      const response = await fetch(`/workflow/definitions/${workflowId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast('Draft workflow saved successfully', 'success')
        setHasUnsavedChanges(false)
        
        // Refresh workflow metadata to capture updated dates
        setWorkflow(prev => ({
          ...prev,
          xml_content: xml
        }))
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Failed to save workflow', 'error')
      }
    } catch (error) {
      showToast('Save failed due to network error', 'error')
    }
  }

  // Validate workflow XML using SpiffWorkflow Parser
  const handleValidate = async () => {
    if (!modeler || !workflow) return
    try {
      // Fetch latest XML state from Modeler canvas
      const { xml } = await modeler.saveXML({ format: true })
      
      // Save draft first automatically
      const saveResponse = await fetch(`/workflow/definitions/${workflowId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: workflow.name,
          description: workflow.description,
          tags: workflow.tags,
          xml_content: xml
        })
      })
      await saveResponse.json()
      setHasUnsavedChanges(false)

      // Trigger validator
      const response = await fetch(`/workflow/definitions/${workflowId}/validate`, {
        method: 'POST'
      })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        setValidationErrors(result.data.errors || [])
        setIsValidationOpen(true)
        if (result.data.is_valid) {
          showToast('BPMN diagram is compilation-ready! No errors found.', 'success')
        } else {
          showToast(`Workflow validation failed: Found ${result.data.errors.length} errors/warnings.`, 'error')
        }
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Validation failed', 'error')
      }
    } catch (error) {
      showToast('Validation failed due to network error', 'error')
    }
  }

  // Publish workflow draft
  const handlePublish = async () => {
    if (hasUnsavedChanges) {
      if (!window.confirm('You have unsaved changes. Save and publish?')) {
        return
      }
      await handleSave()
    }

    try {
      const response = await fetch(`/workflow/definitions/${workflowId}/publish`, {
        method: 'POST'
      })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'Workflow successfully published!', 'success')
        // Go back to Dashboard to refresh definitions list
        onClose()
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Publishing failed', 'error')
      }
    } catch (error) {
      showToast('Publishing failed', 'error')
    }
  }

  // Export/Download BPMN XML
  const handleExport = () => {
    window.location.href = `/workflow/definitions/${workflowId}/export`
    showToast('Downloading BPMN diagram file...', 'success')
  }

  // Safe Exit Handler
  const handleClose = () => {
    if (hasUnsavedChanges) {
      if (!window.confirm('You have unsaved changes that will be lost. Exit anyway?')) {
        return
      }
    }
    onClose()
  }

  // Select and focus error node in Modeler
  const handleSelectErrorNode = (nodeId) => {
    if (!modeler || !nodeId) return
    try {
      const elementRegistry = modeler.get('elementRegistry')
      const element = elementRegistry.get(nodeId)
      if (element) {
        modeler.get('selection').select(element)
        modeler.get('canvas').scrollToElement(element)
      } else {
        showToast(`Element with ID '${nodeId}' not found in current view.`, 'error')
      }
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', flexGrow: 1, justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Loader className="spinner" size={32} color="var(--color-accent-secondary)" />
      </div>
    )
  }

  return (
    <div className="designer-view">
      {/* Left Sidebar: Explorer */}
      <div className="explorer-sidebar">
        <h4 className="explorer-title">Diagram Explorer</h4>
        {explorerElements.length === 0 ? (
          <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>No activities loaded.</span>
        ) : (
          <ul className="explorer-list">
            {explorerElements.map(el => (
              <li 
                key={el.id}
                className={`explorer-item ${selectedElement?.businessObject.id === el.id ? 'active' : ''}`}
                onClick={() => handleSelectExplorerItem(el)}
              >
                <FolderOpen size={13} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={el.name}>
                  {el.name}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Center Pane: BPMN Modeler Canvas */}
      <div className="canvas-area">
        <div ref={canvasRef} className="bpmn-container" />

        {/* Floating Modeler Canvas Toolbar */}
        <div className="designer-toolbar">
          <button className="toolbar-btn" title="Save Draft" onClick={handleSave}>
            <Save size={16} />
          </button>
          <button className="toolbar-btn" title="Validate Diagram" onClick={handleValidate}>
            <CheckSquare size={16} />
          </button>
          {workflow?.status === 'Draft' && (
            <button className="toolbar-btn" style={{ color: 'var(--color-accent-secondary)' }} title="Publish Version" onClick={handlePublish}>
              <Play size={16} />
            </button>
          )}
          <span style={{ width: '1px', background: 'var(--border-glass)', margin: '0 4px' }} />
          <button className="toolbar-btn" title="Undo" onClick={() => handleUndoRedo('undo')}>
            <Undo2 size={16} />
          </button>
          <button className="toolbar-btn" title="Redo" onClick={() => handleUndoRedo('redo')}>
            <Redo2 size={16} />
          </button>
          <span style={{ width: '1px', background: 'var(--border-glass)', margin: '0 4px' }} />
          <button className="toolbar-btn" title="Zoom In" onClick={() => handleZoom('in')}>
            <ZoomIn size={16} />
          </button>
          <button className="toolbar-btn" title="Zoom Out" onClick={() => handleZoom('out')}>
            <ZoomOut size={16} />
          </button>
          <button className="toolbar-btn" title="Zoom Fit" onClick={() => handleZoom('fit')}>
            <Maximize2 size={16} />
          </button>
          <span style={{ width: '1px', background: 'var(--border-glass)', margin: '0 4px' }} />
          <button className="toolbar-btn" title="Download BPMN" onClick={handleExport}>
            <Download size={16} />
          </button>
          <button className="toolbar-btn" style={{ color: 'var(--color-error)' }} title="Exit Designer" onClick={handleClose}>
            <ArrowLeft size={16} />
          </button>
        </div>

        {/* Validation Errorscollapsible bar */}
        <div className="validation-footer" style={{ height: isValidationOpen ? '220px' : '45px' }}>
          <div className="validation-header" onClick={() => setIsValidationOpen(!isValidationOpen)}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={14} color={validationErrors.length > 0 ? 'var(--color-error)' : 'var(--color-success)'} />
              <span style={{ fontSize: '13px', fontWeight: '600' }}>
                BPMN Compiler Validation ({validationErrors.length} issues)
              </span>
            </div>
            {isValidationOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </div>

          {isValidationOpen && (
            <div className="error-list">
              {validationErrors.length === 0 ? (
                <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', textAlign: 'center', padding: '16px' }}>
                  No warnings or compilation errors. The workflow is structurally healthy.
                </div>
              ) : (
                validationErrors.map((err, idx) => (
                  <div 
                    key={idx} 
                    className={`error-item ${err.severity.toLowerCase()}`}
                    style={{ cursor: err.node_id ? 'pointer' : 'default' }}
                    onClick={() => err.node_id && handleSelectErrorNode(err.node_id)}
                    title={err.node_id ? 'Click to focus activity' : ''}
                  >
                    <span style={{ fontWeight: '700', fontSize: '11px', textTransform: 'uppercase' }}>
                      {err.severity}
                    </span>
                    <span style={{ flexGrow: 1 }}>
                      {err.node_name ? `[${err.node_name}] ` : ''}{err.message}
                    </span>
                    {err.node_id && (
                      <span style={{ fontSize: '11px', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px' }}>
                        Focus
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Sidebar: Properties Panel */}
      <PropertiesPanel 
        selectedElement={selectedElement} 
        modeler={modeler}
        workflow={workflow}
        onUpdateWorkflow={handleUpdateWorkflow}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />
    </div>
  )
}

export default Designer
