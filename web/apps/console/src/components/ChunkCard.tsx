import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Chunk } from '@/api/types'

interface Props {
  chunk: Chunk
  isReparsing?: boolean
  onEdit: () => void
  onReparse?: () => void
}

export function ChunkCard({ chunk, isReparsing, onEdit, onReparse }: Props) {
  const reparsing = Boolean(isReparsing)
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
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            onClick={() => onReparse?.()}
            disabled={reparsing || !onReparse}
          >
            {reparsing ? '重解析中...' : '重解析'}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            className="h-7 text-xs"
            onClick={onEdit}
            disabled={reparsing}
          >
            编辑
          </Button>
        </div>
      </div>
      <p className="text-sm text-foreground leading-relaxed line-clamp-4">{chunk.content}</p>
    </div>
  )
}
