import { useState, useEffect, useCallback } from 'react'
import { DocList } from '@/components/DocList'
import { ChunkList } from '@/components/ChunkList'
import { api } from '@/api/client'
import type { DocumentInfo } from '@/api/types'
import { useToast } from '@/hooks/use-toast'

export function ChunksPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null)
  const { toast } = useToast()

  const refreshDocuments = useCallback(async () => {
    const res = await api.documents.list()
    setDocuments(res.documents)
  }, [])

  useEffect(() => {
    api.documents.list()
      .then(res => setDocuments(res.documents))
      .finally(() => setDocsLoading(false))
  }, [])

  const handleDeleteDoc = async (docId: string) => {
    setDeletingDocId(docId)
    try {
      const result = await api.documents.delete(docId)
      if (selectedDocId === docId) setSelectedDocId(null)
      await refreshDocuments()
      if (result.errors.length > 0) {
        toast({ title: '部分删除失败', description: result.errors.join('; '), variant: 'destructive' })
      } else {
        toast({ title: '已删除' })
      }
    } catch (e) {
      toast({ title: '删除失败', description: (e as Error).message, variant: 'destructive' })
    } finally {
      setDeletingDocId(null)
    }
  }

  return (
    <div className="flex flex-1 min-h-0">
      <aside className="w-60 shrink-0 flex flex-col min-h-0">
        <DocList
          documents={documents}
          loading={docsLoading}
          selectedDocId={selectedDocId}
          onSelect={setSelectedDocId}
          onDelete={handleDeleteDoc}
          deletingDocId={deletingDocId}
        />
      </aside>
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <ChunkList docId={selectedDocId} />
      </main>
    </div>
  )
}
