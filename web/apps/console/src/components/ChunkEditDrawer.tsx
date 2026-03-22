import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter,
} from '@/components/ui/sheet'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/api/client'
import type { Chunk } from '@/api/types'

const SEMANTIC_TYPES = [
  'scope', 'definition', 'limit', 'procedure',
  'material', 'calculation', 'amendment', 'metadata', 'unknown',
]

interface Props {
  chunk: Chunk | null
  open: boolean
  onClose: () => void
  onSaved: (updated: Chunk) => void
}

export function ChunkEditDrawer({ chunk, open, onClose, onSaved }: Props) {
  const { toast } = useToast()
  const [content, setContent] = useState('')
  const [semanticType, setSemanticType] = useState('')
  const [sectionPath, setSectionPath] = useState('')
  const [saving, setSaving] = useState(false)

  // sync form state when chunk changes
  useEffect(() => {
    if (chunk) {
      setContent(chunk.content)
      setSemanticType(chunk.metadata.semantic_type)
      setSectionPath(chunk.metadata.section_path.replace(/\|/g, '/'))
    }
  }, [chunk])

  async function handleSave() {
    if (!chunk) return
    setSaving(true)
    try {
      const updated = await api.chunks.update(chunk.id, {
        content,
        semantic_type: semanticType,
        section_path: sectionPath,
      })
      toast({ title: '已保存并重新嵌入', description: chunk.id })
      onSaved(updated)
      onClose()
    } catch (e: any) {
      toast({ title: '保存失败', description: e.message, variant: 'destructive' })
    } finally {
      setSaving(false)
    }
  }

  function handleCancel() {
    if (!saving) onClose()
  }

  return (
    <Sheet open={open} onOpenChange={v => { if (!v) handleCancel() }}>
      <SheetContent side="right" className="w-[520px] flex flex-col">
        <SheetHeader>
          <SheetTitle>编辑 Chunk</SheetTitle>
          <SheetDescription className="font-mono break-all">
            {chunk?.id}
          </SheetDescription>
        </SheetHeader>

        {/* Form body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-5">
          {/* Content */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              content
            </label>
            <Textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              className="text-sm min-h-[200px] bg-secondary border-border resize-none"
              disabled={saving}
            />
          </div>

          {/* semantic_type */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              semantic_type
            </label>
            <Select value={semanticType} onValueChange={setSemanticType} disabled={saving}>
              <SelectTrigger className="h-9 text-sm bg-secondary border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SEMANTIC_TYPES.map(t => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* section_path */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              section_path
            </label>
            <Input
              value={sectionPath}
              onChange={e => setSectionPath(e.target.value)}
              placeholder="如 3/3.1"
              className="h-9 text-sm bg-secondary border-border"
              disabled={saving}
            />
          </div>

          {/* hint */}
          <p className="text-xs text-amber-400/80 bg-amber-400/10 rounded px-3 py-2">
            ⚡ 保存后将自动重新生成向量嵌入
          </p>

          {/* raw content (read-only) */}
          {chunk?.metadata.raw_content && chunk.metadata.raw_content !== chunk.content && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-muted-foreground uppercase tracking-wide">
                raw_content（原始，只读）
              </label>
              <p className="text-xs text-muted-foreground bg-muted rounded px-3 py-2 leading-relaxed whitespace-pre-wrap">
                {chunk.metadata.raw_content}
              </p>
            </div>
          )}

          {/* doc metadata (read-only) */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              文档元数据（只读）
            </label>
            <div className="text-xs text-muted-foreground bg-muted rounded px-3 py-2 flex flex-col gap-1">
              <div><span className="opacity-60">doc_id: </span>{chunk?.metadata.doc_id}</div>
              <div><span className="opacity-60">title: </span>{chunk?.metadata.title || '—'}</div>
              <div><span className="opacity-60">standard_no: </span>{chunk?.metadata.standard_no}</div>
              <div><span className="opacity-60">doc_type: </span>{chunk?.metadata.doc_type}</div>
            </div>
          </div>
        </div>

        <SheetFooter>
          <Button
            className="bg-accent hover:bg-accent/90 text-accent-foreground"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? '保存中...' : '保存'}
          </Button>
          <Button variant="secondary" onClick={handleCancel} disabled={saving}>
            取消
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
