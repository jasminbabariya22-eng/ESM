import React, { useState, useEffect } from 'react'
import { 
  Plus, 
  Search, 
  Filter, 
  FileCode, 
  Trash2, 
  Copy, 
  Download, 
  Upload, 
  Check, 
  Zap,
  Globe,
  Loader,
  X
} from 'lucide-react'

function Dashboard({ onOpenDesigner, showToast }) {
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  
  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  
  // Form payloads
  const [newDraft, setNewDraft] = useState({ spec_id: '', name: '', description: '', tags: '' })
  const [importDraft, setImportDraft] = useState({ spec_id: '', name: '', description: '', tags: '', file: null })
  const [submitting, setSubmitting] = useState(false)

  // Fetch all workflow definitions
  const fetchWorkflows = async () => {
    setLoading(true)
    try {
      const response = await fetch('/workflow/definitions')
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        setWorkflows(result.data || [])
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Failed to fetch definitions', 'error')
      }
    } catch (error) {
      showToast('Network error while loading definitions', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkflows()
  }, [])

  // Create Draft Definition
  const handleCreateDraft = async (e) => {
    e.preventDefault()
    if (!newDraft.spec_id || !newDraft.name) {
      showToast('Specification ID and Name are required.', 'error')
      return
    }
    setSubmitting(true)
    try {
      const response = await fetch('/workflow/definitions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newDraft)
      })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'Draft created successfully', 'success')
        setShowCreateModal(false)
        setNewDraft({ spec_id: '', name: '', description: '', tags: '' })
        fetchWorkflows()
        // Open directly in designer
        if (result.data && result.data.id) {
          onOpenDesigner(result.data.id)
        }
      } else {
        showToast(result.detail || result?.Error?.Error_message || result?.message || 'Failed to create draft', 'error')
      }
    } catch (error) {
      showToast('Failed to create draft due to network issue', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // Import BPMN File
  const handleImportBPMN = async (e) => {
    e.preventDefault()
    if (!importDraft.spec_id || !importDraft.name || !importDraft.file) {
      showToast('All fields and a BPMN file selection are required.', 'error')
      return
    }
    setSubmitting(true)
    const formData = new FormData()
    formData.append('spec_id', importDraft.spec_id)
    formData.append('name', importDraft.name)
    formData.append('description', importDraft.description)
    formData.append('tags', importDraft.tags)
    formData.append('file', importDraft.file)

    try {
      const response = await fetch('/workflow/definitions/import', {
        method: 'POST',
        body: formData
      })
      const result = await response.json()
      const isSuccess = response.ok && result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'BPMN specification imported successfully', 'success')
        setShowImportModal(false)
        setImportDraft({ spec_id: '', name: '', description: '', tags: '', file: null })
        fetchWorkflows()
        if (result.data && result.data.id) {
          onOpenDesigner(result.data.id)
        }
      } else {
        showToast(result.detail || result?.Error?.Error_message || result?.message || 'BPMN structural validation failed', 'error')
      }
    } catch (error) {
      showToast('BPMN import failed', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // Publish Draft
  const handlePublish = async (id, e) => {
    e.stopPropagation()
    try {
      const response = await fetch(`/workflow/definitions/${id}/publish`, { method: 'POST' })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'Workflow published successfully', 'success')
        fetchWorkflows()
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Publishing failed', 'error')
      }
    } catch (err) {
      showToast('Network error while publishing', 'error')
    }
  }

  // Activate Version
  const handleActivate = async (id, e) => {
    e.stopPropagation()
    try {
      const response = await fetch(`/workflow/definitions/${id}/activate`, { method: 'POST' })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'Workflow version activated', 'success')
        fetchWorkflows()
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Activation failed', 'error')
      }
    } catch (err) {
      showToast('Network error while activating', 'error')
    }
  }

  // Deactivate Version
  const handleDeactivate = async (id, e) => {
    e.stopPropagation()
    try {
      const response = await fetch(`/workflow/definitions/${id}/deactivate`, { method: 'POST' })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'Workflow version deactivated successfully', 'success')
        fetchWorkflows()
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Deactivation failed', 'error')
      }
    } catch (err) {
      showToast('Network error while deactivating', 'error')
    }
  }

  // Clone/Duplicate Draft
  const handleDuplicate = async (id, e) => {
    e.stopPropagation()
    try {
      const response = await fetch(`/workflow/definitions/${id}/duplicate`, { method: 'POST' })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'Cloned draft specification successfully', 'success')
        fetchWorkflows()
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Cloning failed', 'error')
      }
    } catch (err) {
      showToast('Network error while duplicating', 'error')
    }
  }

  // Delete Version
  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this workflow version? This action is permanent.')) {
      return
    }
    try {
      const response = await fetch(`/workflow/definitions/${id}`, { method: 'DELETE' })
      const result = await response.json()
      const isSuccess = result && (result.status === 'success' || (result.Error && !result.Error.Error));
      if (isSuccess) {
        showToast(result?.Error?.Error_message || result?.message || 'Deleted successfully', 'success')
        fetchWorkflows()
      } else {
        showToast(result?.Error?.Error_message || result?.message || 'Deletion rejected: Active production versions cannot be deleted.', 'error')
      }
    } catch (err) {
      showToast('Network error while deleting', 'error')
    }
  }

  // Export BPMN File
  const handleExport = (id, specId, version, e) => {
    e.stopPropagation()
    window.location.href = `/workflow/definitions/${id}/export`
    showToast(`Downloading BPMN diagram for ${specId} v${version}...`, 'success')
  }

  // Filters and queries calculations
  const filteredWorkflows = workflows.filter(wf => {
    const matchesSearch = 
      (wf.spec_id && wf.spec_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (wf.name && wf.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (wf.description && wf.description.toLowerCase().includes(searchQuery.toLowerCase()))
      
    const matchesStatus = statusFilter === '' || wf.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  return (
    <div className="dashboard-view">
      <div className="dashboard-header-actions">
        <div className="search-filter-box">
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            <input 
              type="text" 
              placeholder="Search specifications..." 
              className="search-input"
              style={{ paddingLeft: '36px' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Filter size={16} color="var(--color-text-muted)" />
            <select 
              className="filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="Draft">Draft</option>
              <option value="Published">Published</option>
              <option value="Active">Active</option>
              <option value="Archived">Archived</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => setShowImportModal(true)}>
            <Upload size={16} />
            <span>Import BPMN</span>
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={18} />
            <span>New Workflow</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
          <Loader className="spinner" size={32} color="var(--color-accent-secondary)" />
        </div>
      ) : filteredWorkflows.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '80px 0', border: '1px dashed var(--border-glass)', borderRadius: '12px', background: 'var(--bg-card)' }}>
          <FileCode size={48} color="var(--color-text-muted)" style={{ marginBottom: '16px' }} />
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: '500', marginBottom: '8px' }}>No workflows found</h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>Create a new draft or import a BPMN file to start designing.</p>
        </div>
      ) : (
        <div className="glass-table-container">
          <table className="glass-table">
            <thead>
              <tr>
                <th>Specification ID</th>
                <th>Process Name</th>
                <th>Version</th>
                <th>Status</th>
                <th>Tags</th>
                <th>Last Updated</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredWorkflows.map(wf => (
                <tr key={wf.id} onClick={() => onOpenDesigner(wf.id)}>
                  <td style={{ fontWeight: '600', color: 'var(--color-accent-secondary)' }}>{wf.spec_id}</td>
                  <td style={{ fontWeight: '500' }}>{wf.name}</td>
                  <td>v{wf.version}</td>
                  <td>
                    <span className={`status-badge ${wf.status.toLowerCase()}`}>
                      {wf.status}
                    </span>
                  </td>
                  <td>{wf.tags ? wf.tags.split(',').map(tag => (
                    <span key={tag} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-glass)', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', marginRight: '4px' }}>
                      {tag.trim()}
                    </span>
                  )) : <span style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>—</span>}</td>
                  <td style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>
                    {new Date(wf.updated_on || wf.created_on).toLocaleString()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', justifyItems: 'flex-end', justifyContent: 'flex-end', gap: '8px' }}>
                      {wf.status === 'Draft' && (
                        <button className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(0, 229, 255, 0.3)', color: 'var(--color-accent-secondary)' }} onClick={(e) => handlePublish(wf.id, e)}>
                          <Globe size={12} />
                          <span>Publish</span>
                        </button>
                      )}
                      {wf.status === 'Published' && (
                        <button className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(0, 230, 118, 0.3)', color: 'var(--color-success)' }} onClick={(e) => handleActivate(wf.id, e)}>
                          <Zap size={12} />
                          <span>Activate</span>
                        </button>
                      )}
                      {wf.is_active && (
                        <button className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(255, 171, 0, 0.3)', color: 'var(--color-warning)' }} onClick={(e) => handleDeactivate(wf.id, e)}>
                          <Zap size={12} style={{ opacity: 0.6 }} />
                          <span>Deactivate</span>
                        </button>
                      )}
                      <button className="btn btn-secondary btn-sm" title="Duplicate Specification" onClick={(e) => handleDuplicate(wf.id, e)}>
                        <Copy size={12} />
                      </button>
                      <button className="btn btn-secondary btn-sm" title="Download BPMN File" onClick={(e) => handleExport(wf.id, wf.spec_id, wf.version, e)}>
                        <Download size={12} />
                      </button>
                      <button className="btn btn-danger btn-sm" title="Delete Version" onClick={(e) => handleDelete(wf.id, e)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: Create Workflow Draft */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <span className="modal-title">Create Workflow Specification</span>
              <X size={18} style={{ cursor: 'pointer', color: 'var(--color-text-muted)' }} onClick={() => setShowCreateModal(false)} />
            </div>
            <form onSubmit={handleCreateDraft}>
              <div className="form-group">
                <label className="form-label">Specification ID (unique key)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. RiskApprovalWorkflow"
                  required
                  value={newDraft.spec_id}
                  onChange={(e) => setNewDraft({ ...newDraft, spec_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Friendly Process Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. Risk Audit Approval Flow"
                  required
                  value={newDraft.name}
                  onChange={(e) => setNewDraft({ ...newDraft, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="Short explanation of workflow triggers and tasks"
                  value={newDraft.description}
                  onChange={(e) => setNewDraft({ ...newDraft, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Tags (comma-separated)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="risk, audit, finance"
                  value={newDraft.tags}
                  onChange={(e) => setNewDraft({ ...newDraft, tags: e.target.value })}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? <Loader className="spinner" size={14} /> : 'Create Draft'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Import BPMN */}
      {showImportModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <span className="modal-title">Import BPMN 2.0 Specification</span>
              <X size={18} style={{ cursor: 'pointer', color: 'var(--color-text-muted)' }} onClick={() => setShowImportModal(false)} />
            </div>
            <form onSubmit={handleImportBPMN}>
              <div className="form-group">
                <label className="form-label">Specification ID</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. RiskApprovalWorkflow"
                  required
                  value={importDraft.spec_id}
                  onChange={(e) => setImportDraft({ ...importDraft, spec_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Friendly Process Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. Risk Audit Approval Flow"
                  required
                  value={importDraft.name}
                  onChange={(e) => setImportDraft({ ...importDraft, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="Import metadata description"
                  value={importDraft.description}
                  onChange={(e) => setImportDraft({ ...importDraft, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Tags (comma-separated)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="imported, workflow"
                  value={importDraft.tags}
                  onChange={(e) => setImportDraft({ ...importDraft, tags: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">BPMN 2.0 File (.bpmn, .xml)</label>
                <input 
                  type="file" 
                  className="form-control" 
                  accept=".bpmn,.xml"
                  required
                  onChange={(e) => setImportDraft({ ...importDraft, file: e.target.files[0] })}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowImportModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? <Loader className="spinner" size={14} /> : 'Import Spec'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
