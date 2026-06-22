/**
 * App — root component. Assembles sidebar + main chat area.
 *
 * Week 4 additions:
 * - RepoSwitcher: switch between previously indexed repos
 * - ExplainPanel: "Explain this file" modal
 * - File right-click → Explain action
 */
import { useState } from 'react'
import RepoInput from './components/RepoInput'
import RepoSwitcher from './components/RepoSwitcher'
import FileTree from './components/FileTree'
import ChatWindow from './components/ChatWindow'
import ExplainPanel from './components/ExplainPanel'

export default function App() {
  const [activeRepo, setActiveRepo] = useState(null)
  const [activeFile, setActiveFile] = useState(null)
  const [explainFile, setExplainFile] = useState(null) // {path} if explain modal open

  function handleRepoReady(repoInfo) {
    setActiveRepo(repoInfo)
    setActiveFile(null)
  }

  function handleRepoSwitch(repoInfo) {
    setActiveRepo(repoInfo)
    setActiveFile(null)
  }

  function handleFileClick(node) {
    setActiveFile(node.path)
  }

  function handleFileExplain(node) {
    setExplainFile(node.path)
  }

  function handleCitationClick(source) {
    setActiveFile(source.file_path)
  }

  return (
    <div className="app-shell">
      {/* ── Left Sidebar ── */}
      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-header">
          <div className="logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"/>
              <polyline points="2 17 12 22 22 17"/>
              <polyline points="2 12 12 17 22 12"/>
            </svg>
            CodeSage
          </div>
        </div>

        {/* Repo URL input */}
        <RepoInput onRepoReady={handleRepoReady} />

        {/* Previously indexed repos switcher */}
        <RepoSwitcher
          activeRepoId={activeRepo?.repo_id}
          onSwitch={handleRepoSwitch}
        />

        {/* File tree */}
        <FileTree
          repoId={activeRepo?.repo_id}
          onFileClick={handleFileClick}
          onFileExplain={handleFileExplain}
          activeFile={activeFile}
        />
      </aside>

      {/* ── Main Chat Area ── */}
      <main className="main-content">
        <ChatWindow
          repoId={activeRepo?.repo_id}
          repoName={activeRepo?.repo_name}
          onCitationClick={handleCitationClick}
        />
      </main>

      {/* ── Explain File Modal ── */}
      {explainFile && activeRepo && (
        <ExplainPanel
          repoId={activeRepo.repo_id}
          filePath={explainFile}
          onClose={() => setExplainFile(null)}
        />
      )}
    </div>
  )
}
