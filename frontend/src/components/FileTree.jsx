/**
 * FileTree — collapsible repository file tree in the sidebar.
 * Fetches the file tree from the API after a repo is indexed.
 */
import { useState, useEffect } from 'react'

// Map file extensions to emoji icons
const FILE_ICONS = {
  py: '🐍', js: '📜', jsx: '⚛️', ts: '📘', tsx: '⚛️',
  json: '📋', md: '📝', css: '🎨', html: '🌐', sh: '⚙️',
  go: '🐹', rs: '🦀', java: '☕', kt: '💜', dart: '🎯',
  yaml: '⚙️', yml: '⚙️', toml: '⚙️', sql: '🗃️',
  txt: '📄', dockerfile: '🐳', default: '📄',
}

function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  if (name.toLowerCase() === 'dockerfile') return FILE_ICONS.dockerfile
  return FILE_ICONS[ext] || FILE_ICONS.default
}

function TreeNode({ node, depth = 0, onFileClick, onFileExplain, activeFile }) {
  const [open, setOpen] = useState(depth < 1) // Expand first level by default

  if (node.is_directory) {
    return (
      <div>
        <div
          className={`tree-node dir`}
          style={{ paddingLeft: `${8 + depth * 14}px` }}
          onClick={() => setOpen(o => !o)}
          title={node.path}
        >
          <span className="tree-icon">{open ? '📂' : '📁'}</span>
          <span className="tree-name">{node.name}</span>
        </div>
        {open && node.children?.map(child => (
          <TreeNode
            key={child.path}
            node={child}
            depth={depth + 1}
            onFileClick={onFileClick}
            onFileExplain={onFileExplain}
            activeFile={activeFile}
          />
        ))}
      </div>
    )
  }

  return (
    <div
      className={`tree-node ${activeFile === node.path ? 'active' : ''}`}
      style={{ paddingLeft: `${8 + depth * 14}px`, justifyContent: 'space-between' }}
      onClick={() => onFileClick?.(node)}
      onDoubleClick={() => onFileExplain?.(node)}
      title={`${node.path}\n(Double-click to explain)`}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 5, minWidth: 0 }}>
        <span className="tree-icon">{getFileIcon(node.name)}</span>
        <span className="tree-name">{node.name}</span>
      </span>
      <button
        onClick={(e) => { e.stopPropagation(); onFileExplain?.(node) }}
        title="Explain this file with AI"
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          fontSize: 11, opacity: 0, padding: '0 2px', color: 'var(--accent-light)',
          transition: 'opacity 0.15s',
        }}
        className="explain-btn"
      >
        🔍
      </button>
    </div>
  )
}

export default function FileTree({ repoId, onFileClick, onFileExplain, activeFile }) {
  const [tree, setTree] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!repoId) return
    setLoading(true)
    fetch(`/api/repos/${repoId}/tree`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { setTree(data?.tree ?? null); setLoading(false) })
      .catch(() => setLoading(false))
  }, [repoId])

  return (
    <div className="filetree-section">
      <h3>File Explorer</h3>
      {loading && <p className="tree-empty">Loading tree…</p>}
      {!loading && !tree && <p className="tree-empty">Index a repo to browse files</p>}
      {tree && (
        <TreeNode
          node={tree}
          depth={0}
          onFileClick={onFileClick}
          onFileExplain={onFileExplain}
          activeFile={activeFile}
        />
      )}
    </div>
  )
}
