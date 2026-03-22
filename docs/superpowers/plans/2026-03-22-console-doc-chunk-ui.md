# Console UI 改进实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩宽 Doc 列表至 360px 并添加分页、新增文档编辑抽屉、完善 Chunk 编辑抽屉的只读元数据字段。

**Architecture:** 后端新增 `PATCH /api/documents/{doc_id}` 接口，通过 ChromaDB 批量更新所有同文档 chunk 的 metadata；前端新增 `DocEditDrawer` 组件复用现有 `Sheet` 模式，`DocList` 增加客户端分页逻辑，`ChunkEditDrawer` 底部补全只读元数据字段。

**Tech Stack:** Python/FastAPI + ChromaDB（后端）、React 19 + shadcn/ui Sheet + Tailwind CSS（前端）、uv（Python 包管理）、pnpm（Node 包管理）

---

### Task 1: 后端 — 新增 UpdateDocumentRequest 模型

**Files:**
- Modify: `server/api/documents/models.py`

- [ ] **Step 1: 在 models.py 末尾新增请求模型**

```python
# 在 DocumentsListResponse 之后添加
from typing import Optional

class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    standard_no: Optional[str] = None
    doc_type: Optional[str] = None
```

完整文件应为：
```python
from typing import Optional

from pydantic import BaseModel


class DocumentInfo(BaseModel):
    doc_id: str
    title: str = ""
    standard_no: str
    doc_type: str
    chunks_count: int


class DocumentsListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    standard_no: Optional[str] = None
    doc_type: Optional[str] = None
```

- [ ] **Step 2: 验证语法无误**

```bash
cd server && uv run python3 -c "from api.documents.models import UpdateDocumentRequest; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add server/api/documents/models.py
git commit -m "feat(documents): add UpdateDocumentRequest model"
```

---

### Task 2: 后端 — update_document 服务方法（TDD）

**Files:**
- Modify: `server/api/documents/service.py`
- Test: `server/tests/api/documents/test_service.py`

- [ ] **Step 1: 写失败测试**

在 `server/tests/api/documents/test_service.py` 末尾追加：

```python
def test_update_document_updates_all_chunks():
    """update_document 应更新该 doc 所有 chunk 的指定 metadata 字段"""
    from api.documents.service import DocumentsService

    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1", "c2"],
        "metadatas": [
            _make_meta("d1", "GB 2762-2022", "food_safety", title="旧标题"),
            _make_meta("d1", "GB 2762-2022", "food_safety", title="旧标题"),
        ],
    }

    with patch("api.documents.service.get_collection", return_value=mock_col):
        result = DocumentsService.update_document("d1", {"title": "新标题"})

    # collection.update 应被调用一次，ids 包含所有 chunk id
    mock_col.update.assert_called_once()
    call_kwargs = mock_col.update.call_args.kwargs
    assert set(call_kwargs["ids"]) == {"c1", "c2"}
    # 每个 metadata 应包含新 title
    for meta in call_kwargs["metadatas"]:
        assert meta["title"] == "新标题"
        # 未传入的字段保持原值
        assert meta["standard_no"] == "GB 2762-2022"

    assert result["doc_id"] == "d1"
    assert result["title"] == "新标题"
    assert result["chunks_count"] == 2


def test_update_document_returns_404_when_no_chunks():
    """doc_id 不存在时应抛出 ValueError"""
    from api.documents.service import DocumentsService

    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": [], "metadatas": []}

    with patch("api.documents.service.get_collection", return_value=mock_col):
        with pytest.raises(ValueError, match="not found"):
            DocumentsService.update_document("nonexistent", {"title": "x"})


def test_update_document_only_updates_provided_fields():
    """只更新传入的字段，未传字段保持原值"""
    from api.documents.service import DocumentsService

    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1"],
        "metadatas": [
            _make_meta("d1", "GB 2762-2022", "food_safety", title="原标题"),
        ],
    }

    with patch("api.documents.service.get_collection", return_value=mock_col):
        result = DocumentsService.update_document("d1", {"doc_type": "method"})

    call_kwargs = mock_col.update.call_args.kwargs
    meta = call_kwargs["metadatas"][0]
    assert meta["doc_type"] == "method"
    assert meta["title"] == "原标题"       # 未传入，保持原值
    assert meta["standard_no"] == "GB 2762-2022"  # 未传入，保持原值
    assert result["doc_type"] == "method"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd server && uv run pytest tests/api/documents/test_service.py::test_update_document_updates_all_chunks -v
```

Expected: FAIL with `AttributeError: type object 'DocumentsService' has no attribute 'update_document'`

- [ ] **Step 3: 在 service.py 实现 update_document**

在 `DocumentsService` 类末尾（`clear_all` 之前）添加：

```python
@staticmethod
def update_document(doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """
    更新该文档所有 chunks 的指定 metadata 字段。
    fields: 只包含要更新的键（title / standard_no / doc_type），不传的字段保持原值。
    Raises ValueError if doc_id not found.
    """
    collection = get_collection()
    result = collection.get(
        where={"doc_id": {"$eq": doc_id}},
        include=["metadatas"],
    )
    ids = result.get("ids") or []
    metadatas = result.get("metadatas") or []

    if not ids:
        raise ValueError(f"Document '{doc_id}' not found")

    updated_metadatas = []
    for meta in metadatas:
        new_meta = dict(meta)
        for key, value in fields.items():
            if value is not None:
                new_meta[key] = value
        updated_metadatas.append(new_meta)

    collection.update(ids=ids, metadatas=updated_metadatas)

    # 取第一个 metadata 构造返回值（所有 chunk 同文档，title/standard_no/doc_type 一致）
    first = updated_metadatas[0]
    return {
        "doc_id": doc_id,
        "title": first.get("title", ""),
        "standard_no": first.get("standard_no", ""),
        "doc_type": first.get("doc_type", ""),
        "chunks_count": len(ids),
    }
```

- [ ] **Step 4: 运行所有三个新测试**

```bash
cd server && uv run pytest tests/api/documents/test_service.py -v -k "update"
```

Expected: 三个测试全部 PASS

- [ ] **Step 5: 运行全部文档服务测试，确保无回归**

```bash
cd server && uv run pytest tests/api/documents/test_service.py -v
```

Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add server/api/documents/service.py server/tests/api/documents/test_service.py
git commit -m "feat(documents): add update_document service method"
```

---

### Task 3: 后端 — PATCH 路由

**Files:**
- Modify: `server/api/documents/router.py`

- [ ] **Step 1: 在 router.py 中新增 PATCH 端点**

在 `router.py` 中修改：\n\n将文件第 4 行的现有 import **替换**为（不要追加，避免重复 import）：

```python
from api.documents.models import DocumentsListResponse, DocumentInfo, UpdateDocumentRequest

@router.patch("/{doc_id}", response_model=DocumentInfo)
def update_document(doc_id: str, body: UpdateDocumentRequest):
    try:
        result = DocumentsService.update_document(
            doc_id,
            body.model_dump(exclude_none=True),
        )
        return DocumentInfo(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

注意：`UpdateDocumentRequest` 已在 `models.py` 中定义，需更新 router.py 顶部 import 行，将 `UpdateDocumentRequest` 加入：

```python
from api.documents.models import DocumentsListResponse, DocumentInfo, UpdateDocumentRequest
```

- [ ] **Step 2: 验证语法**

```bash
cd server && uv run python3 -c "from api.documents.router import router; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add server/api/documents/router.py
git commit -m "feat(documents): add PATCH /documents/{doc_id} endpoint"
```

---

### Task 4: 前端 — API 类型与客户端方法

**Files:**
- Modify: `web/apps/console/src/api/types.ts`
- Modify: `web/apps/console/src/api/client.ts`

- [ ] **Step 1: 在 types.ts 末尾添加新接口**

在 `AgentResponse` 之后追加：

```typescript
export interface UpdateDocumentPayload {
  title?: string
  standard_no?: string
  doc_type?: string
}
```

- [ ] **Step 2: 在 client.ts 中更新 import 并添加 update 方法**

将顶部 import 改为：

```typescript
import type {
  Chunk,
  ChunksListResponse,
  DocumentInfo,
  KBStats,
  UpdateChunkPayload,
  UpdateDocumentPayload,
  AgentChatRequest,
  AgentResponse,
} from './types'
```

在 `api.documents` 对象中，`clearAll` 之后添加：

```typescript
update: (doc_id: string, payload: UpdateDocumentPayload) =>
  request<DocumentInfo>(`/documents/${doc_id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),
```

- [ ] **Step 3: Commit**

```bash
git add web/apps/console/src/api/types.ts web/apps/console/src/api/client.ts
git commit -m "feat(console): add UpdateDocumentPayload type and api.documents.update"
```

---

### Task 5: 前端 — 新建 DocEditDrawer 组件

**Files:**
- Create: `web/apps/console/src/components/DocEditDrawer.tsx`

- [ ] **Step 1: 创建组件文件**

创建 `web/apps/console/src/components/DocEditDrawer.tsx`，内容如下：

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add web/apps/console/src/components/DocEditDrawer.tsx
git commit -m "feat(console): add DocEditDrawer component"
```

---

### Task 6: 前端 — ChunksPage 接入 DocEditDrawer

**Files:**
- Modify: `web/apps/console/src/pages/ChunksPage.tsx`

- [ ] **Step 1: 更新 ChunksPage.tsx**

完整替换文件内容：

```tsx
import { useState, useEffect, useCallback } from 'react'
import { DocList } from '@/components/DocList'
import { ChunkList } from '@/components/ChunkList'
import { DocEditDrawer } from '@/components/DocEditDrawer'
import { api } from '@/api/client'
import type { DocumentInfo } from '@/api/types'
import { useToast } from '@/hooks/use-toast'

export function ChunksPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null)
  const [editingDoc, setEditingDoc] = useState<DocumentInfo | null>(null)
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
      <aside className="w-[360px] shrink-0 flex flex-col min-h-0">
        <DocList
          documents={documents}
          loading={docsLoading}
          selectedDocId={selectedDocId}
          onSelect={setSelectedDocId}
          onDelete={handleDeleteDoc}
          onEdit={setEditingDoc}
          deletingDocId={deletingDocId}
        />
      </aside>
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <ChunkList docId={selectedDocId} />
      </main>
      <DocEditDrawer
        doc={editingDoc}
        open={editingDoc !== null}
        onClose={() => setEditingDoc(null)}
        onSaved={refreshDocuments}
      />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/apps/console/src/pages/ChunksPage.tsx
git commit -m "feat(console): wire DocEditDrawer into ChunksPage, widen sidebar to 360px"
```

---

### Task 7: 前端 — DocList 分页、搜索和编辑按钮

**Files:**
- Modify: `web/apps/console/src/components/DocList.tsx`

- [ ] **Step 1: 完整替换 DocList.tsx**

```tsx
import { useState, useMemo } from 'react'
import { Trash2, Loader2, Pencil, ChevronLeft, ChevronRight } from 'lucide-react'
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
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import type { DocumentInfo } from '@/api/types'

const PAGE_SIZE = 20

interface Props {
  documents: DocumentInfo[]
  loading: boolean
  selectedDocId: string | null
  onSelect: (docId: string) => void
  onDelete: (docId: string) => Promise<void>
  onEdit: (doc: DocumentInfo) => void
  deletingDocId: string | null
}

export function DocList({ documents, loading, selectedDocId, onSelect, onDelete, onEdit, deletingDocId }: Props) {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)

  const filtered = useMemo(() => {
    if (!query.trim()) return documents
    const q = query.toLowerCase()
    return documents.filter(
      d =>
        d.standard_no.toLowerCase().includes(q) ||
        d.doc_type.toLowerCase().includes(q) ||
        d.doc_id.toLowerCase().includes(q) ||
        (d.title || '').toLowerCase().includes(q),
    )
  }, [documents, query])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  function handleQueryChange(value: string) {
    setQuery(value)
    setPage(1)
  }

  return (
    <div className="flex flex-col h-full border-r border-border">
      <div className="p-3 border-b border-border">
        <Input
          placeholder="搜索文档..."
          value={query}
          onChange={e => handleQueryChange(e.target.value)}
          className="h-8 text-sm bg-secondary"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
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
            {paged.map(doc => {
              const isDeleting = deletingDocId === doc.doc_id
              return (
                <DocItem
                  key={doc.doc_id}
                  doc={doc}
                  selected={selectedDocId === doc.doc_id}
                  isDeleting={isDeleting}
                  onSelect={onSelect}
                  onDelete={onDelete}
                  onEdit={onEdit}
                />
              )
            })}
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="border-t border-border px-3 py-2 flex items-center justify-between text-xs text-muted-foreground">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-1 rounded hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="上一页"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span>第 {currentPage} / {totalPages} 页</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-1 rounded hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="下一页"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}

interface DocItemProps {
  doc: DocumentInfo
  selected: boolean
  isDeleting: boolean
  onSelect: (docId: string) => void
  onDelete: (docId: string) => Promise<void>
  onEdit: (doc: DocumentInfo) => void
}

function DocItem({ doc, selected, isDeleting, onSelect, onDelete, onEdit }: DocItemProps) {
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [hovered, setHovered] = useState(false)

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
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        onClick={() => onSelect(doc.doc_id)}
        className={`w-full text-left px-3 py-2 rounded-md transition-colors text-sm pr-14 ${
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

      {/* 编辑按钮 */}
      <button
        onClick={e => { e.stopPropagation(); onEdit(doc) }}
        className={`absolute right-7 top-1/2 -translate-y-1/2 p-1 rounded transition-opacity hover:bg-secondary ${hovered ? 'opacity-100' : 'opacity-0'}`}
        aria-label="编辑文档"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>

      {/* 删除按钮 */}
      <button
        onClick={e => { e.stopPropagation(); setOpen(true) }}
        disabled={isDeleting}
        className={`absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded transition-opacity hover:bg-destructive/10 hover:text-destructive disabled:opacity-50 ${hovered || isDeleting ? 'opacity-100' : 'opacity-0'}`}
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

- [ ] **Step 2: Commit**

```bash
git add web/apps/console/src/components/DocList.tsx
git commit -m "feat(console): add pagination, edit button, and title search to DocList"
```

---

### Task 8: 前端 — ChunkEditDrawer 补充只读元数据字段

**Files:**
- Modify: `web/apps/console/src/components/ChunkEditDrawer.tsx`

- [ ] **Step 1: 在 ChunkEditDrawer.tsx 中添加只读元数据分组**

在 `raw_content` 只读块之后（第 137 行 `</div>` 之后、外层 `</div>` 之前），追加：

```tsx
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
```

具体位置：在文件第 137 行（`)}` 结束 `raw_content` 条件渲染块）之后，第 138 行（`</div>` 关闭 form body）之前插入。

- [ ] **Step 2: Commit**

```bash
git add web/apps/console/src/components/ChunkEditDrawer.tsx
git commit -m "feat(console): add read-only doc metadata section to ChunkEditDrawer"
```

---

### Task 9: 手动验证

- [ ] **Step 1: 启动后端**

```bash
cd server && uv run python3 run.py
```

- [ ] **Step 2: 启动前端**

```bash
cd web && pnpm dev
```

- [ ] **Step 3: 验证 Doc 列表宽度**

打开 http://localhost:5173，确认左侧 Doc 列表宽度明显大于之前（约 360px），GB 标准标题可完整显示。

- [ ] **Step 4: 验证分页（需要 > 20 个文档时生效；文档少时分页控件隐藏属正常）**

若文档少于 20 条，分页控件不显示；在搜索框输入内容后，结果自动重置到第 1 页。

- [ ] **Step 5: 验证搜索含 title**

在搜索框输入文档标题中的关键词，确认能匹配到对应文档。

- [ ] **Step 6: 验证文档编辑**

1. 悬停在某个文档上，确认出现铅笔图标（编辑）和垃圾桶图标（删除）
2. 点击铅笔图标，右侧弹出抽屉
3. 修改 title 字段，点击保存
4. 确认 toast 显示「已保存」，列表刷新，标题已更新

- [ ] **Step 7: 验证 Chunk 编辑底部元数据**

1. 选中一个文档，点击任意 chunk 的编辑按钮
2. 滚动到编辑抽屉底部，确认「文档元数据（只读）」分组正确显示 doc_id、title、standard_no、doc_type

- [ ] **Step 8: 运行后端测试，确认无回归**

```bash
cd server && uv run pytest tests/api/documents/ -v
```

Expected: 全部 PASS
