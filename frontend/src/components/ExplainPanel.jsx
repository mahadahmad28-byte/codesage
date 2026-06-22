/**
 * ExplainPanel — shows an AI explanation of a selected file, streamed in real-time.
 * Triggered when the user right-clicks a file in the tree or clicks "Explain".
 */
import { useState } from 'react'
import { marked } from 'marked'
import hljs from 'highlight.js'

marked.setOptions({
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

export default function ExplainPanel({ repoId, filePath, onClose }) {
  const [content, setContent] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [started, setStarted] = useState(false)

  async function startExplain() {
    if (streaming) return
    setContent('')
    setStreaming(true)
    setStarted(true)

    try {
      const res = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_id: repoId, file_path: filePath }),
      })

      if (!res.ok) throw new Error('Explain request failed')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data && data !== '[DONE]') {
              setContent(prev => prev + data)
            }
          }
        }
      }
    } catch (e) {
      setContent(`❌ Error: ${e.message}`)
    } finally {
      setStreaming(false)
    }
  }

  // Auto-start when panel opens
  if (!started && repoId && filePath) {
    startExplain()
  }

  const fileName = filePath?.split(/[/\\]/).pop() || ''
  const html = content ? marked.parse(content) : ''

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(4px)',
    }}>
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-xl)',
        width: '700px', maxWidth: '95vw',
        maxHeight: '80vh',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px', borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 18 }}>🔍</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>Explain File</div>
              <div style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-light)' }}>
                {filePath}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {!streaming && started && (
              <button className="btn btn-ghost" onClick={startExplain} style={{ fontSize: 11 }}>
                ↺ Re-explain
              </button>
            )}
            <button className="btn btn-ghost" onClick={onClose} style={{ fontSize: 11 }}>
              ✕ Close
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {streaming && !content && (
            <div className="thinking-dots" style={{ justifyContent: 'center', padding: 40 }}>
              <span /><span /><span />
            </div>
          )}
          {content && (
            <div
              className="message-content"
              style={{ background: 'transparent', border: 'none', padding: 0 }}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          )}
          {streaming && content && (
            <span className="streaming-cursor" style={{ marginLeft: 2 }} />
          )}
        </div>
      </div>
    </div>
  )
}
