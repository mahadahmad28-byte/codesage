/**
 * CitationChips — displays source file references returned by the RAG engine.
 * Clicking a chip inserts the file path into chat or highlights it in the tree.
 */

export default function CitationChips({ sources, onCitationClick }) {
  if (!sources || sources.length === 0) return null

  // Deduplicate by file_path
  const unique = sources.reduce((acc, src) => {
    if (!acc.find(s => s.file_path === src.file_path)) acc.push(src)
    return acc
  }, [])

  return (
    <div className="citations" role="list" aria-label="Source references">
      {unique.map((src, i) => {
        const fileName = src.file_path.split(/[/\\]/).pop()
        const relevancePct = Math.round((src.relevance_score ?? 0) * 100)
        const lineRange = src.start_line
          ? ` L${src.start_line}–${src.end_line}`
          : ''

        return (
          <button
            key={i}
            className="citation-chip"
            title={`${src.file_path}${lineRange}\nRelevance: ${relevancePct}%`}
            onClick={() => onCitationClick?.(src)}
            aria-label={`Source: ${src.file_path}`}
          >
            📎 {fileName}{lineRange}
            <span className="cite-score">{relevancePct}%</span>
          </button>
        )
      })}
    </div>
  )
}
