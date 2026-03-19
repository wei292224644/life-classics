// admin/src/components/DocList.tsx
import { useState, useMemo } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import type { DocumentInfo } from '@/api/types'

interface Props {
  documents: DocumentInfo[]
  loading: boolean
  selectedDocId: string | null
  onSelect: (docId: string) => void
}

export function DocList({ documents, loading, selectedDocId, onSelect }: Props) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    if (!query.trim()) return documents
    const q = query.toLowerCase()
    return documents.filter(
      d =>
        d.standard_no.toLowerCase().includes(q) ||
        d.doc_type.toLowerCase().includes(q) ||
        d.doc_id.toLowerCase().includes(q),
    )
  }, [documents, query])

  return (
    <div className="flex flex-col h-full border-r border-border">
      <div className="p-3 border-b border-border">
        <Input
          placeholder="搜索文档..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="h-8 text-sm bg-secondary"
        />
      </div>
      <ScrollArea className="flex-1">
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
            {filtered.map(doc => (
              <button
                key={doc.doc_id}
                onClick={() => onSelect(doc.doc_id)}
                className={`w-full text-left px-3 py-2 rounded-md transition-colors text-sm ${
                  selectedDocId === doc.doc_id
                    ? 'bg-accent/20 border-l-2 border-accent'
                    : 'hover:bg-secondary'
                }`}
              >
                <div className="font-medium text-foreground truncate">
                  {doc.standard_no || doc.doc_id}
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-xs text-muted-foreground truncate">{doc.doc_type}</span>
                  <Badge variant="secondary" className="text-xs px-1 py-0 h-4">
                    {doc.chunks_count}
                  </Badge>
                </div>
              </button>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
