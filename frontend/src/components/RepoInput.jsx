/**
 * RepoInput — sidebar panel for entering a GitHub repo URL and triggering indexing.
 * Shows live status: idle → indexing → ready (or error).
 * Supports private repos via optional GitHub personal access token.
 */
import { useState } from 'react'

const PLACEHOLDER = 'https://github.com/user/repo'

export default function RepoInput({ onRepoReady }) {
  const [url, setUrl] = useState('')
  const [token, setToken] = useState('')
  const [showToken, setShowToken] = useState(false)
  const [status, setStatus] = useState('idle') // idle | indexing | ready | error
  const [repoInfo, setRepoInfo] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  async function handleIndex() {
    if (!url.trim()) return
    setStatus('indexing')
    setErrorMsg('')

    try {
      const body = { repo_url: url.trim() }
      if (token.trim()) body.github_token = token.trim()

      const res = await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Indexing failed')
      }

      const data = await res.json()
      setRepoInfo(data)
      setStatus('ready')
      onRepoReady(data)
    } catch (e) {
      setStatus('error')
      setErrorMsg(e.message)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleIndex()
  }

  return (
    <div className="repo-panel">
      <label>GitHub Repository</label>

      <div className="input-row">
        <input
          id="repo-url-input"
          className="url-input"
          type="text"
          placeholder={PLACEHOLDER}
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={status === 'indexing'}
        />
        <button
          id="index-btn"
          className="btn btn-primary"
          onClick={handleIndex}
          disabled={!url.trim() || status === 'indexing'}
          title="Index repository"
        >
          {status === 'indexing' ? <span className="spinner" /> : '⚡'}
        </button>
      </div>

      {/* Private repo token toggle */}
      <div style={{ marginTop: 6 }}>
        <button
          id="toggle-token-btn"
          onClick={() => setShowToken(v => !v)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-dim)',
            fontSize: '0.75rem',
            cursor: 'pointer',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <span style={{ fontSize: '0.65rem' }}>{showToken ? '▲' : '▼'}</span>
          Private repo? Add token
        </button>

        {showToken && (
          <input
            id="github-token-input"
            className="url-input"
            type="password"
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
            value={token}
            onChange={e => setToken(e.target.value)}
            disabled={status === 'indexing'}
            style={{ marginTop: 6, fontSize: '0.85rem' }}
          />
        )}
      </div>

      {/* Status feedback */}
      {status === 'indexing' && (
        <div className="status-badge indexing" style={{ marginTop: 8 }}>
          <span className="spinner" style={{ width: 10, height: 10 }} />
          Cloning &amp; indexing…
        </div>
      )}

      {status === 'ready' && repoInfo && (
        <div className="status-badge ready" style={{ marginTop: 8 }}>
          ✓ {repoInfo.repo_name} — {repoInfo.files_indexed} files, {repoInfo.chunks_created} chunks
        </div>
      )}

      {status === 'error' && (
        <div className="status-badge error" style={{ marginTop: 8 }} title={errorMsg}>
          ✗ {errorMsg.slice(0, 60)}{errorMsg.length > 60 ? '…' : ''}
        </div>
      )}
    </div>
  )
}
