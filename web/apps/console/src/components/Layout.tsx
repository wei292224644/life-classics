import { useEffect, useRef, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { TabNav } from './TabNav'
import { api } from '@/api/client'
import type { KBStats } from '@/api/types'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { buttonVariants } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

export interface LayoutContext {
  refreshStats: () => void
  clearChatRef: React.MutableRefObject<(() => void) | null>
}

export function Layout() {
  const [stats, setStats] = useState<KBStats | null>(null)
  const [clearOpen, setClearOpen] = useState(false)
  const [clearing, setClearing] = useState(false)
  const { toast } = useToast()
  const clearChatRef = useRef<(() => void) | null>(null)

  const refreshStats = () => {
    api.kb.stats().then(setStats).catch(() => {})
  }

  useEffect(() => { refreshStats() }, [])

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* Header */}
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
                    toast({ description: `已清空 ${result.deleted_documents} 个文档，${result.deleted_chunks} 个 chunks` })
                    refreshStats()
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

      {/* Tab Nav */}
      <TabNav onClearChat={() => clearChatRef.current?.()} />

      {/* Page Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <Outlet context={{ refreshStats, clearChatRef } satisfies LayoutContext} />
      </div>
    </div>
  )
}
