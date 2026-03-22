import { useState, useMemo } from 'react'
import { Trash2, Loader2, Pencil, ChevronLeft, ChevronRight } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import type { DocumentInfo } from '@/api/types'

const PAGE_SIZE = 20

interface Props {
  documents: DocumentInfo[]
  loading: boolean
  selectedDocId: string | null
  onSelect: (docId: string) => void
  onDelete: (docId: string) => Promise<void>
  onEdit: (doc: DocumentInfo) => void
  deletingDocId: string | null
}

export function DocList({ documents, loading, selectedDocId, onSelect, onDelete, onEdit, deletingDocId }: Props) {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)

  const filtered = useMemo(() => {
    if (!query.trim()) return documents
    const q = query.toLowerCase()
    return documents.filter(
      d =>
        d.standard_no.toLowerCase().includes(q) ||
        d.doc_type.toLowerCase().includes(q) ||
        d.doc_id.toLowerCase().includes(q) ||
        (d.title || '').toLowerCase().includes(q),
    )
  }, [documents, query])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  function handleQueryChange(value: string) {
    setQuery(value)
    setPage(1)
  }

  return (
    <div className="flex flex-col h-full border-r border-border">
      <div className="p-3 border-b border-border">
        <Input
          placeholder="搜索文档..."
          value={query}
          onChange={e => handleQueryChange(e.target.value)}
          className="h-8 text-sm bg-secondary"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-3 flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground text-center">
            {documents.length === 0 ? '暂无文档' : '无匹配结果'}
          </p>
        ) : (
          <div className="p-2 flex flex-col gap-1">
            {paged.map(doc => {
              const isDeleting = deletingDocId === doc.doc_id
              return (
                <DocItem
                  key={doc.doc_id}
                  doc={doc}
                  selected={selectedDocId === doc.doc_id}
                  isDeleting={isDeleting}
                  onSelect={onSelect}
                  onDelete={onDelete}
                  onEdit={onEdit}
                />
              )
            })}
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="border-t border-border px-3 py-3 flex items-center justify-between text-xs text-muted-foreground">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-2 rounded hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="上一页"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span>第 {currentPage} / {totalPages} 页</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-2 rounded hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="下一页"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  )
}

interface DocItemProps {
  doc: DocumentInfo
  selected: boolean
  isDeleting: boolean
  onSelect: (docId: string) => void
  onDelete: (docId: string) => Promise<void>
  onEdit: (doc: DocumentInfo) => void
}

function DocItem({ doc, selected, isDeleting, onSelect, onDelete, onEdit }: DocItemProps) {
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [hovered, setHovered] = useState(false)

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      await onDelete(doc.doc_id)
    } finally {
      setConfirming(false)
      setOpen(false)
    }
  }

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        onClick={() => onSelect(doc.doc_id)}
        className={`w-full text-left px-3 py-2 rounded-md transition-colors text-sm pr-14 ${
          selected
            ? 'bg-accent/20 border-l-2 border-accent'
            : 'hover:bg-secondary'
        }`}
      >
        <div className="font-medium text-foreground break-words leading-snug">
          {doc.title || doc.doc_id}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="text-xs text-muted-foreground truncate">{doc.doc_type}</span>
          <Badge variant="secondary" className="text-xs px-1 py-0 h-4">
            {doc.chunks_count}
          </Badge>
        </div>
      </button>

      {/* 编辑按钮 */}
      <button
        onClick={e => { e.stopPropagation(); onEdit(doc) }}
        className={`absolute right-7 top-1/2 -translate-y-1/2 p-1 rounded transition-opacity hover:bg-secondary ${hovered ? 'opacity-100' : 'opacity-0'}`}
        aria-label="编辑文档"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>

      {/* 删除按钮 */}
      <button
        onClick={e => { e.stopPropagation(); setOpen(true) }}
        disabled={isDeleting}
        className={`absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded transition-opacity hover:bg-destructive/10 hover:text-destructive disabled:opacity-50 ${hovered || isDeleting ? 'opacity-100' : 'opacity-0'}`}
        aria-label="删除文档"
      >
        {isDeleting
          ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
          : <Trash2 className="h-3.5 w-3.5" />
        }
      </button>

      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确认删除「{doc.title || doc.doc_id}」？此操作将删除该文档所有 chunks，无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={confirming}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={e => { e.preventDefault(); handleConfirm() }}
              disabled={confirming}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {confirming ? <Loader2 className="h-4 w-4 animate-spin" /> : '删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
