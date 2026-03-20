import { useCallback, useRef, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { api } from '@/api/client'
import { useToast } from '@/hooks/use-toast'
import type { LayoutContext } from '@/components/Layout'

const PIPELINE_STAGES = [
  { id: 'parse',     label: '解析 Markdown' },
  { id: 'clean',     label: '清洗内容' },
  { id: 'structure', label: '识别结构类型' },
  { id: 'slice',     label: '切片' },
  { id: 'classify',  label: '分类语义类型' },
  { id: 'escalate',  label: '处理低置信度 Chunk' },
  { id: 'enrich',    label: '交叉引用富化' },
  { id: 'transform', label: '内容转换' },
  { id: 'merge',     label: '合并相邻 Chunk' },
]

type StageStatus = 'pending' | 'active' | 'done' | 'error'

interface StageState {
  id: string
  label: string
  status: StageStatus
}

function StageIcon({ status }: { status: StageStatus }) {
  if (status === 'done') {
    return (
      <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center shrink-0">
        <span className="text-[10px] text-black font-bold">✓</span>
      </div>
    )
  }
  if (status === 'active') {
    return (
      <div className="w-5 h-5 rounded-full bg-purple-600 flex items-center justify-center shrink-0">
        <div className="w-2.5 h-2.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (status === 'error') {
    return (
      <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center shrink-0">
        <span className="text-[10px] text-white font-bold">✕</span>
      </div>
    )
  }
  return <div className="w-5 h-5 rounded-full bg-muted border border-border shrink-0" />
}

const initialStages = (): StageState[] =>
  PIPELINE_STAGES.map(s => ({ ...s, status: 'pending' as StageStatus }))

export function UploadPage() {
  const { refreshStats } = useOutletContext<LayoutContext>()
  const { toast } = useToast()

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [stages, setStages] = useState<StageState[]>(initialStages)
  const [hasResult, setHasResult] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    if (!file.name.endsWith('.md')) return '仅支持 Markdown 文件（.md）'
    if (file.size > 5 * 1024 * 1024) return '文件过大，请上传 5MB 以内的文件'
    return null
  }

  const handleFile = (file: File) => {
    const err = validateFile(file)
    if (err) { toast({ description: err, variant: 'destructive' }); return }
    setSelectedFile(file)
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return
    setIsUploading(true)
    setHasResult(true)
    setStages(initialStages())

    try {
      const result = await api.documents.upload(selectedFile, (stage, status) => {
        setStages(prev =>
          prev.map(s => s.id === stage ? { ...s, status } : s)
        )
      })
      // 将仍为 pending/active 的阶段标为 done（escalate 可能被跳过）
      setStages(prev =>
        prev.map(s =>
          s.status === 'pending' || s.status === 'active' ? { ...s, status: 'done' } : s
        )
      )
      setSelectedFile(null)
      if (inputRef.current) inputRef.current.value = ''
      refreshStats()
      toast({ description: `入库成功，共生成 ${result.chunks_count} 个 chunk` })
    } catch (err) {
      const message = (err as Error).message
      setStages(prev =>
        prev.map(s => s.status === 'active' ? { ...s, status: 'error' } : s)
      )
      toast({ description: `上传失败: ${message}`, variant: 'destructive' })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="flex gap-6 p-6 flex-1 min-h-0 overflow-hidden">
      {/* Left: Upload Area */}
      <div className="flex-1 flex flex-col gap-4">
        <p className="text-xs text-muted-foreground uppercase tracking-widest">上传文件</p>

        {/* Drop Zone */}
        <div
          onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
            isDragging ? 'border-purple-500 bg-purple-500/10' : 'border-border hover:border-purple-500/50'
          }`}
        >
          <div className="text-3xl mb-2">📄</div>
          <p className="text-sm text-foreground mb-1">拖拽 .md 文件到此处</p>
          <p className="text-xs text-muted-foreground mb-4">或点击选择文件 · 最大 5MB</p>
          <span className="bg-purple-700 text-white text-xs px-4 py-1.5 rounded-md">选择文件</span>
          <input
            ref={inputRef}
            type="file"
            accept=".md"
            className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
          />
        </div>

        {/* Selected File */}
        {selectedFile && (
          <div className="flex items-center gap-2 px-3 py-2 bg-muted rounded-md border border-border text-sm">
            <span className="text-purple-400">📝</span>
            <span className="flex-1 text-foreground truncate">{selectedFile.name}</span>
            <span className="text-muted-foreground text-xs">{(selectedFile.size / 1024).toFixed(0)} KB</span>
            <button
              onClick={() => { setSelectedFile(null); if (inputRef.current) inputRef.current.value = '' }}
              className="text-muted-foreground hover:text-foreground text-xs ml-1"
            >✕</button>
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!selectedFile || isUploading}
          className="w-full bg-purple-700 text-white py-2.5 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-600 transition-colors"
        >
          {isUploading ? '上传中...' : '上传并入库'}
        </button>
      </div>

      {/* Right: Pipeline Progress */}
      <div className="flex-1 flex flex-col gap-3">
        <p className="text-xs text-muted-foreground uppercase tracking-widest">处理进度</p>

        {hasResult ? (
          <div className="bg-muted/50 border border-border rounded-xl p-5 flex flex-col gap-3">
            {stages.map(stage => (
              <div key={stage.id} className="flex items-center gap-3">
                <StageIcon status={stage.status} />
                <span className={`text-sm ${
                  stage.status === 'active' ? 'text-foreground font-medium' :
                  stage.status === 'done' ? 'text-muted-foreground' :
                  stage.status === 'error' ? 'text-red-400' : 'text-muted-foreground/40'
                }`}>
                  {stage.label}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
            上传后此处显示处理进度
          </div>
        )}
      </div>
    </div>
  )
}
