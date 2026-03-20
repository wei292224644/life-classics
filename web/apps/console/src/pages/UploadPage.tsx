import { useCallback, useEffect, useRef, useState } from 'react'
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

interface LastUpload {
  fileName: string
  stages: StageState[]
  chunksCount?: number
  error?: string
  completedAt?: string
}

const LS_KEY = 'kb-last-upload'

function loadLastUpload(): LastUpload | null {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? (JSON.parse(raw) as LastUpload) : null
  } catch {
    return null
  }
}

function saveLastUpload(data: LastUpload) {
  localStorage.setItem(LS_KEY, JSON.stringify(data))
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

export function UploadPage() {
  const { refreshStats } = useOutletContext<LayoutContext>()
  const { toast } = useToast()

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [lastUpload, setLastUpload] = useState<LastUpload | null>(loadLastUpload)
  const [stages, setStages] = useState<StageState[]>(
    PIPELINE_STAGES.map(s => ({ ...s, status: 'pending' as StageStatus }))
  )

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const uploadTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stageIndexRef = useRef(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // Restore last upload stage state on mount
  useEffect(() => {
    if (lastUpload) {
      setStages(lastUpload.stages)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (uploadTimeoutRef.current) clearTimeout(uploadTimeoutRef.current)
    }
  }, [])

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

  const startStageTimer = () => {
    stageIndexRef.current = 0
    const initialStages = PIPELINE_STAGES.map((s, i) => ({
      ...s,
      status: (i === 0 ? 'active' : 'pending') as StageStatus,
    }))
    setStages(initialStages)

    timerRef.current = setInterval(() => {
      stageIndexRef.current += 1
      const idx = stageIndexRef.current
      if (idx >= PIPELINE_STAGES.length) {
        if (timerRef.current) clearInterval(timerRef.current)
        return
      }
      setStages(prev =>
        prev.map((s, i) => ({
          ...s,
          status: i < idx ? 'done' : i === idx ? 'active' : 'pending',
        }))
      )
    }, 3000)
  }

  const finishStages = (success: boolean) => {
    if (timerRef.current) clearInterval(timerRef.current)
    setStages(prev =>
      prev.map((s) => {
        if (s.status === 'done') return s
        if (s.status === 'active') return { ...s, status: success ? 'done' : 'error' as StageStatus }
        return { ...s, status: success ? 'done' : 'pending' as StageStatus }
      })
    )
  }

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return
    setIsUploading(true)
    startStageTimer()

    uploadTimeoutRef.current = setTimeout(() => {
      finishStages(false)
      setIsUploading(false)
      // persist timeout failure
      const timeoutUpload: LastUpload = {
        fileName: selectedFile.name,
        stages: PIPELINE_STAGES.map((s, i) => ({
          ...s,
          status: (i < stageIndexRef.current ? 'done' : i === stageIndexRef.current ? 'error' : 'pending') as StageStatus,
        })),
        error: '上传超时',
        completedAt: new Date().toISOString(),
      }
      setLastUpload(timeoutUpload)
      saveLastUpload(timeoutUpload)
      toast({ description: '上传超时（180秒），请检查服务状态', variant: 'destructive' })
    }, 180_000)

    try {
      const result = await api.documents.upload(selectedFile)
      if (uploadTimeoutRef.current) { clearTimeout(uploadTimeoutRef.current); uploadTimeoutRef.current = null }
      finishStages(true)

      const upload: LastUpload = {
        fileName: result.file_name,
        stages: PIPELINE_STAGES.map(s => ({ ...s, status: 'done' as StageStatus })),
        chunksCount: result.chunks_count,
        completedAt: new Date().toISOString(),
      }
      setLastUpload(upload)
      saveLastUpload(upload)
      setSelectedFile(null)
      if (inputRef.current) inputRef.current.value = ''
      refreshStats()
      toast({ description: `入库成功，共生成 ${result.chunks_count} 个 chunk` })
    } catch (err) {
      if (uploadTimeoutRef.current) { clearTimeout(uploadTimeoutRef.current); uploadTimeoutRef.current = null }
      finishStages(false)
      const message = (err as Error).message
      // Use stageIndexRef to reconstruct stage state at time of failure
      const failedStages: StageState[] = PIPELINE_STAGES.map((s, i) => ({
        ...s,
        status: (i < stageIndexRef.current ? 'done' : i === stageIndexRef.current ? 'error' : 'pending') as StageStatus,
      }))
      const upload: LastUpload = {
        fileName: selectedFile.name,
        stages: failedStages,
        error: message,
        completedAt: new Date().toISOString(),
      }
      setLastUpload(upload)
      saveLastUpload(upload)
      toast({ description: `上传失败: ${message}`, variant: 'destructive' })
    } finally {
      setIsUploading(false)
    }
  }

  const currentStages = isUploading ? stages : (lastUpload?.stages ?? null)

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

        {currentStages ? (
          <div className="bg-muted/50 border border-border rounded-xl p-5 flex flex-col gap-3">
            {(lastUpload && !isUploading) && (
              <div className="text-xs text-muted-foreground mb-1">
                {lastUpload.fileName}
                {lastUpload.chunksCount != null && ` · ${lastUpload.chunksCount} chunks`}
                {lastUpload.error && <span className="text-red-400 ml-1">· 失败</span>}
              </div>
            )}
            {currentStages.map(stage => (
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
