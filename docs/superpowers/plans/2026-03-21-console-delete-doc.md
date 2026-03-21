# 控制台单独删除文档 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在控制台文档列表中为每条文档添加删除按钮，支持确认弹窗和 loading 状态。

**Architecture:** 三处改动：(1) `api/client.ts` 新增 `delete` 方法；(2) `DocList.tsx` 添加删除按钮（hover 显示、受控 AlertDialog 确认、`deletingDocId` loading 状态）；(3) `ChunksPage.tsx` 实现删除逻辑，提取 `refreshDocuments`，管理 `deletingDocId` state。

**Tech Stack:** React 19, TypeScript, Radix UI (`alert-dialog`), Tailwind CSS, lucide-react, `@/api/client.ts`

---

## 文件变更一览

| 操作 | 文件 | 说明 |
|------|------|------|
| Modify | `web/apps/console/src/api/client.ts` | 新增 `api.documents.delete(doc_id)` |
| Modify | `web/apps/console/src/components/DocList.tsx` | 新增删除按钮 + AlertDialog |
| Modify | `web/apps/console/src/pages/ChunksPage.tsx` | 提取 `refreshDocuments`，实现 `handleDeleteDoc` |

---

## Task 1: `api/client.ts` 新增 `delete` 方法

**Files:**
- Modify: `web/apps/console/src/api/client.ts:27-34`

- [ ] **Step 1: 在 `api.documents` 对象中新增 `delete` 方法**

在 `list` 和 `clearAll` 之间插入：

```ts
delete: (doc_id: string) =>
  request<{ doc_id: string; errors: string[] }>(`/documents/${doc_id}`, { method: 'DELETE' }),
```

完整的 `api.documents` 块变为：

```ts
documents: {
  list: () => request<{ documents: DocumentInfo[]; total: number }>('/documents'),
  delete: (doc_id: string) =>
    request<{ doc_id: string; errors: string[] }>(`/documents/${doc_id}`, { method: 'DELETE' }),
  clearAll: () =>
    request<{
      status: string
      deleted_documents: number
      deleted_chunks: number
    }>('/documents/clear', { method: 'DELETE' }),
  upload: async (
    // ... 保持不变
```

- [ ] **Step 2: 确认 TypeScript 无类型错误**

```bash
cd web
pnpm --filter @acme/console tsc --noEmit
```

预期：无错误输出。

- [ ] **Step 3: Commit**

```bash
git add web/apps/console/src/api/client.ts
git commit -m "feat(console): add delete method to api.documents"
```

---

## Task 2: `DocList.tsx` 添加删除按钮 + AlertDialog

**Files:**
- Modify: `web/apps/console/src/components/DocList.tsx`

- [ ] **Step 1: 更新 Props 接口**

将文件顶部的 `Props` 接口改为：

```ts
interface Props {
  documents: DocumentInfo[]
  loading: boolean
  selectedDocId: string | null
  onSelect: (docId: string) => void
  onDelete: (docId: string) => Promise<void>
  deletingDocId: string | null
}
```

- [ ] **Step 2: 新增 import**

原文件第 1 行已有 `import { useState, useMemo } from 'react'`，**保持不变**。在该行之后追加：

```ts
import { Trash2, Loader2 } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
```

- [ ] **Step 3: 将每条文档 item 改为带删除按钮的受控 AlertDialog**

将原来的 `filtered.map(doc => (...))` 替换为：

```tsx
{filtered.map(doc => {
  const isDeleting = deletingDocId === doc.doc_id
  return (
    <DocItem
      key={doc.doc_id}
      doc={doc}
      selected={selectedDocId === doc.doc_id}
      isDeleting={isDeleting}
      onSelect={onSelect}
      onDelete={onDelete}
    />
  )
})}
```

在组件文件末尾（`DocList` 函数外）添加 `DocItem` 子组件：

```tsx
interface DocItemProps {
  doc: DocumentInfo
  selected: boolean
  isDeleting: boolean
  onSelect: (docId: string) => void
  onDelete: (docId: string) => Promise<void>
}

function DocItem({ doc, selected, isDeleting, onSelect, onDelete }: DocItemProps) {
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      await onDelete(doc.doc_id)
    } finally {
      setConfirming(false)
      setOpen(false)
    }
  }

  return (
    <div className="group relative">
      <button
        onClick={() => onSelect(doc.doc_id)}
        className={`w-full text-left px-3 py-2 rounded-md transition-colors text-sm pr-8 ${
          selected
            ? 'bg-accent/20 border-l-2 border-accent'
            : 'hover:bg-secondary'
        }`}
      >
        <div className="font-medium text-foreground truncate">
          {doc.title || doc.doc_id}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="text-xs text-muted-foreground truncate">{doc.doc_type}</span>
          <Badge variant="secondary" className="text-xs px-1 py-0 h-4">
            {doc.chunks_count}
          </Badge>
        </div>
      </button>

      <button
        onClick={e => { e.stopPropagation(); setOpen(true) }}
        disabled={isDeleting}
        className="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-opacity disabled:opacity-50"
        aria-label="删除文档"
      >
        {isDeleting
          ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
          : <Trash2 className="h-3.5 w-3.5" />
        }
      </button>

      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确认删除「{doc.title || doc.doc_id}」？此操作将删除该文档所有 chunks，无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={confirming}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={e => { e.preventDefault(); handleConfirm() }}
              disabled={confirming}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {confirming ? <Loader2 className="h-4 w-4 animate-spin" /> : '删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
```

- [ ] **Step 4: 确认 TypeScript 无错误**

```bash
cd web
pnpm --filter @acme/console tsc --noEmit
```

预期：无错误。

- [ ] **Step 5: Commit**

```bash
git add web/apps/console/src/components/DocList.tsx
git commit -m "feat(console): add per-document delete button with confirmation dialog"
```

---

## Task 3: `ChunksPage.tsx` 实现删除逻辑

**Files:**
- Modify: `web/apps/console/src/pages/ChunksPage.tsx`

- [ ] **Step 1: 更新 import**

将第 1 行改为（新增 `useCallback`）：

```ts
import { useState, useEffect, useCallback } from 'react'
```

在现有 import 块末尾追加（原文件已有 `DocumentInfo` import，保留不变）：

```ts
import { useToast } from '@/hooks/use-toast'
```

- [ ] **Step 2: 重写 `ChunksPage` 函数**

完整替换 `ChunksPage` 函数体（保留文件顶部所有 import 不变，只替换函数本身）：

```tsx
export function ChunksPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null)
  const { toast } = useToast()

  const refreshDocuments = useCallback(async () => {
    const res = await api.documents.list()
    setDocuments(res.documents)
  }, [])

  useEffect(() => {
    api.documents.list()
      .then(res => setDocuments(res.documents))
      .finally(() => setDocsLoading(false))
  }, [])

  const handleDeleteDoc = async (docId: string) => {
    setDeletingDocId(docId)
    try {
      const result = await api.documents.delete(docId)
      if (selectedDocId === docId) setSelectedDocId(null)
      await refreshDocuments()
      if (result.errors.length > 0) {
        toast({ title: '部分删除失败', description: result.errors.join('; '), variant: 'destructive' })
      } else {
        toast({ title: '已删除' })
      }
    } catch (e) {
      toast({ title: '删除失败', description: (e as Error).message, variant: 'destructive' })
    } finally {
      setDeletingDocId(null)
    }
  }

  return (
    <div className="flex flex-1 min-h-0">
      <aside className="w-60 shrink-0 flex flex-col min-h-0">
        <DocList
          documents={documents}
          loading={docsLoading}
          selectedDocId={selectedDocId}
          onSelect={setSelectedDocId}
          onDelete={handleDeleteDoc}
          deletingDocId={deletingDocId}
        />
      </aside>
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <ChunkList docId={selectedDocId} />
      </main>
    </div>
  )
}
```

- [ ] **Step 3: 确认 TypeScript 无错误**

```bash
cd web
pnpm --filter @acme/console tsc --noEmit
```

预期：无错误。

- [ ] **Step 4: 手动验证**

启动开发服务器（若未启动）：
```bash
cd web
pnpm dev
```

打开 `http://localhost:3000`，进入 Chunks 页面：
1. hover 某条文档 → 右侧出现垃圾桶图标
2. 点击垃圾桶 → AlertDialog 弹出，显示正确的文档标题
3. 点击"取消" → 弹窗关闭，文档列表不变
4. 再次点击垃圾桶 → 点击"删除" → 按钮进入 loading 状态 → 弹窗关闭 → 文档从列表移除 → Toast "已删除"
5. 若删除的是当前选中文档 → 右侧 ChunkList 变为空状态

- [ ] **Step 5: Commit**

```bash
git add web/apps/console/src/pages/ChunksPage.tsx
git commit -m "feat(console): implement delete document handler in ChunksPage"
```
