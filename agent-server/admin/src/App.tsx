// agent-server/admin/src/App.tsx
import { useEffect, useState } from 'react'
import { DocList } from './components/DocList'
import { ChunkList } from './components/ChunkList'
import { Toaster } from '@/components/ui/toaster'
import { api } from './api/client'
import type { DocumentInfo, KBStats } from './api/types'

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [stats, setStats] = useState<KBStats | null>(null)

  useEffect(() => {
    api.documents.list()
      .then(res => setDocuments(res.documents))
      .finally(() => setDocsLoading(false))
    api.kb.stats().then(setStats).catch(() => {})
  }, [])

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0">
        <span className="font-bold text-sm tracking-wide">⚡ KB Admin</span>
        {stats && (
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span>chunks <strong className="text-foreground">{stats.total_chunks}</strong></span>
            <span>docs <strong className="text-foreground">{stats.total_documents}</strong></span>
          </div>
        )}
      </header>

      {/* Main layout */}
      <div className="flex flex-1 min-h-0">
        {/* Left panel */}
        <aside className="w-60 shrink-0 flex flex-col min-h-0">
          <DocList
            documents={documents}
            loading={docsLoading}
            selectedDocId={selectedDocId}
            onSelect={setSelectedDocId}
          />
        </aside>

        {/* Right panel */}
        <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <ChunkList docId={selectedDocId} />
        </main>
      </div>

      <Toaster />
    </div>
  )
}
