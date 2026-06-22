/**
 * ChatWindow — the main conversation panel.
 *
 * Features:
 * - Sends questions to /api/chat/stream via Server-Sent Events
 * - Streams tokens in real time (typing effect)
 * - Renders markdown (via marked) with syntax highlighting (via highlight.js)
 * - Shows source citation chips per assistant message
 * - Maintains full conversation history for follow-up questions
 * - Suggestion chips when no messages yet
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import CitationChips from './CitationChips'

// Configure marked to use highlight.js
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

const SUGGESTIONS = [
  'How does authentication work?',
  'What does the main entry point do?',
  'Explain the database models',
  'Where are API routes defined?',
  'What testing strategy is used?',
]

function ThinkingIndicator() {
  return (
    <div className="message assistant">
      <div className="message-avatar">🧠</div>
      <div className="message-body">
        <div className="message-content">
          <div className="thinking-dots">
            <span /><span /><span />
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ msg, onCitationClick }) {
  const html = msg.role === 'assistant'
    ? marked.parse(msg.content || '')
    : null

  return (
    <div className={`message ${msg.role}`}>
      <div className="message-avatar">
        {msg.role === 'user' ? '👤' : '🧠'}
      </div>
      <div className="message-body">
        <div className={`message-content ${msg.streaming ? 'streaming-cursor' : ''}`}>
          {msg.role === 'user'
            ? <p>{msg.content}</p>
            : <div dangerouslySetInnerHTML={{ __html: html }} />
          }
        </div>

        {/* Source citations */}
        {msg.role === 'assistant' && msg.sources?.length > 0 && !msg.streaming && (
          <CitationChips sources={msg.sources} onCitationClick={onCitationClick} />
        )}
      </div>
    </div>
  )
}

export default function ChatWindow({ repoId, repoName, onCitationClick }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const esRef = useRef(null)  // EventSource ref for cleanup

  // Auto-scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  function handleInputChange(e) {
    setInput(e.target.value)
    const ta = textareaRef.current
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'
  }

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isStreaming || !repoId) return

    const question = input.trim()
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    // Add user message
    const userMsg = { role: 'user', content: question, id: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setIsStreaming(true)

    // Placeholder assistant message that will be filled in via streaming
    const assistantId = Date.now() + 1
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: '', sources: [], streaming: true, id: assistantId },
    ])

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_id: repoId,
          question,
          chat_history: messages.map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (!res.ok) throw new Error('Stream request failed')

      // Read SSE via ReadableStream (works with Vite proxy)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('event: sources')) continue

          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (!data || data === '') continue

            try {
              // Try to parse as JSON array (sources event)
              const parsed = JSON.parse(data)
              if (Array.isArray(parsed)) {
                setMessages(prev => prev.map(m =>
                  m.id === assistantId ? { ...m, sources: parsed } : m
                ))
              }
            } catch {
              // Plain text token
              if (data !== '[DONE]') {
                setMessages(prev => prev.map(m =>
                  m.id === assistantId
                    ? { ...m, content: m.content + data }
                    : m
                ))
              }
            }
          }
        }
      }
    } catch (e) {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: `❌ Error: ${e.message}`, streaming: false }
          : m
      ))
    } finally {
      // Mark streaming as done
      setMessages(prev => prev.map(m =>
        m.id === assistantId ? { ...m, streaming: false } : m
      ))
      setIsStreaming(false)
    }
  }, [input, isStreaming, repoId, messages])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function useSuggestion(text) {
    setInput(text)
    textareaRef.current?.focus()
  }

  const canSend = !!repoId && !!input.trim() && !isStreaming

  return (
    <div className="chat-window">
      {/* Message list */}
      <div className="messages-list" id="messages-list">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🧠</div>
            <h2>CodeSage</h2>
            <p>
              {repoId
                ? `Repo indexed! Ask anything about ${repoName || 'the codebase'}.`
                : 'Index a GitHub repository on the left, then start asking questions.'}
            </p>
            {repoId && (
              <div className="suggestions">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    className="suggestion-chip"
                    onClick={() => useSuggestion(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            onCitationClick={onCitationClick}
          />
        ))}

        {/* Show thinking dots while waiting for first token */}
        {isStreaming && messages[messages.length - 1]?.content === '' && (
          <ThinkingIndicator />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Chat input */}
      <div className="chat-input-area">
        <div className="input-wrapper">
          <textarea
            id="chat-input"
            ref={textareaRef}
            className="chat-textarea"
            placeholder={
              repoId
                ? 'Ask anything about the codebase… (Enter to send, Shift+Enter for newline)'
                : 'Index a repository first…'
            }
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={!repoId || isStreaming}
            rows={1}
          />
          <button
            id="send-btn"
            className="send-btn"
            onClick={sendMessage}
            disabled={!canSend}
            title="Send message (Enter)"
            aria-label="Send message"
          >
            {isStreaming
              ? <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            }
          </button>
        </div>
        <p className="input-hint">
          {repoId ? 'Enter ↵ to send · Shift+Enter for new line' : 'Waiting for repo…'}
        </p>
      </div>
    </div>
  )
}
