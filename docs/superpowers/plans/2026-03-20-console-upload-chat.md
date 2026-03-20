# Console 上传与对话功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为控制台新增"上传 Markdown 文档"和"与 RAG Agent 对话"两个功能，并引入 React Router 做路由管理。

**Architecture:** 引入 `react-router-dom` 将 App 改为路由驱动；抽出 `Layout` 组件管理全局 Header + TabNav + Outlet；新增 `UploadPage`（左右分栏，左侧上传区，右侧流水线进度）和 `ChatPage`（全宽对话流）。状态通过 `localStorage` 持久化，跨标签切换不丢失。

**Tech Stack:** React 19、Vite、react-router-dom@^7、react-markdown@^9、shadcn/ui、Tailwind CSS、localStorage

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|---|---|
| `src/components/Layout.tsx` | 全局布局：Header + TabNav + Outlet，管理 kbStats 状态和 refreshStats 回调 |
| `src/components/TabNav.tsx` | 标签导航：Chunks / 上传 / 对话，使用 NavLink，对话页显示清空按钮 |
| `src/pages/ChunksPage.tsx` | 将现有 DocList + ChunkList 两列布局从 App.tsx 中抽出 |
| `src/pages/UploadPage.tsx` | 左右分栏：左侧文件上传区，右侧流水线进度面板（localStorage 持久化） |
| `src/pages/ChatPage.tsx` | 全宽对话流：消息列表 + 输入区，消息 localStorage 持久化 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `src/App.tsx` | 改为 BrowserRouter + Routes 配置，移除原有布局逻辑 |
| `src/api/types.ts` | 新增 4 个类型：UploadDocumentResponse、AgentChatRequest、SearchResult、AgentResponse |
| `src/api/client.ts` | 新增 `documents.upload`（fetch + FormData）和 `agent.chat` 方法 |
| `package.json` | 新增 react-router-dom@^7、react-markdown@^9 |

---

## Task 1: 安装依赖 + 新增类型定义

**Files:**
- Modify: `web/apps/console/package.json`
- Modify: `web/apps/console/src/api/types.ts`

- [ ] **Step 1: 安装新依赖**

在 `web/apps/console/` 目录下（项目使用 pnpm workspace，若 npm 报错请改用 pnpm）：

```bash
cd web/apps/console
npm install react-router-dom@^7 react-markdown@^9
```

确认 `package.json` 的 `dependencies` 中出现：
```json
"react-router-dom": "^7.x.x",
"react-markdown": "^9.x.x"
```

- [ ] **Step 2: 新增类型定义**

在 `src/api/types.ts` 末尾追加：

```typescript
export interface UploadDocumentResponse {
  success: boolean
  message: string
  doc_id: string | null
  chunks_count: number
  file_name: string
  strategy: string
}

export interface AgentChatRequest {
  message: string
  conversation_history: { role: string; content: string }[]
  thread_id: string
}

export interface SearchResult {
  id: string
  content: string
  metadata?: Record<string, unknown>
  relevance_score?: number
  relevance_reason?: string
}

export interface AgentResponse {
  content: string
  sources: SearchResult[] | null
  tool_calls: Record<string, unknown>[] | null
}
```

- [ ] **Step 3: 验证类型编译无报错**

```bash
cd web/apps/console
npx tsc --noEmit
```

Expected: 无报错输出。

- [ ] **Step 4: Commit**

```bash
git add web/apps/console/package.json web/apps/console/src/api/types.ts
git commit -m "feat(console): add deps and new type definitions for upload and chat"
```

---

## Task 2: 扩展 API 客户端

**Files:**
- Modify: `web/apps/console/src/api/client.ts`

- [ ] **Step 1: 新增 upload 方法**

在 `src/api/client.ts` 中，更新导入并在 `api` 对象里添加 upload 和 agent：

```typescript
import type {
  Chunk,
  ChunksListResponse,
  DocumentInfo,
  KBStats,
  UpdateChunkPayload,
  UploadDocumentResponse,
  AgentChatRequest,
  AgentResponse,
} from './types'
```

在 `api` 对象的 `documents` 下新增 upload，并新增 `agent` 命名空间：

```typescript
export const api = {
  documents: {
    list: () => request<{ documents: DocumentInfo[]; total: number }>('/documents'),
    clearAll: () =>
      request<{
        status: string
        deleted_documents: number
        deleted_chunks: number
      }>('/documents/clear', { method: 'DELETE' }),
    upload: async (file: File): Promise<UploadDocumentResponse> => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('strategy', 'text')
      const res = await fetch('/api/documents', { method: 'POST', body: formData })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? `HTTP ${res.status}`)
      }
      return res.json()
    },
  },
  chunks: {
    // ⚠️ 保持原有 chunks 命名空间不变，不要替换，只合并新增内容
  },
  kb: {
    stats: () => request<KBStats>('/kb/stats'),
  },
  agent: {
    chat: (payload: AgentChatRequest): Promise<AgentResponse> =>
      request('/agent/chat', { method: 'POST', body: JSON.stringify(payload) }),
  },
}
```

- [ ] **Step 2: 验证编译**

```bash
cd web/apps/console
npx tsc --noEmit
```

Expected: 无报错。

- [ ] **Step 3: Commit**

```bash
git add web/apps/console/src/api/client.ts
git commit -m "feat(console): add upload and agent.chat API methods"
```

---

## Task 3: 重构 App.tsx + 创建 Layout 和 TabNav

**Files:**
- Modify: `web/apps/console/src/App.tsx`
- Create: `web/apps/console/src/components/Layout.tsx`
- Create: `web/apps/console/src/components/TabNav.tsx`
- Create: `web/apps/console/src/pages/ChunksPage.tsx`

- [ ] **Step 1: 抽出 ChunksPage**

新建 `src/pages/ChunksPage.tsx`，将现有 DocList + ChunkList 两列逻辑从 App.tsx 移入：

```tsx
import { useState } from 'react'
import { DocList } from '@/components/DocList'
import { ChunkList } from '@/components/ChunkList'
import { api } from '@/api/client'
import type { DocumentInfo } from '@/api/types'
import { useEffect } from 'react'

export function ChunksPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)

  useEffect(() => {
    api.documents.list()
      .then(res => setDocuments(res.documents))
      .finally(() => setDocsLoading(false))
  }, [])

  return (
    <div className="flex flex-1 min-h-0">
      <aside className="w-60 shrink-0 flex flex-col min-h-0">
        <DocList
          documents={documents}
          loading={docsLoading}
          selectedDocId={selectedDocId}
          onSelect={setSelectedDocId}
        />
      </aside>
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <ChunkList docId={selectedDocId} />
      </main>
    </div>
  )
}
```

- [ ] **Step 2: 创建 TabNav**

新建 `src/components/TabNav.tsx`：

```tsx
import { NavLink, useLocation } from 'react-router-dom'

interface TabNavProps {
  onClearChat?: () => void
}

export function TabNav({ onClearChat }: TabNavProps) {
  const location = useLocation()
  const isChat = location.pathname === '/chat'

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 text-sm border-b-2 transition-colors ${
      isActive
        ? 'border-purple-600 text-foreground font-medium'
        : 'border-transparent text-muted-foreground hover:text-foreground'
    }`

  return (
    <nav className="flex items-center border-b border-border shrink-0 bg-card px-2">
      <NavLink end to="/chunks" className={linkClass}>Chunks</NavLink>
      <NavLink end to="/upload" className={linkClass}>上传</NavLink>
      <NavLink end to="/chat" className={linkClass}>对话</NavLink>
      {isChat && onClearChat && (
        <button
          onClick={onClearChat}
          className="ml-auto mr-2 text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1"
        >
          清空对话
        </button>
      )}
    </nav>
  )
}
```

- [ ] **Step 3: 创建 Layout**

新建 `src/components/Layout.tsx`：

```tsx
import { useEffect, useRef, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { TabNav } from './TabNav'
import { api } from '@/api/client'
import type { KBStats } from '@/api/types'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { buttonVariants } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

// 暴露给子页面的 context（通过 Outlet context 传递）
export interface LayoutContext {
  refreshStats: () => void
  clearChatRef: React.MutableRefObject<(() => void) | null>
}

export function Layout() {
  const [stats, setStats] = useState<KBStats | null>(null)
  const [clearOpen, setClearOpen] = useState(false)
  const [clearing, setClearing] = useState(false)
  const { toast } = useToast()
  const clearChatRef = useRef<(() => void) | null>(null)

  const refreshStats = () => {
    api.kb.stats().then(setStats).catch(() => {})
  }

  useEffect(() => { refreshStats() }, [])

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0">
        <span className="font-bold text-sm tracking-wide">⚡ KB Admin</span>
        {stats && (
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span>chunks <strong className="text-foreground">{stats.total_chunks}</strong></span>
            <span>docs <strong className="text-foreground">{stats.total_documents}</strong></span>
          </div>
        )}
        <AlertDialog open={clearOpen} onOpenChange={setClearOpen}>
          <AlertDialogTrigger asChild>
            <button
              className={buttonVariants({ variant: 'destructive' })}
              style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
            >
              清空
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>清空知识库</AlertDialogTitle>
              <AlertDialogDescription>
                此操作将删除所有文档和 Chunks，且不可恢复。是否继续？
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setClearOpen(false)}>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  setClearing(true)
                  try {
                    const result = await api.documents.clearAll()
                    toast({ description: `已清空 ${result.deleted_documents} 个文档，${result.deleted_chunks} 个 chunks` })
                    refreshStats()
                  } catch (err) {
                    toast({ description: `清空失败: ${(err as Error).message}`, variant: 'destructive' })
                  } finally {
                    setClearing(false)
                    setClearOpen(false)
                  }
                }}
                disabled={clearing}
              >
                {clearing ? '清空中...' : '确认清空'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </header>

      {/* Tab Nav */}
      <TabNav onClearChat={() => clearChatRef.current?.()} />

      {/* Page Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <Outlet context={{ refreshStats, clearChatRef } satisfies LayoutContext} />
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 重写 App.tsx**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ChunksPage } from './pages/ChunksPage'
import { UploadPage } from './pages/UploadPage'
import { ChatPage } from './pages/ChatPage'
import { Toaster } from '@/components/ui/toaster'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/chunks" replace />} />
          <Route path="chunks" element={<ChunksPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="chat" element={<ChatPage />} />
        </Route>
      </Routes>
      <Toaster />
    </BrowserRouter>
  )
}
```

> 注意：`UploadPage` 和 `ChatPage` 此时尚未创建，会有编译报错。先创建空占位文件：
>
> `src/pages/UploadPage.tsx`:
> ```tsx
> export function UploadPage() { return <div className="p-6">Upload coming soon</div> }
> ```
>
> `src/pages/ChatPage.tsx`:
> ```tsx
> export function ChatPage() { return <div className="p-6">Chat coming soon</div> }
> ```

- [ ] **Step 5: 验证路由基本工作**

```bash
cd web/apps/console
npm run dev
```

打开 http://localhost:5173，确认：
- 自动重定向到 `/chunks`
- Chunks 标签高亮，现有文档列表和 Chunk 列表正常显示
- 点击"上传"和"对话"标签可切换（显示占位内容）
- Header 统计数据正常加载
- 清空按钮弹窗正常工作

- [ ] **Step 6: Commit**

```bash
git add web/apps/console/src/
git commit -m "feat(console): add react-router, Layout, TabNav, ChunksPage"
```

---

## Task 4: 实现 UploadPage

**Files:**
- Modify: `web/apps/console/src/pages/UploadPage.tsx`

流水线阶段定义（9 个节点，来自 `server/parser/graph.py`）：

```typescript
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
```

localStorage key: `kb-last-upload`，存储结构：

```typescript
interface LastUpload {
  fileName: string
  stages: Array<{ id: string; label: string; status: 'done' | 'error' | 'pending' }>
  chunksCount?: number
  error?: string
  completedAt?: string
}
```

- [ ] **Step 1: 实现完整 UploadPage**

用以下内容替换 `src/pages/UploadPage.tsx`：

```tsx
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
    return raw ? JSON.parse(raw) : null
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
  const stageIndexRef = useRef(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // 恢复上次上传的阶段状态
  useEffect(() => {
    if (lastUpload) {
      setStages(lastUpload.stages)
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
        clearInterval(timerRef.current!)
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
      prev.map((s, i) => {
        if (s.status === 'done') return s
        if (s.status === 'active') return { ...s, status: success ? 'done' : 'error' }
        return { ...s, status: success ? 'done' : 'pending' }
      })
    )
  }

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return
    setIsUploading(true)
    startStageTimer()

    const timeoutId = setTimeout(() => {
      finishStages(false)
      setIsUploading(false)
      toast({ description: '上传超时（180秒），请检查服务状态', variant: 'destructive' })
    }, 180_000)

    try {
      const result = await api.documents.upload(selectedFile)
      clearTimeout(timeoutId)
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
      clearTimeout(timeoutId)
      finishStages(false)
      const message = (err as Error).message
      const upload: LastUpload = {
        fileName: selectedFile.name,
        stages,
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
    <div className="flex gap-6 p-6 h-full">
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
```

- [ ] **Step 2: 验证 UploadPage 编译和基本交互**

```bash
cd web/apps/console
npm run dev
```

访问 http://localhost:5173/upload，确认：
- 拖拽区域可点击，文件选择器仅允许 `.md` 文件
- 选择非 `.md` 文件时出现 toast 错误
- 选择超过 5MB 文件时出现 toast 错误
- 选择合法文件后显示文件名和大小
- 点击 ✕ 清除文件
- 右侧无上传时显示占位文字
- 刷新页面后右侧恢复上次上传状态（如有）

- [ ] **Step 3: Commit**

```bash
git add web/apps/console/src/pages/UploadPage.tsx
git commit -m "feat(console): implement UploadPage with pipeline progress panel"
```

---

## Task 5: 实现 ChatPage

**Files:**
- Modify: `web/apps/console/src/pages/ChatPage.tsx`

localStorage key: `kb-chat-messages`，存储结构：

```typescript
interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SearchResult[]
}
```

- [ ] **Step 1: 实现完整 ChatPage**

用以下内容替换 `src/pages/ChatPage.tsx`：

```tsx
import { useEffect, useRef, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { api } from '@/api/client'
import type { SearchResult } from '@/api/types'
import { useToast } from '@/hooks/use-toast'
import type { LayoutContext } from '@/components/Layout'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SearchResult[]
}

const LS_KEY = 'kb-chat-messages'

function loadMessages(): Message[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveMessages(msgs: Message[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(msgs))
}

export function ChatPage() {
  const { clearChatRef } = useOutletContext<LayoutContext>()
  const { toast } = useToast()

  const [messages, setMessages] = useState<Message[]>(loadMessages)
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 注册清空回调到 Layout
  useEffect(() => {
    clearChatRef.current = () => {
      setMessages([])
      localStorage.removeItem(LS_KEY)
    }
    return () => { clearChatRef.current = null }
  }, [clearChatRef])

  // 持久化消息
  useEffect(() => {
    saveMessages(messages)
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isSending) return

    const userMsg: Message = { role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setIsSending(true)

    // 滚动到底部
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)

    try {
      const res = await api.agent.chat({
        message: text,
        conversation_history: messages.map(m => ({ role: m.role, content: m.content })),
        thread_id: 'console-test',
      })
      const assistantMsg: Message = {
        role: 'assistant',
        content: res.content,
        sources: res.sources ?? undefined,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      toast({ description: `发送失败: ${(err as Error).message}`, variant: 'destructive' })
    } finally {
      setIsSending(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Message List */}
      <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center text-muted-foreground gap-2 mt-20">
            <span className="text-4xl">💬</span>
            <p className="text-base font-medium">开始与知识库对话</p>
            <p className="text-sm">提问关于 GB 标准的任何问题</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                <div
                  className="max-w-[70%] bg-purple-700 text-white text-sm px-4 py-2.5"
                  style={{ borderRadius: '12px 12px 2px 12px' }}
                >
                  {msg.content}
                </div>
              ) : (
                <div className="max-w-[85%] flex flex-col gap-2">
                  <div className="bg-muted border border-border rounded-xl rounded-tl-sm px-4 py-3 text-sm prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                  {/* 来源（预留：当前 sources 始终为 null） */}
                  {msg.sources && msg.sources.length > 0 && (
                    <SourcesPanel sources={msg.sources} />
                  )}
                </div>
              )}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border px-6 py-4 shrink-0 flex gap-3">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          rows={1}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行…"
          className="flex-1 resize-none bg-muted border border-border rounded-lg px-3 py-2 text-sm placeholder:text-muted-foreground disabled:opacity-50 focus:outline-none focus:ring-1 focus:ring-purple-600"
          style={{ minHeight: '40px', maxHeight: '120px' }}
          onInput={e => {
            const t = e.currentTarget
            t.style.height = 'auto'
            t.style.height = `${Math.min(t.scrollHeight, 120)}px`
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isSending}
          className="bg-purple-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-600 transition-colors shrink-0"
        >
          {isSending ? '发送中…' : '发送'}
        </button>
      </div>
    </div>
  )
}

function SourcesPanel({ sources }: { sources: SearchResult[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="text-xs border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-muted/50 hover:bg-muted text-muted-foreground"
      >
        <span>📚 召回来源 · {sources.length} 个 chunk</span>
        <span className="ml-auto">{open ? '▲' : '▶'}</span>
      </button>
      {open && (
        <div className="flex flex-col divide-y divide-border">
          {sources.map(s => (
            <div key={s.id} className="px-3 py-2 text-muted-foreground">
              <span className="text-purple-400">{s.metadata?.doc_id as string ?? s.id}</span>
              {s.metadata?.section_path && <span> / {s.metadata.section_path as string}</span>}
              {s.relevance_score != null && (
                <span className="ml-2 text-muted-foreground/60">· {s.relevance_score.toFixed(2)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 验证 ChatPage 编译和基本交互**

```bash
cd web/apps/console
npm run dev
```

访问 http://localhost:5173/chat，确认：
- 空状态显示 💬 引导文字
- 输入文字后发送按钮可用
- 空消息发送按钮禁用
- Enter 发送，Shift+Enter 换行
- 发送中输入框和按钮禁用
- 切换到其他标签再回来，消息历史保留
- 刷新页面消息历史保留
- "清空对话"按钮（TabNav 右侧）点击后消息清空

- [ ] **Step 3: 端到端验证（需后端在线）**

确保后端服务运行在 http://localhost:9999，然后：
1. 在 `/upload` 上传一个 GB 标准 .md 文件，观察流水线进度逐步推进，上传完成后 Header 统计更新
2. 在 `/chat` 发送一条与刚上传文档相关的问题，确认收到 AI 回复且内容 Markdown 正常渲染

- [ ] **Step 4: 最终构建验证**

```bash
cd web/apps/console
npm run build
```

Expected: 构建成功，无 TypeScript 错误。

- [ ] **Step 5: Commit**

```bash
git add web/apps/console/src/pages/ChatPage.tsx
git commit -m "feat(console): implement ChatPage with markdown rendering and localStorage persistence"
```

---

## 完成检查清单

- [ ] `/chunks` 路由：现有文档列表和 Chunk 编辑功能完整保留
- [ ] `/upload` 路由：文件校验、进度模拟、localStorage 持久化、refreshStats 调用
- [ ] `/chat` 路由：多轮对话、localStorage 持久化、清空对话功能
- [ ] Header 统计数据在上传成功后自动刷新
- [ ] `npm run build` 构建成功无报错
