import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/api/client'
import type { Chunk } from '@/api/types'

const SEMANTIC_TYPES = [
  'scope', 'definition', 'limit', 'procedure',
  'material', 'calculation', 'amendment', 'metadata', 'unknown',
]

interface Props {
  chunk: Chunk
  isEditing: boolean
  onEditStart: () => void
  onEditEnd: () => void
  onSaved: (updated: Chunk) => void
}

export function ChunkCard({ chunk, isEditing, onEditStart, onEditEnd, onSaved }: Props) {
  const { toast } = useToast()
  const [content, setContent] = useState(chunk.content)
  const [semanticType, setSemanticType] = useState(chunk.metadata.semantic_type)
  const [sectionPath, setSectionPath] = useState(
    chunk.metadata.section_path.replace(/\|/g, '/'),
  )
  const [saving, setSaving] = useState(false)

  const displaySectionPath = chunk.metadata.section_path.replace(/\|/g, '/')

  async function handleSave() {
    setSaving(true)
    try {
      const updated = await api.chunks.update(chunk.id, {
        content,
        semantic_type: semanticType,
        section_path: sectionPath,
      })
      toast({ title: '已保存并重新嵌入', description: chunk.id })
      onSaved(updated)
      onEditEnd()
    } catch (e: any) {
      toast({ title: '保存失败', description: e.message, variant: 'destructive' })
    } finally {
      setSaving(false)
    }
  }

  function handleCancel() {
    setContent(chunk.content)
    setSemanticType(chunk.metadata.semantic_type)
    setSectionPath(chunk.metadata.section_path.replace(/\|/g, '/'))
    onEditEnd()
  }

  return (
    <div
      className={`rounded-lg border p-4 transition-all ${
        isEditing ? 'border-accent shadow-[0_0_0_2px_rgba(52,211,153,0.15)]' : 'border-border'
      } bg-card`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge
            variant="outline"
            className={`text-xs ${isEditing ? 'border-accent text-accent' : ''}`}
          >
            {isEditing ? '✏️ 编辑中' : semanticType}
          </Badge>
          {!isEditing && (
            <span className="text-xs text-muted-foreground">{displaySectionPath}</span>
          )}
        </div>
        {!isEditing ? (
          <Button size="sm" variant="secondary" className="h-7 text-xs" onClick={onEditStart}>
            编辑
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button
              size="sm"
              className="h-7 text-xs bg-accent hover:bg-accent/90"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? '保存中...' : '保存'}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="h-7 text-xs"
              onClick={handleCancel}
              disabled={saving}
            >
              取消
            </Button>
          </div>
        )}
      </div>

      {/* Content */}
      {!isEditing ? (
        <p className="text-sm text-foreground leading-relaxed line-clamp-4">{chunk.content}</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">content</p>
            <Textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              className="text-sm min-h-[100px] bg-secondary border-border"
              disabled={saving}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                semantic_type
              </p>
              <Select value={semanticType} onValueChange={setSemanticType} disabled={saving}>
                <SelectTrigger className="h-8 text-sm bg-secondary border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SEMANTIC_TYPES.map(t => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                section_path
              </p>
              <Input
                value={sectionPath}
                onChange={e => setSectionPath(e.target.value)}
                placeholder="如 3/3.1"
                className="h-8 text-sm bg-secondary border-border"
                disabled={saving}
              />
            </div>
          </div>
          <p className="text-xs text-amber-400/80 bg-amber-400/10 rounded px-2 py-1">
            ⚡ 保存后将自动重新生成向量嵌入
          </p>
        </div>
      )}
    </div>
  )
}
