import React, { useState, useEffect } from 'react'
import { 
  LayoutDashboard, 
  GitBranch, 
  Activity, 
  User, 
  CheckCircle2, 
  AlertTriangle,
  X 
} from 'lucide-react'
import Dashboard from './components/Dashboard'
import Designer from './components/Designer'
import Monitoring from './components/Monitoring'

function App() {
  const [currentView, setCurrentView] = useState('dashboard')
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
  }

  // Auto-hide toast messages
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null)
      }, 4000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  const renderActiveView = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <Dashboard 
            onOpenDesigner={(id) => {
              setSelectedWorkflowId(id)
              setCurrentView('designer')
            }} 
            showToast={showToast}
          />
        )
      case 'designer':
        return (
          <Designer 
            workflowId={selectedWorkflowId} 
            onClose={() => {
              setSelectedWorkflowId(null)
              setCurrentView('dashboard')
            }} 
            showToast={showToast}
          />
        )
      case 'monitoring':
        return <Monitoring showToast={showToast} />
      default:
        return (
          <Dashboard 
            onOpenDesigner={(id) => {
              setSelectedWorkflowId(id)
              setCurrentView('designer')
            }} 
            showToast={showToast}
          />
        )
    }
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div>
          <div className="brand-section">
            <div className="brand-logo">
              <GitBranch size={20} color="#fff" />
            </div>
            <span className="brand-name">Studio</span>
          </div>

          <ul className="nav-links">
            <li 
              className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
              onClick={() => {
                setSelectedWorkflowId(null)
                setCurrentView('dashboard')
              }}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </li>
            <li 
              className={`nav-item ${currentView === 'designer' ? 'active' : ''}`}
              onClick={() => {
                if (selectedWorkflowId) {
                  setCurrentView('designer')
                } else {
                  showToast('Please select or create a workflow definition first.', 'error')
                }
              }}
            >
              <GitBranch size={18} />
              <span>Designer</span>
            </li>
            <li 
              className={`nav-item ${currentView === 'monitoring' ? 'active' : ''}`}
              onClick={() => {
                setSelectedWorkflowId(null)
                setCurrentView('monitoring')
              }}
            >
              <Activity size={18} />
              <span>Monitoring</span>
            </li>
          </ul>
        </div>

        <div className="user-tag">
          <User size={14} color="#8b949e" />
          <span>Administrator</span>
        </div>
      </div>

      {/* Main Workspace Pane */}
      <div className="main-content">
        <div className="top-bar">
          <span className="view-title">
            {currentView === 'dashboard' && 'Workflow Specifications'}
            {currentView === 'designer' && 'Workflow Designer Mode'}
            {currentView === 'monitoring' && 'Workflow Monitoring & Traces'}
          </span>
          <div className="user-tag" style={{ border: 'none', background: 'rgba(0,229,255,0.06)', color: 'var(--color-accent-secondary)' }}>
            <span>Engine Version: SpiffWorkflow 3.x</span>
          </div>
        </div>

        {renderActiveView()}
      </div>

      {/* Global Notifications Toast */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          <span>{toast.message}</span>
          <X size={14} style={{ cursor: 'pointer', marginLeft: '8px' }} onClick={() => setToast(null)} />
        </div>
      )}
    </div>
  )
}

export default App
