import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  LayoutDashboard, FileText, BookOpen, CheckCircle2, AlertTriangle,
  Send, RefreshCw, ChevronRight, Plus, Shield, Sparkles
} from 'lucide-react'

const API = '/api'

function App() {
  const [view, setView] = useState('dashboard')
  const [workspaces, setWorkspaces] = useState([])
  const [currentWs, setCurrentWs] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [selectedDraft, setSelectedDraft] = useState(null)
  const [guidelines, setGuidelines] = useState([])
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [newDraft, setNewDraft] = useState({ title: '', content: '', channel: 'social' })
  const [newGuideline, setNewGuideline] = useState({ category: 'terminology', title: '', content: '', severity: 'medium', is_exact_match: false })

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const loadWorkspaces = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/workspaces`)
      setWorkspaces(data)
      if (data.length && !currentWs) {
        setCurrentWs(data[0])
      }
    } catch (e) {
      console.error(e)
      showToast('Could not reach backend. Is the API running?')
    }
  }, [currentWs])

  useEffect(() => { loadWorkspaces() }, [])

  useEffect(() => {
    if (currentWs) {
      loadDrafts()
      loadGuidelines()
    }
  }, [currentWs])

  const loadDrafts = async () => {
    if (!currentWs) return
    const { data } = await axios.get(`${API}/workspaces/${currentWs.id}/drafts`)
    setDrafts(data)
  }

  const loadGuidelines = async () => {
    if (!currentWs) return
    const { data } = await axios.get(`${API}/workspaces/${currentWs.id}/guidelines`)
    setGuidelines(data)
  }

  const createDraft = async () => {
    if (!newDraft.content.trim() || !currentWs) return
    setLoading(true)
    try {
      const { data } = await axios.post(`${API}/drafts`, {
        workspace_id: currentWs.id,
        title: newDraft.title || 'Untitled Draft',
        content: newDraft.content,
        channel: newDraft.channel
      })
      setSelectedDraft(data)
      setNewDraft({ title: '', content: '', channel: 'social' })
      setView('review')
      loadDrafts()
      showToast('Draft checked successfully')
    } catch (e) {
      showToast('Failed to create draft')
    } finally {
      setLoading(false)
    }
  }

  const refreshDraft = async (id) => {
    const { data } = await axios.get(`${API}/drafts/${id}`)
    setSelectedDraft(data)
  }

  const updateFinding = async (fid, status) => {
    await axios.patch(`${API}/findings/${fid}`, { status })
    if (selectedDraft) await refreshDraft(selectedDraft.id)
    showToast(`Finding marked as ${status}`)
  }

  const applySuggestions = async () => {
    if (!selectedDraft) return
    setLoading(true)
    try {
      await axios.post(`${API}/drafts/${selectedDraft.id}/apply-suggestions`)
      await refreshDraft(selectedDraft.id)
      showToast('Suggestions applied')
    } finally {
      setLoading(false)
    }
  }

  const recheck = async () => {
    if (!selectedDraft) return
    setLoading(true)
    try {
      const { data } = await axios.post(`${API}/drafts/${selectedDraft.id}/recheck`)
      setSelectedDraft(data)
      showToast('Recheck complete')
    } finally {
      setLoading(false)
    }
  }

  const submitReview = async () => {
    if (!selectedDraft) return
    const { data } = await axios.post(`${API}/drafts/${selectedDraft.id}/submit`)
    setSelectedDraft(data)
    loadDrafts()
    showToast('Submitted for human approval')
  }

  const approveAction = async (action, comment = '') => {
    if (!selectedDraft) return
    const { data } = await axios.post(`${API}/drafts/${selectedDraft.id}/approve`, { action, comment })
    setSelectedDraft(data)
    loadDrafts()
    showToast(action === 'approve' ? 'Content approved' : 'Changes requested')
  }

  const addGuideline = async () => {
    if (!newGuideline.title || !newGuideline.content || !currentWs) return
    await axios.post(`${API}/workspaces/${currentWs.id}/guidelines`, newGuideline)
    setNewGuideline({ category: 'terminology', title: '', content: '', severity: 'medium', is_exact_match: false })
    loadGuidelines()
    showToast('Guideline added')
  }

  const severityBadge = (s) => {
    const map = { critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }
    return <span className={`badge ${map[s] || 'badge-low'}`}>{s}</span>
  }

  const Dashboard = () => (
    <>
      <div className="page-header">
        <h1>Brand Governance Dashboard</h1>
        <p>Review drafts against approved guidelines before publication.</p>
      </div>
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value">{drafts.length}</div>
          <div className="stat-label">Total Drafts</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{drafts.filter(d => d.status === 'under_review').length}</div>
          <div className="stat-label">Under Review</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{drafts.filter(d => d.status === 'approved').length}</div>
          <div className="stat-label">Approved</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{guidelines.length}</div>
          <div className="stat-label">Active Guidelines</div>
        </div>
      </div>
      <div className="card">
        <h2><FileText size={18} /> Recent Drafts</h2>
        {drafts.length === 0 ? (
          <div className="empty-state">No drafts yet. Create your first draft to get started.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Channel</th>
                <th>Status</th>
                <th>Findings</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {drafts.slice(0, 8).map(d => (
                <tr key={d.id}>
                  <td>{d.title}</td>
                  <td style={{ textTransform: 'capitalize' }}>{d.channel}</td>
                  <td><span className={`status-pill status-${d.status}`}>{d.status.replace('_', ' ')}</span></td>
                  <td>{d.findings?.length || 0}</td>
                  <td>
                    <button className="btn btn-secondary" style={{ padding: '0.35rem 0.7rem', fontSize: '0.8rem' }}
                      onClick={() => { setSelectedDraft(d); setView('review') }}>
                      Open <ChevronRight size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )

  const NewDraftView = () => (
    <>
      <div className="page-header">
        <h1>Submit New Draft</h1>
        <p>Paste your marketing copy. Inkloom will check it against brand rules and approved sources.</p>
      </div>
      <div className="card">
        <div className="form-group">
          <label>Title</label>
          <input value={newDraft.title} onChange={e => setNewDraft({ ...newDraft, title: e.target.value })}
            placeholder="e.g. Q4 Social Campaign – Product Launch" />
        </div>
        <div className="form-group">
          <label>Channel / Content Type</label>
          <select value={newDraft.channel} onChange={e => setNewDraft({ ...newDraft, channel: e.target.value })}>
            <option value="social">Social Post</option>
            <option value="ad">Advertisement Copy</option>
            <option value="campaign">Campaign Document</option>
            <option value="email">Email / Newsletter</option>
          </select>
        </div>
        <div className="form-group">
          <label>Draft Content</label>
          <textarea
            value={newDraft.content}
            onChange={e => setNewDraft({ ...newDraft, content: e.target.value })}
            placeholder="Paste or type your draft here..."
            rows={10}
          />
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
          <button className="btn btn-primary" onClick={createDraft} disabled={loading || !newDraft.content.trim()}>
            {loading ? <span className="loader" /> : <Sparkles size={16} />}
            Run Brand Checks
          </button>
        </div>
      </div>
      <div className="card">
        <h2>Try a sample</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Click to load a sample that will trigger several checks (claims, terminology, tone).
        </p>
        <button className="btn btn-secondary" onClick={() => setNewDraft({
          title: 'Sample – Overclaiming Ad',
          channel: 'ad',
          content: `Discover the best product in the world! Our solution is 100% safe and guaranteed to transform your business overnight. Customers love how awesome and cool it is. Free forever – no catch! Join thousands who already switched to the #1 platform.`
        })}>
          Load Sample Draft
        </button>
      </div>
    </>
  )

  const ReviewView = () => {
    if (!selectedDraft) return <div className="empty-state">Select a draft to review</div>
    const openFindings = selectedDraft.findings?.filter(f => f.status === 'open') || []
    const resolved = selectedDraft.findings?.filter(f => f.status !== 'open') || []

    return (
      <>
        <div className="page-header">
          <h1>{selectedDraft.title}</h1>
          <p>
            Channel: <strong style={{ textTransform: 'capitalize' }}>{selectedDraft.channel}</strong>
            {' · '}
            Status: <span className={`status-pill status-${selectedDraft.status}`}>{selectedDraft.status.replace('_', ' ')}</span>
          </p>
        </div>

        <div className="grid-2">
          <div className="card">
            <h2>Draft Content</h2>
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65, fontSize: '0.95rem' }}>
              {selectedDraft.content}
            </div>
            <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button className="btn btn-secondary" onClick={recheck} disabled={loading}>
                <RefreshCw size={15} /> Recheck
              </button>
              {openFindings.some(f => f.suggested_text) && (
                <button className="btn btn-primary" onClick={applySuggestions} disabled={loading}>
                  Apply All Suggestions
                </button>
              )}
            </div>
          </div>

          <div className="card">
            <h2><AlertTriangle size={18} /> Findings ({selectedDraft.findings?.length || 0})</h2>
            {openFindings.length === 0 && resolved.length === 0 && (
              <div className="empty-state" style={{ padding: '1.5rem' }}>
                <CheckCircle2 size={32} style={{ color: 'var(--success)', marginBottom: '0.5rem' }} />
                <div>No issues found. Looking good!</div>
              </div>
            )}
            {openFindings.map(f => (
              <div key={f.id} className="finding">
                <div className="finding-header">
                  <div className="finding-title">{f.title}</div>
                  <div className="finding-meta">
                    {severityBadge(f.severity)}
                    <span className={`badge ${f.is_rule_based ? 'badge-rule' : 'badge-ai'}`}>
                      {f.is_rule_based ? 'Rule-based' : 'AI-assisted'}
                    </span>
                  </div>
                </div>
                <div className="finding-explanation">{f.explanation}</div>
                {f.original_text && (
                  <div style={{ fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                    <strong>Matched:</strong> “{f.original_text}”
                  </div>
                )}
                {f.suggested_text && (
                  <div className="suggestion-box">
                    <strong>Suggestion:</strong> {f.suggested_text}
                  </div>
                )}
                <div className="finding-actions" style={{ marginTop: '0.75rem' }}>
                  <button className="btn btn-success" style={{ padding: '0.35rem 0.7rem', fontSize: '0.8rem' }}
                    onClick={() => updateFinding(f.id, 'accepted')}>Accept</button>
                  <button className="btn btn-secondary" style={{ padding: '0.35rem 0.7rem', fontSize: '0.8rem' }}
                    onClick={() => updateFinding(f.id, 'rejected')}>Reject</button>
                </div>
              </div>
            ))}
            {resolved.length > 0 && (
              <div style={{ marginTop: '1rem', opacity: 0.7 }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                  Resolved ({resolved.length})
                </div>
                {resolved.map(f => (
                  <div key={f.id} className="finding" style={{ opacity: 0.75 }}>
                    <div className="finding-title" style={{ fontSize: '0.88rem' }}>{f.title}</div>
                    <span className="badge badge-status">{f.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h2><Shield size={18} /> Human Approval</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            AI findings are advisory. An authorised reviewer must approve before content is considered ready to publish.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {(selectedDraft.status === 'draft' || selectedDraft.status === 'changes_requested') && (
              <button className="btn btn-primary" onClick={submitReview}>
                <Send size={15} /> Submit for Review
              </button>
            )}
            {selectedDraft.status === 'under_review' && (
              <>
                <button className="btn btn-success" onClick={() => approveAction('approve')}>
                  <CheckCircle2 size={15} /> Approve
                </button>
                <button className="btn btn-danger" onClick={() => approveAction('request_changes', 'Please address remaining findings')}>
                  Request Changes
                </button>
              </>
            )}
            {selectedDraft.status === 'approved' && (
              <div style={{ color: 'var(--success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 size={18} /> This content has been approved for publication.
              </div>
            )}
          </div>
        </div>
      </>
    )
  }

  const GuidelinesView = () => (
    <>
      <div className="page-header">
        <h1>Brand Rule Library</h1>
        <p>Explicit guidelines, preferred terminology and restricted claims used by the checker.</p>
      </div>
      <div className="card">
        <h2><Plus size={18} /> Add Guideline</h2>
        <div className="grid-2">
          <div className="form-group">
            <label>Category</label>
            <select value={newGuideline.category} onChange={e => setNewGuideline({ ...newGuideline, category: e.target.value })}>
              <option value="terminology">Terminology</option>
              <option value="prohibited">Prohibited Phrase</option>
              <option value="claim">Claim Restriction</option>
              <option value="tone">Tone</option>
              <option value="preferred">Preferred Language</option>
            </select>
          </div>
          <div className="form-group">
            <label>Severity</label>
            <select value={newGuideline.severity} onChange={e => setNewGuideline({ ...newGuideline, severity: e.target.value })}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>Title</label>
          <input value={newGuideline.title} onChange={e => setNewGuideline({ ...newGuideline, title: e.target.value })}
            placeholder="Short descriptive title" />
        </div>
        <div className="form-group">
          <label>Content / Rule Text</label>
          <textarea value={newGuideline.content} onChange={e => setNewGuideline({ ...newGuideline, content: e.target.value })}
            placeholder="The rule text or exact phrase to match" rows={3} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', marginBottom: '1rem' }}>
          <input type="checkbox" checked={newGuideline.is_exact_match}
            onChange={e => setNewGuideline({ ...newGuideline, is_exact_match: e.target.checked })}
            style={{ width: 'auto' }} />
          Exact phrase match (deterministic rule)
        </label>
        <button className="btn btn-primary" onClick={addGuideline}>Add Guideline</button>
      </div>
      <div className="card">
        <h2><BookOpen size={18} /> Current Guidelines ({guidelines.length})</h2>
        {guidelines.length === 0 ? (
          <div className="empty-state">No guidelines yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Title</th>
                <th>Content</th>
                <th>Severity</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {guidelines.map(g => (
                <tr key={g.id}>
                  <td style={{ textTransform: 'capitalize' }}>{g.category}</td>
                  <td>{g.title}</td>
                  <td style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.content}</td>
                  <td>{severityBadge(g.severity)}</td>
                  <td>
                    <span className={`badge ${g.is_exact_match ? 'badge-rule' : 'badge-ai'}`}>
                      {g.is_exact_match ? 'Exact' : 'Guidance'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-mark">I</div>
          <div>
            <div className="logo-text">Inkloom AI</div>
            <div className="logo-sub">Brand Governance</div>
          </div>
        </div>
        <button className={`nav-item ${view === 'dashboard' ? 'active' : ''}`} onClick={() => setView('dashboard')}>
          <LayoutDashboard size={18} /> Dashboard
        </button>
        <button className={`nav-item ${view === 'new' ? 'active' : ''}`} onClick={() => setView('new')}>
          <Plus size={18} /> New Draft
        </button>
        <button className={`nav-item ${view === 'review' ? 'active' : ''}`} onClick={() => setView('review')}>
          <FileText size={18} /> Review Draft
        </button>
        <button className={`nav-item ${view === 'guidelines' ? 'active' : ''}`} onClick={() => setView('guidelines')}>
          <BookOpen size={18} /> Brand Rules
        </button>
        <div style={{ marginTop: 'auto', padding: '1rem 0.75rem', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>Active Workspace</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{currentWs?.name || 'Loading…'}</div>
        </div>
      </aside>
      <main className="main">
        {view === 'dashboard' && <Dashboard />}
        {view === 'new' && <NewDraftView />}
        {view === 'review' && <ReviewView />}
        {view === 'guidelines' && <GuidelinesView />}
      </main>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}

export default App
