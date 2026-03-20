# Upload SSE Real Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将文档上传接口从"假进度定时器"改为基于 SSE 的真实流水线进度推送，前端实时显示每个 parser 节点的开始/完成状态。

**Architecture:** 后端通过 LangGraph 的 `astream_events(version="v2")` 监听每个节点事件，使用 `event["metadata"]["langgraph_node"]` 过滤节点边界事件（比 `event["name"]` 更可靠）；`POST /api/documents` 改为返回 `StreamingResponse`，按 SSE 格式推送进度；前端用 `fetch` + `ReadableStream` 读流实时更新阶段状态，刷新页面后进度归零（不持久化）。

**Tech Stack:** Python FastAPI `StreamingResponse`、LangGraph `astream_events v2`、TypeScript `fetch` + `ReadableStream` + `TextDecoder`

---

## SSE 事件协议

后端推送的事件（每条格式：`data: <json>\n\n`）：

| type | 字段 | 说明 |
|------|------|------|
| `stage` | `stage: str`, `status: "active"\|"done"\|"error"` | 单个节点的进度 |
| `done` | `chunks_count: int` | 全部完成（含 KB 写入）|
| `error` | `message: str` | 出错 |

`stage` 值对应前端 `PIPELINE_STAGES` 的 `id`：`parse` / `clean` / `structure` / `slice` / `classify` / `escalate` / `enrich` / `transform` / `merge`

> **注意：** `escalate` 节点是条件执行的，若无低置信度 chunk 会跳过，该阶段保持 `pending`（灰色）属于正常现象。

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| Modify | `server/parser/graph.py` | 新增 `run_parser_workflow_stream` async generator |
| Modify | `server/api/documents/service.py` | 新增 `upload_document_stream`，import 移至文件顶部 |
| Modify | `server/api/documents/router.py` | `POST /api/documents` 改为 `StreamingResponse`，清理废弃 import |
| Modify | `server/tests/api/documents/test_service.py` | 删除过期测试，新增 stream 测试，保留其余三个测试 |
| Modify | `web/apps/console/src/api/client.ts` | `upload` 改为 SSE 流，清理废弃 import |
| Modify | `web/apps/console/src/pages/UploadPage.tsx` | 删除 localStorage + 定时器，接入真实进度 |

---

## Task 1: 在 graph.py 新增流式函数

**Files:**
- Modify: `server/parser/graph.py`

- [ ] **Step 1: 在文件顶部补充导入**

在 `server/parser/graph.py` 顶部现有 import 块末尾追加：

```python
from collections.abc import AsyncGenerator
```

- [ ] **Step 2: 在文件末尾新增 `run_parser_workflow_stream`**

```python
# 节点名集合，对应前端 PIPELINE_STAGES 的 id（去掉 _node 后缀）
_PIPELINE_NODE_NAMES = {
    "parse_node", "clean_node", "structure_node", "slice_node",
    "classify_node", "escalate_node", "enrich_node", "transform_node", "merge_node",
}


async def run_parser_workflow_stream(
    md_content: str,
    doc_metadata: dict,
    rules_dir: str,
    config: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """流式执行 parser workflow，每个节点开始/结束时 yield 进度事件。

    使用 metadata["langgraph_node"] 过滤节点边界事件（比 event["name"] 更可靠，
    可排除 LLM 调用、RunnableSequence 等子事件的干扰）。

    Yields:
        {"type": "stage", "stage": str, "status": "active" | "done"}
        {"type": "workflow_done", "chunks": list[DocumentChunk]}
    """
    initial_state = WorkflowState(
        md_content=md_content,
        doc_metadata=doc_metadata,
        config=config or {},
        rules_dir=rules_dir,
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )

    async for event in parser_graph.astream_events(initial_state, version="v2"):
        event_type = event.get("event", "")
        # 用 metadata.langgraph_node 定位节点边界（比 event["name"] 更可靠）
        node_name = event.get("metadata", {}).get("langgraph_node", "")

        if node_name not in _PIPELINE_NODE_NAMES:
            continue

        stage = node_name.removesuffix("_node")

        if event_type == "on_chain_start":
            yield {"type": "stage", "stage": stage, "status": "active"}

        elif event_type == "on_chain_end":
            yield {"type": "stage", "stage": stage, "status": "done"}

            if node_name == "merge_node":
                output = event.get("data", {}).get("output") or {}
                final_chunks = output.get("final_chunks", [])
                yield {"type": "workflow_done", "chunks": final_chunks}
```

> **注意：** `async def` + `yield` 会使函数成为 async generator function，`-> AsyncGenerator[...]` 的标注仅作文档用途，不影响运行时行为，但某些版本的 mypy 会警告；如遇 CI 报错可移除该标注。

- [ ] **Step 3: 提交**

```bash
git add server/parser/graph.py
git commit -m "feat(parser): add run_parser_workflow_stream for SSE progress"
```

---

## Task 2: service.py 新增 `upload_document_stream`

**Files:**
- Modify: `server/api/documents/service.py`

- [ ] **Step 1: 在文件顶部补充导入**

在现有 import 块末尾追加：

```python
import json
from collections.abc import AsyncGenerator
from parser.graph import run_parser_workflow_stream
```

- [ ] **Step 2: 在 `DocumentsService` 类中新增 `upload_document_stream` 方法**

```python
@staticmethod
async def upload_document_stream(
    file_content: bytes,
    filename: str,
) -> AsyncGenerator[str, None]:
    """流式上传文档，yield SSE 格式字符串（每条：data: <json>\n\n）。"""
    try:
        md_content = file_content.decode("utf-8")
    except UnicodeDecodeError:
        yield f"data: {json.dumps({'type': 'error', 'message': '文件编码错误，请确保文件为 UTF-8 编码'})}\n\n"
        return

    doc_id = os.path.splitext(filename)[0]
    doc_metadata = {
        "doc_id": doc_id,
        "standard_no": doc_id,
        "doc_type": "standard",
    }
    rules_dir = str(Path(__file__).parent.parent.parent / "parser" / "rules")

    try:
        async for event in run_parser_workflow_stream(
            md_content=md_content,
            doc_metadata=doc_metadata,
            rules_dir=rules_dir,
        ):
            if event["type"] == "workflow_done":
                chunks = event["chunks"]
                if chunks:
                    await chroma_writer.write(chunks, doc_metadata)
                    fts_writer.write(chunks, doc_metadata)
                yield f"data: {json.dumps({'type': 'done', 'chunks_count': len(chunks)})}\n\n"
            else:
                yield f"data: {json.dumps(event)}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
```

- [ ] **Step 3: 提交**

```bash
git add server/api/documents/service.py
git commit -m "feat(documents): add upload_document_stream SSE generator"
```

---

## Task 3: router.py 改为 StreamingResponse

**Files:**
- Modify: `server/api/documents/router.py`

- [ ] **Step 1: 更新 import 块**

将原来的 import 替换为（删除不再使用的 `UploadDocumentResponse`、`Optional`、`Form` 参数中的 `chunk_size`/`chunk_overlap`）：

```python
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from api.documents.models import DocumentsListResponse, DocumentInfo
from api.documents.service import DocumentsService
```

- [ ] **Step 2: 将上传路由替换为 StreamingResponse 版本**

删除原来的 `upload_document` 函数，替换为：

```python
@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    strategy: str = Form("text"),
):
    content = await file.read()
    return StreamingResponse(
        DocumentsService.upload_document_stream(
            file_content=content,
            filename=file.filename or "unknown",
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 3: 提交**

```bash
git add server/api/documents/router.py
git commit -m "feat(documents): switch upload endpoint to SSE StreamingResponse"
```

---

## Task 4: 更新测试文件

**Files:**
- Modify: `server/tests/api/documents/test_service.py`

- [ ] **Step 1: 修正现有三个测试的 patch 路径**

现有三个测试（保留）使用了错误的 `app.api.documents.service.*` 前缀，正确路径是 `api.documents.service.*`。将文件中所有 `"app.api.documents.service.` 替换为 `"api.documents.service.`（共 4 处）。

- [ ] **Step 2: 删除过期测试，新增 stream 测试**

**只删除** `test_upload_document_returns_501` 函数（约第 65–71 行）。

在文件顶部 import 行做如下修改：
- 将 `from unittest.mock import MagicMock, patch` 改为 `from unittest.mock import AsyncMock, MagicMock, patch`
- 在最顶部新增 `import json`

在文件末尾追加以下两个新测试：

```python
@pytest.mark.asyncio
async def test_upload_document_stream_yields_stage_events():
    """upload_document_stream 应依次 yield stage 事件和 done 事件，并写入 KB"""
    from api.documents.service import DocumentsService

    fake_events = [
        {"type": "stage", "stage": "parse", "status": "active"},
        {"type": "stage", "stage": "parse", "status": "done"},
        {"type": "workflow_done", "chunks": [{"chunk_id": "abc"}]},
    ]

    async def fake_stream(*args, **kwargs):
        for e in fake_events:
            yield e

    with patch("api.documents.service.run_parser_workflow_stream", fake_stream), \
         patch("api.documents.service.chroma_writer") as mock_chroma, \
         patch("api.documents.service.fts_writer") as mock_fts:
        mock_chroma.write = AsyncMock()

        results = []
        async for line in DocumentsService.upload_document_stream(b"# test", "test.md"):
            results.append(line)

    assert results[0] == f"data: {json.dumps({'type': 'stage', 'stage': 'parse', 'status': 'active'})}\n\n"
    assert results[1] == f"data: {json.dumps({'type': 'stage', 'stage': 'parse', 'status': 'done'})}\n\n"
    assert results[2] == f"data: {json.dumps({'type': 'done', 'chunks_count': 1})}\n\n"
    mock_chroma.write.assert_called_once()
    mock_fts.write.assert_called_once()


@pytest.mark.asyncio
async def test_upload_document_stream_utf8_error():
    """非 UTF-8 文件应 yield error 事件并直接返回"""
    from api.documents.service import DocumentsService

    results = []
    async for line in DocumentsService.upload_document_stream(b"\xff\xfe", "bad.md"):
        results.append(line)

    assert len(results) == 1
    payload = json.loads(results[0].removeprefix("data: ").rstrip())
    assert payload["type"] == "error"
    assert "UTF-8" in payload["message"]
```

- [ ] **Step 2: 运行测试，确认通过**

```bash
cd server
uv run pytest tests/api/documents/test_service.py -v
```

期望：5 个测试全部 PASS

- [ ] **Step 3: 提交**

```bash
git add server/tests/api/documents/test_service.py
git commit -m "test(documents): replace upload_501 test with SSE stream tests"
```

---

## Task 5: 前端 api/client.ts 改为 SSE 流式上传

**Files:**
- Modify: `web/apps/console/src/api/client.ts`

- [ ] **Step 1: 从 import 列表移除 `UploadDocumentResponse`**

将文件顶部 import 从：

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

改为：

```typescript
import type {
  Chunk,
  ChunksListResponse,
  DocumentInfo,
  KBStats,
  UpdateChunkPayload,
  AgentChatRequest,
  AgentResponse,
} from './types'
```

- [ ] **Step 2: 替换 `upload` 方法**

```typescript
upload: async (
  file: File,
  onProgress: (stage: string, status: 'active' | 'done' | 'error') => void,
): Promise<{ chunks_count: number }> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('strategy', 'text')

  const res = await fetch(`${BASE}/documents`, { method: 'POST', body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE 事件以 \n\n 分隔
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const dataLine = part.split('\n').find(l => l.startsWith('data: '))
      if (!dataLine) continue
      const payload = JSON.parse(dataLine.slice(6))

      if (payload.type === 'stage') {
        onProgress(payload.stage, payload.status)
      } else if (payload.type === 'done') {
        return { chunks_count: payload.chunks_count }
      } else if (payload.type === 'error') {
        throw new Error(payload.message)
      }
    }
  }

  throw new Error('上传流意外结束')
},
```

- [ ] **Step 3: 同步清理 `types.ts`**

检查 `web/apps/console/src/api/types.ts`，若 `UploadDocumentResponse` 没有其他引用，将其从文件中删除。

- [ ] **Step 4: 提交**

```bash
git add web/apps/console/src/api/client.ts web/apps/console/src/api/types.ts
git commit -m "feat(console): update upload api to consume SSE stream"
```

---

## Task 6: UploadPage.tsx 接入真实进度

**Files:**
- Modify: `web/apps/console/src/pages/UploadPage.tsx`

- [ ] **Step 1: 完整替换文件内容**

```typescript
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
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/console/src/pages/UploadPage.tsx
git commit -m "feat(console): wire real SSE progress to UploadPage, remove localStorage and timer"
```

---

## Task 7: 端到端验证

- [ ] **Step 1: 后端单元测试全量**

```bash
cd server
uv run pytest tests/ -v
```

期望：所有测试通过

- [ ] **Step 2: 启动后端**

```bash
cd server
uv run python3 run.py
```

- [ ] **Step 3: 启动前端**

```bash
cd web
pnpm dev
```

- [ ] **Step 4: 手动测试**

1. 打开 `http://localhost:5173` → 上传页
2. 选择一个 `.md` 文件，点击"上传并入库"
3. 观察右侧进度面板：每个阶段应依次出现转圈（active）→ 绿勾（done）
4. `escalate` 阶段可能保持灰色（被跳过），属于正常现象
5. 完成后 toast 显示实际 chunks 数量
6. 刷新页面 → 进度面板回到空白状态（正确行为）
