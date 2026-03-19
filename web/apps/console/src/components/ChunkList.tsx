import { useEffect, useState, useCallback } from 'react'
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

const SEMANTIC_TYPES = [
  'scope', 'definition', 'limit', 'procedure',
  'material', 'calculation', 'amendment', 'metadata', 'unknown',
]
const PAGE_SIZE = 20

interface Props {
  docId: string | null
}

export function ChunkList({ docId }: Props) {
  const [chunks, setChunks] = useState<Chunk[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [semanticFilter, setSemanticFilter] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const [editingChunk, setEditingChunk] = useState<Chunk | null>(null)

  const load = useCallback(async () => {
    if (!docId) { setChunks([]); setTotal(0); return }
    setLoading(true)
    try {
      const res = await api.chunks.list({
        doc_id: docId,
        semantic_type: semanticFilter === 'all' ? undefined : semanticFilter,
        limit: PAGE_SIZE,
        offset,
      })
      setChunks(res.chunks)
      setTotal(res.total)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [docId, semanticFilter, offset])

  useEffect(() => { setOffset(0) }, [docId, semanticFilter])
  useEffect(() => { load() }, [load])

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
                onEdit={() => setEditingChunk(chunk)}
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
