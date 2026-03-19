import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Chunk } from '@/api/types'

interface Props {
  chunk: Chunk
  onEdit: () => void
}

export function ChunkCard({ chunk, onEdit }: Props) {
  const displaySectionPath = chunk.metadata.section_path.replace(/\|/g, '/')

  return (
    <div className="rounded-lg border border-border p-4 bg-card hover:border-border/80 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="text-xs">
            {chunk.metadata.semantic_type}
          </Badge>
          <span className="text-xs text-muted-foreground">{displaySectionPath}</span>
        </div>
        <Button size="sm" variant="secondary" className="h-7 text-xs shrink-0" onClick={onEdit}>
          编辑
        </Button>
      </div>
      <p className="text-sm text-foreground leading-relaxed line-clamp-4">{chunk.content}</p>
    </div>
  )
}
