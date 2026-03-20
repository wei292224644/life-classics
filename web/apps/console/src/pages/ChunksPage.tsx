import { useState, useEffect } from 'react'
import { DocList } from '@/components/DocList'
import { ChunkList } from '@/components/ChunkList'
import { api } from '@/api/client'
import type { DocumentInfo } from '@/api/types'

export function ChunksPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)

  useEffect(() => {
    api.documents.list()
      .then(res => setDocuments(res.documents))
      .finally(() => setDocsLoading(false))
  }, [])

  return (
    <div className="flex flex-1 min-h-0">
      <aside className="w-60 shrink-0 flex flex-col min-h-0">
        <DocList
          documents={documents}
          loading={docsLoading}
          selectedDocId={selectedDocId}
          onSelect={setSelectedDocId}
        />
      </aside>
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <ChunkList docId={selectedDocId} />
      </main>
    </div>
  )
}
