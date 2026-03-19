// agent-server/admin/src/App.tsx
import { useEffect, useState } from 'react'
import { DocList } from './components/DocList'
import { ChunkList } from './components/ChunkList'
import { Toaster } from '@/components/ui/toaster'
import { api } from './api/client'
import type { DocumentInfo, KBStats } from './api/types'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { buttonVariants } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

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

  const [clearOpen, setClearOpen] = useState(false)
  const [clearing, setClearing] = useState(false)
  const { toast } = useToast()

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
        <AlertDialog open={clearOpen} onOpenChange={setClearOpen}>
          <AlertDialogTrigger asChild>
            <button
              className={buttonVariants({ variant: 'destructive' })}
              style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
            >
              清空
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>清空知识库</AlertDialogTitle>
              <AlertDialogDescription>
                此操作将删除所有文档和 Chunks，且不可恢复。是否继续？
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setClearOpen(false)}>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  setClearing(true)
                  try {
                    const result = await api.documents.clearAll()
                    toast({
                      description: `已清空 ${result.deleted_documents} 个文档，${result.deleted_chunks} 个 chunks`,
                    })
                    setDocuments([])
                    setSelectedDocId(null)
                    setDocsLoading(false)
                    api.kb.stats().then(setStats).catch(() => {})
                  } catch (err) {
                    toast({ description: `清空失败: ${(err as Error).message}`, variant: 'destructive' })
                  } finally {
                    setClearing(false)
                    setClearOpen(false)
                  }
                }}
                disabled={clearing}
              >
                {clearing ? '清空中...' : '确认清空'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
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
