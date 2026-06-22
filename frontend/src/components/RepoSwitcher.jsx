/**
 * RepoSwitcher — shows all indexed repos in the sidebar and lets the user
 * switch between them or delete them. Fetches from GET /api/repos.
 */
import { useState, useEffect } from 'react'

export default function RepoSwitcher({ activeRepoId, onSwitch }) {
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(false)

  async function fetchRepos() {
    setLoading(true)
    try {
      const res = await fetch('/api/repos')
      if (res.ok) {
        const data = await res.json()
        setRepos(data.repos || [])
      }
    } catch (_) {}
    setLoading(false)
  }

  useEffect(() => { fetchRepos() }, [activeRepoId])

  async function handleDelete(e, repo) {
    e.stopPropagation()
    if (!confirm(`Delete "${repo.repo_name}"? This removes all indexed data.`)) return
    await fetch(`/api/repos/${repo.repo_id}`, { method: 'DELETE' })
    fetchRepos()
    if (activeRepoId === repo.repo_id) onSwitch(null)
  }

  if (loading) return <p className="tree-empty">Loading repos…</p>
  if (repos.length === 0) return null

  return (
    <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: 6, marginBottom: 4 }}>
      <h3 style={{ padding: '4px 16px', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>
        Indexed Repos
      </h3>
      {repos.map(repo => (
        <div
          key={repo.repo_id}
          className={`tree-node ${activeRepoId === repo.repo_id ? 'active' : ''}`}
          onClick={() => onSwitch(repo)}
          title={repo.repo_url}
          style={{ justifyContent: 'space-between' }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, minWidth: 0 }}>
            <span className="tree-icon">🗄️</span>
            <span className="tree-name">{repo.repo_name}</span>
          </span>
          <button
            onClick={(e) => handleDelete(e, repo)}
            title="Delete repo"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-dim)', fontSize: 11, padding: '0 2px',
              opacity: 0.6, flexShrink: 0,
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
