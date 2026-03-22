import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter,
} from '@/components/ui/sheet'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/api/client'
import type { DocumentInfo } from '@/api/types'

interface Props {
  doc: DocumentInfo | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}

export function DocEditDrawer({ doc, open, onClose, onSaved }: Props) {
  const { toast } = useToast()
  const [title, setTitle] = useState('')
  const [standardNo, setStandardNo] = useState('')
  const [docType, setDocType] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (doc) {
      setTitle(doc.title)
      setStandardNo(doc.standard_no)
      setDocType(doc.doc_type)
    }
  }, [doc])

  async function handleSave() {
    if (!doc) return
    setSaving(true)
    try {
      await api.documents.update(doc.doc_id, {
        title,
        standard_no: standardNo,
        doc_type: docType,
      })
      toast({ title: '已保存' })
      onSaved()
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
      <SheetContent side="right" className="w-[480px] flex flex-col">
        <SheetHeader>
          <SheetTitle>编辑文档</SheetTitle>
          <SheetDescription className="font-mono text-xs break-all">
            {doc?.doc_id}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-5">
          {/* 只读：doc_id */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              doc_id（只读）
            </label>
            <p className="text-xs text-muted-foreground bg-muted rounded px-3 py-2 font-mono break-all">
              {doc?.doc_id}
            </p>
          </div>

          {/* 只读：chunks_count */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              chunks_count（只读）
            </label>
            <p className="text-xs text-muted-foreground bg-muted rounded px-3 py-2">
              {doc?.chunks_count}
            </p>
          </div>

          {/* 可编辑：title */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              title
            </label>
            <Input
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="h-9 text-sm bg-secondary border-border"
              disabled={saving}
            />
          </div>

          {/* 可编辑：standard_no */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              standard_no
            </label>
            <Input
              value={standardNo}
              onChange={e => setStandardNo(e.target.value)}
              placeholder="如 GB 2762-2022"
              className="h-9 text-sm bg-secondary border-border"
              disabled={saving}
            />
          </div>

          {/* 可编辑：doc_type */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">
              doc_type
            </label>
            <Input
              value={docType}
              onChange={e => setDocType(e.target.value)}
              placeholder="如 方法标准"
              className="h-9 text-sm bg-secondary border-border"
              disabled={saving}
            />
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
