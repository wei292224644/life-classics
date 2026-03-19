# 清空知识库功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Admin UI 顶部栏添加"清空知识库"按钮，带二次确认弹窗，成功后刷新界面状态。

**Architecture:** 后端新增 `DELETE /api/documents/clear` → 前端 API client 加方法 → App.tsx 加按钮 + AlertDialog → 成功后重置状态。

**Tech Stack:** Python/FastAPI, React/Vite, shadcn/ui (AlertDialog, Button), TypeScript

---

## 文件变更总览

| 文件 | 变更 |
|------|------|
| `agent-server/app/core/kb/writer/fts_writer.py` | 新增 `clear_all()` 函数 |
| `agent-server/app/api/documents/service.py` | 新增 `DocumentsService.clear_all()` |
| `agent-server/app/api/documents/router.py` | 新增 `DELETE /clear` 端点（放在 `/{doc_id}` **之前**） |
| `agent-server/admin/src/api/client.ts` | `documents.clearAll` 方法 |
| `agent-server/admin/src/App.tsx` | 顶部栏加按钮 + AlertDialog |

---

## Task 1: 后端 FTS — 添加 `fts_writer.clear_all()`

**File:**
- Modify: `agent-server/app/core/kb/writer/fts_writer.py`

- [ ] **Step 1: 在 `fts_writer.py` 末尾添加 `clear_all()` 函数**

FTS5 外部内容表（`content=chunks`）需要用 `INSERT ... VALUES('delete', ...)` 同步删除。直接 `DELETE FROM chunks_fts` 无效。最简洁的做法是删除重建表。

在 `fts_writer.py` 末尾添加：

```python
def clear_all(db_path: Optional[str] = None) -> int:
    """
    清空 chunks 和 chunks_fts 表，返回删除的行数。
    FTS5 外部内容表需要先从 FTS 索引删除，再清空基础表。
    """
    path = _get_db_path(db_path)
    with sqlite3.connect(path) as conn:
        # 获取所有行用于 FTS 索引同步
        rows = conn.execute(
            "SELECT rowid, chunk_id, tokenized_content FROM chunks"
        ).fetchall()

        for rowid, chunk_id, tokenized_content in rows:
            conn.execute(
                "INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, tokenized_content)"
                " VALUES('delete', ?, ?, ?)",
                (rowid, chunk_id, tokenized_content),
            )

        deleted = conn.execute("DELETE FROM chunks").rowcount
        conn.commit()
    return deleted
```

- [ ] **Step 2: 提交**

```bash
git add agent-server/app/core/kb/writer/fts_writer.py
git commit -m "feat(fts): add clear_all() function"
```

---

## Task 2: 后端 Documents Service + Router — 添加 `clear_all` 端点

**Files:**
- Modify: `agent-server/app/api/documents/service.py`
- Modify: `agent-server/app/api/documents/router.py`

**前置依赖:** Task 1 完成

- [ ] **Step 1: 在 `DocumentsService` 添加 `clear_all` 静态方法**

在 `agent-server/app/api/documents/service.py` 的 `DocumentsService` 类末尾添加：

```python
@staticmethod
def clear_all() -> dict[str, Any]:
    """
    清空所有文档和 chunks（ChromaDB + FTS）。
    Returns:
        {
            "status": "success",
            "deleted_documents": int,
            "deleted_chunks": int,
        }
    """
    # 获取删除前的统计
    collection = get_collection()
    all_results = collection.get(include=["metadatas"])
    metadatas = all_results.get("metadatas") or []
    doc_ids = {m.get("doc_id") for m in metadatas if m.get("doc_id")}
    total_chunks = len(all_results.get("ids") or [])

    # 清空 ChromaDB
    collection.delete(where={})

    # 清空 FTS
    from app.core.kb.writer import fts_writer
    fts_writer.clear_all()

    return {
        "status": "success",
        "deleted_documents": len(doc_ids),
        "deleted_chunks": total_chunks,
    }
```

- [ ] **Step 2: 在 `router.py` 添加 `DELETE /clear` 端点（注意：放在 `/{doc_id}` 之前）**

打开 `agent-server/app/api/documents/router.py`，将 `@router.delete("/{doc_id}")` 整段（从第41行到第46行）复制到文件末尾，然后在原位置用 `@router.delete("/clear")` 替换，或直接按以下顺序重写：

删除线部分是旧的 `/{doc_id}` 端点，**新增的 `/clear` 端点放在它前面**：

```python
# 新增：清空所有文档
@router.delete("/clear")
def clear_all_documents():
    try:
        return DocumentsService.clear_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 原有的：删除指定文档（保持不动，但要确认它在 /clear 之后）
@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    try:
        return DocumentsService.delete_document(doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**关键：FastAPI 按顺序匹配路由，`/clear` 必须在 `/{doc_id}` 之前，否则 `clear` 会被当作 doc_id。**

- [ ] **Step 3: 验证后端**

```bash
cd agent-server && uv run python -c "from app.api.documents.router import router; print('OK')"
```

- [ ] **Step 4: 提交**

```bash
git add agent-server/app/api/documents/router.py agent-server/app/api/documents/service.py
git commit -m "feat(api): add DELETE /documents/clear endpoint"
```

---

## Task 3: 前端 API Client — 添加 `clearAll` 方法

**File:**
- Modify: `agent-server/admin/src/api/client.ts`

- [ ] **Step 1: 在 `documents` 对象末尾添加 `clearAll` 方法**

在 `documents` 对象的 `delete` 方法之后（`clearAll` 之前）添加：

```ts
clearAll: () =>
  request<{
    status: string
    deleted_documents: number
    deleted_chunks: number
  }>('/documents/clear', { method: 'DELETE' }),
```

- [ ] **Step 2: 提交**

```bash
git add agent-server/admin/src/api/client.ts
git commit -m "feat(admin): add clearAll API method"
```

---

## Task 4: App.tsx — 添加清空按钮和确认弹窗

**File:**
- Modify: `agent-server/admin/src/App.tsx`

**前置依赖:** Task 2 和 Task 3 完成

需要添加的 import（在现有 import 之后追加）：

```ts
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { buttonVariants } from '@/components/ui/button'
import { useState } from 'react'
import { useToast } from '@/hooks/use-toast'
```

- [ ] **Step 1: 添加 `useState` 和 `useToast`**

在 `App` 组件内，在 `useEffect` 之后添加：

```ts
const [clearOpen, setClearOpen] = useState(false)
const [clearing, setClearing] = useState(false)
const { toast } = useToast()
```

- [ ] **Step 2: 在顶部栏 stats div 闭合标签后添加 AlertDialog**

在 header 的 stats div 闭合标签后（`})}` 之后）添加：

```tsx
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
            toast({
              description: `已清空 ${result.deleted_documents} 个文档，${result.deleted_chunks} 个 chunks`,
            })
            setDocuments([])
            setSelectedDocId(null)
            setDocsLoading(false)
            api.kb.stats().then(setStats).catch(() => {})
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
```

- [ ] **Step 3: 验证前端构建**

```bash
cd agent-server/admin && npm run build 2>&1 | tail -20
```

- [ ] **Step 4: 提交**

```bash
git add agent-server/admin/src/App.tsx
git commit -m "feat(admin): add clear all button with confirmation dialog"
```
