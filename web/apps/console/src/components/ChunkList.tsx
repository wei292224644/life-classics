import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChunkCard } from './ChunkCard'
import { ChunkEditDrawer } from './ChunkEditDrawer'
import { api } from '@/api/client'
import type { Chunk } from '@/api/types'
import { useToast } from '@/hooks/use-toast'

const SEMANTIC_TYPES = [
  'scope', 'definition', 'limit', 'procedure',
  'material', 'calculation', 'amendment', 'metadata', 'unknown',
]
const PAGE_SIZE = 20

function CopyId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleCopy = () => {
    navigator.clipboard.writeText(id)
    setCopied(true)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button
      onClick={handleCopy}
      className="font-mono text-xs text-muted-foreground hover:text-foreground transition-colors border border-border rounded px-1.5 py-0.5"
      title={id}
    >
      {copied ? '已复制' : id.slice(0, 8) + '…'}
    </button>
  )
}

interface Props {
  docId: string | null
}

type LoadResult =
  | { ok: true; chunks: Chunk[] }
  | { ok: false; error: unknown }

interface LoadParams {
  docId: string | null
  semanticFilter: string
  offset: number
}

export function ChunkList({ docId }: Props) {
  const [chunks, setChunks] = useState<Chunk[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [semanticFilter, setSemanticFilter] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const [editingChunk, setEditingChunk] = useState<Chunk | null>(null)
  const [reparsingIds, setReparsingIds] = useState<Set<string>>(new Set())
  const reparsingLockRef = useRef<Set<string>>(new Set())
  const currentParamsRef = useRef<LoadParams>({ docId, semanticFilter, offset })
  const loadRequestIdRef = useRef(0)
  const { toast } = useToast()

  const loadAndReturn = useCallback(async (params?: LoadParams): Promise<LoadResult> => {
    const { docId: currentDocId, semanticFilter: currentSemanticFilter, offset: currentOffset } = params ?? currentParamsRef.current
    const requestId = ++loadRequestIdRef.current

    if (!currentDocId) {
      if (requestId === loadRequestIdRef.current) {
        setChunks([])
        setTotal(0)
        setLoading(false)
      }
      return { ok: true, chunks: [] }
    }

    setLoading(true)
    try {
      const res = await api.chunks.list({
        doc_id: currentDocId,
        semantic_type: currentSemanticFilter === 'all' ? undefined : currentSemanticFilter,
        limit: PAGE_SIZE,
        offset: currentOffset,
      })
      if (requestId === loadRequestIdRef.current) {
        setChunks(res.chunks)
        setTotal(res.total)
      }
      return { ok: true, chunks: res.chunks }
    } catch (e) {
      console.error(e)
      return { ok: false, error: e }
    } finally {
      if (requestId === loadRequestIdRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => { setOffset(0) }, [docId, semanticFilter])
  useEffect(() => {
    const params = { docId, semanticFilter, offset }
    currentParamsRef.current = params
    void loadAndReturn(params)
  }, [docId, semanticFilter, offset, loadAndReturn])

  const handleReparse = useCallback(async (chunkId: string) => {
    if (reparsingLockRef.current.has(chunkId)) return

    reparsingLockRef.current.add(chunkId)

    setReparsingIds(prev => {
      const next = new Set(prev)
      next.add(chunkId)
      return next
    })

    try {
      await api.chunks.reparse(chunkId)
      const latest = await loadAndReturn()
      if (!latest.ok) {
        toast({ description: '重解析成功，但列表刷新失败，请手动刷新' })
      } else {
        const isVisible = latest.chunks.some(chunk => chunk.id === chunkId)
        if (!isVisible) {
          toast({ description: '重解析完成，该条在当前筛选条件下不可见' })
        } else {
          toast({ description: '重解析成功' })
        }
      }

      if (editingChunk?.id === chunkId) {
        toast({ description: '当前抽屉内容可能过期，请关闭后重新打开再编辑' })
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : ''
      const genericErrors = new Set([
        'Internal Server Error',
        'Bad Gateway',
        'Service Unavailable',
        'Gateway Timeout',
      ])
      const shouldFallback =
        !message
        || e instanceof TypeError
        || message.includes('Failed to fetch')
        || genericErrors.has(message)
        || /^HTTP\s+\d+$/.test(message)
      toast({ description: shouldFallback ? '重解析失败，请稍后重试' : message })
    } finally {
      setReparsingIds(prev => {
        const next = new Set(prev)
        next.delete(chunkId)
        return next
      })
      reparsingLockRef.current.delete(chunkId)
    }
  }, [loadAndReturn, toast, editingChunk])

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  if (!docId) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        请先选择左侧文档
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-card">
        <Select value={semanticFilter} onValueChange={setSemanticFilter}>
          <SelectTrigger className="w-44 h-8 text-sm bg-secondary border-border">
            <SelectValue placeholder="semantic_type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            {SEMANTIC_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
          </SelectContent>
        </Select>
        {semanticFilter !== 'all' && (
          <Button variant="ghost" size="sm" className="h-8 text-xs" onClick={() => setSemanticFilter('all')}>
            清除
          </Button>
        )}
        <span className="ml-auto text-xs text-muted-foreground">共 {total} 条</span>
        <CopyId id={docId} />
      </div>

      {/* Chunk list */}
      <ScrollArea className="flex-1 px-4 py-3">
        {loading ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}
          </div>
        ) : chunks.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
            该文档暂无 chunks，请先通过 parser_workflow 写入数据
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {chunks.map(chunk => (
              <ChunkCard
                key={chunk.id}
                chunk={chunk}
                isReparsing={reparsingIds.has(chunk.id)}
                onEdit={() => setEditingChunk(chunk)}
                onReparse={() => handleReparse(chunk.id)}
              />
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 py-2 border-t border-border">
          <Button
            variant="ghost" size="sm" className="h-7 w-7 p-0 text-xs"
            disabled={currentPage === 1}
            onClick={() => setOffset(offset - PAGE_SIZE)}
          >←</Button>
          {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
            const page = i + 1
            return (
              <Button
                key={page}
                variant={currentPage === page ? 'default' : 'ghost'}
                size="sm"
                className="h-7 w-7 p-0 text-xs"
                onClick={() => setOffset((page - 1) * PAGE_SIZE)}
              >{page}</Button>
            )
          })}
          <Button
            variant="ghost" size="sm" className="h-7 w-7 p-0 text-xs"
            disabled={currentPage === totalPages}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >→</Button>
        </div>
      )}

      {/* Edit drawer */}
      <ChunkEditDrawer
        chunk={editingChunk}
        open={editingChunk !== null}
        onClose={() => setEditingChunk(null)}
        onSaved={updated => {
          setChunks(prev => prev.map(c => c.id === updated.id ? updated : c))
        }}
      />
    </div>
  )
}
