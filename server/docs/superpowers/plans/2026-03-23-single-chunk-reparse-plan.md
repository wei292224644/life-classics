# Single Chunk Re-parse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `POST /api/chunks/{chunk_id}/reparse` 接口，支持对单个 chunk 重跑 transform_node → merge_node，将转写错误的内容重新生成。

**Architecture:** 在 `ChunksService` 新增 `reparse_chunk` 异步方法，复用现有 `transform_node` + `merge_node`，重建 `ClassifiedChunk` 后依次调用，最后通过 upsert 写回 ChromaDB + FTS。

**Tech Stack:** FastAPI / Pydantic / ChromaDB / LangGraph nodes (transform_node, merge_node)

---

## File Structure

```
server/
  api/chunks/
    service.py        # 新增 ChunksService.reparse_chunk()
    router.py         # 新增 POST /{chunk_id}/reparse
  tests/api/chunks/
    test_service.py   # 新增 reparse_chunk 测试
```

---

## Task 1: 新增 ChunksService.reparse_chunk()

**Files:**
- Modify: `server/api/chunks/service.py` (imports + end of class)

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_reparse_chunk_rebuilds_classified_and_reruns_transform():
    """reparse_chunk 应重建 ClassifiedChunk，重跑 transform + merge，upsert 新 chunk"""
    old_meta = {
        "doc_id": "d1",
        "semantic_type": "scope",
        "structure_type": "paragraph",
        "section_path": "1|1.1",
        "standard_no": "GB 2762",
        "doc_type": "food",
        "raw_content": "原始 markdown",
        "segment_raw_content": "这是 segment 原始内容",
        "transform_strategy": "plain_embed",
        "prompt_template": "请转化：\n",
        "cross_refs": [],
        "failed_table_refs": [],
    }
    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1"],
        "documents": ["旧的规范化内容"],
        "metadatas": [old_meta],
    }
    fake_embedding = [[0.1, 0.2]]

    with patch("api.chunks.service.get_collection", return_value=mock_col), \
         patch("api.chunks.service.embed_batch", AsyncMock(return_value=fake_embedding)), \
         patch("api.chunks.service.fts_writer") as mock_fts, \
         patch("parser.nodes.transform_node.transform_node", new_callable=AsyncMock) as mock_transform, \
         patch("parser.nodes.merge_node.merge_node") as mock_merge, \
         patch("config.settings.RULES_DIR", "/rules"):
        mock_transform.return_value = {
            "final_chunks": [{
                "chunk_id": "c1",
                "content": "新内容",
                "raw_content": "原始 markdown",
                "structure_type": "paragraph",
                "semantic_type": "scope",
                "section_path": ["1", "1.1"],
                "doc_metadata": {"doc_id": "d1", "standard_no": "GB 2762", "doc_type": "food"},
                "meta": {"segment_raw_content": "这是 segment 原始内容"},
            }],
            "errors": [],
        }
        mock_merge.return_value = {
            "final_chunks": mock_transform.return_value["final_chunks"],
            "doc_metadata": {"doc_id": "d1", "standard_no": "GB 2762", "doc_type": "food"},
        }

        from api.chunks.service import ChunksService
        result = await ChunksService.reparse_chunk("c1")

    # 验证 upsert 写入新内容
    upsert_kwargs = mock_col.upsert.call_args.kwargs
    assert upsert_kwargs["ids"] == ["c1"]
    assert upsert_kwargs["documents"] == ["新内容"]
    assert upsert_kwargs["embeddings"] == fake_embedding
    # 验证 transform_node 接收到的 TypedSegment.content 来自 segment_raw_content
    call_args = mock_transform.call_args
    passed_state = call_args[0][0]
    passed_classified = passed_state.classified_chunks[0]
    assert passed_classified["segments"][0]["content"] == "这是 segment 原始内容"
    # 验证 FTS 也被更新
    mock_fts.write.assert_called_once()
    assert result["id"] == "c1"
    assert result["content"] == "新内容"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && uv run pytest tests/api/chunks/test_service.py::test_reparse_chunk_rebuilds_classified_and_reruns_transform -v`
Expected: FAIL (AttributeError: 'ChunksService' has no attribute 'reparse_chunk')

- [ ] **Step 3: Add imports to service.py**

在文件顶部 import 区追加：
```python
from parser.models import ClassifiedChunk, RawChunk, TypedSegment, WorkflowState
from parser.nodes.transform_node import transform_node
from parser.nodes.merge_node import merge_node
from config import settings
```

- [ ] **Step 4: Add reparse_chunk method to ChunksService**

在 `ChunksService` 类末尾添加：

```python
@staticmethod
async def reparse_chunk(chunk_id: str) -> dict[str, Any]:
    """对单个 chunk 重跑 transform → merge，结果写回 ChromaDB + FTS。"""
    col = get_collection()
    existing = col.get(ids=[chunk_id], include=["documents", "metadatas"])
    if not (existing.get("ids") or []):
        raise ValueError(f"chunk {chunk_id} not found")

    docs = existing.get("documents") or []
    metas = existing.get("metadatas") or []
    old_content = docs[0] if docs else ""
    meta = metas[0]

    doc_id = meta.get("doc_id", "")
    standard_no = meta.get("standard_no", "")
    doc_type = meta.get("doc_type", "")
    raw_content = meta.get("raw_content", "")
    segment_raw_content = meta.get("segment_raw_content", old_content)
    structure_type = meta.get("structure_type", "paragraph")
    semantic_type = meta.get("semantic_type", "scope")
    transform_strategy = meta.get("transform_strategy", "plain_embed")
    prompt_template = meta.get("prompt_template", "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n")
    cross_refs = meta.get("cross_refs", [])
    failed_table_refs = meta.get("failed_table_refs", [])

    # 重建 TypedSegment
    typed_segment = TypedSegment(
        content=segment_raw_content,
        structure_type=structure_type,
        semantic_type=semantic_type,
        transform_params={"strategy": transform_strategy, "prompt_template": prompt_template},
        confidence=1.0,
        escalated=False,
        cross_refs=cross_refs,
        ref_context="",
        failed_table_refs=failed_table_refs,
    )

    # 重建 ClassifiedChunk
    raw_chunk = RawChunk(
        content=raw_content,
        section_path=meta.get("section_path", "").split("|"),
        char_count=len(raw_content),
    )
    classified = ClassifiedChunk(
        raw_chunk=raw_chunk,
        segments=[typed_segment],
        has_unknown=False,
    )

    doc_metadata = {
        "doc_id": doc_id,
        "standard_no": standard_no,
        "doc_type": doc_type,
    }

    # 重跑 transform → merge
    transform_result = await transform_node(
        WorkflowState(
            md_content="",
            doc_metadata=doc_metadata,
            config={},
            rules_dir=settings.RULES_DIR,
            raw_chunks=[raw_chunk],
            classified_chunks=[classified],
            final_chunks=[],
            errors=[],
        )
    )
    merge_result = merge_node({
        "final_chunks": transform_result["final_chunks"],
        "doc_metadata": doc_metadata,
    })
    final_chunks = merge_result["final_chunks"]

    if not final_chunks:
        raise ValueError(f"reparse produced no chunks for {chunk_id}")

    # 取第一个 chunk（reparse 单 chunk 场景下应为 1 个）
    new_chunk = final_chunks[0]
    new_content = new_chunk["content"]

    # 重新 embed 并 upsert
    embeddings = await embed_batch([new_content])
    new_section_path_pipe = "|".join(new_chunk["section_path"])
    new_meta = {
        **meta,
        "semantic_type": new_chunk["semantic_type"],
        "section_path": new_section_path_pipe,
    }
    col.upsert(
        ids=[chunk_id],
        documents=[new_content],
        embeddings=embeddings,
        metadatas=[new_meta],
    )

    # 同步更新 FTS
    fts_writer.init_db()
    fts_doc_meta = {
        "doc_id": doc_id,
        "standard_no": standard_no,
        "doc_type": doc_type,
    }
    fts_chunk = {
        "chunk_id": chunk_id,
        "content": new_content,
        "semantic_type": new_chunk["semantic_type"],
        "section_path": new_chunk["section_path"],
        "raw_content": raw_content,
        "doc_metadata": {},
        "meta": new_chunk.get("meta", {}),
    }
    fts_writer.write([fts_chunk], fts_doc_meta)

    return {"id": chunk_id, "content": new_content, "metadata": new_meta}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd server && uv run pytest tests/api/chunks/test_service.py::test_reparse_chunk_rebuilds_classified_and_reruns_transform -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/api/chunks/service.py
git commit -m "feat(api/chunks): add ChunksService.reparse_chunk() method"
```

---

## Task 3: 新增 POST /{chunk_id}/reparse 路由

**Files:**
- Modify: `server/api/chunks/router.py:5` (import ReparseResponse), `server/api/chunks/router.py:65` (追加路由)

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_reparse_endpoint_returns_200():
    with patch("api.chunks.router.ChunksService.reparse_chunk", new_callable=AsyncMock) as mock_reparse:
        mock_reparse.return_value = {
            "id": "c1",
            "content": "新内容",
            "metadata": {"semantic_type": "scope"},
        }
        from fastapi.testclient import TestClient
        from main import app  # 需要确认 main 路径
        # 或直接构造请求
```

（router 层测试也可以通过集成测试覆盖，或简化为只测 service 层，本任务跳过 router 单独测试）

- [ ] **Step 2: 添加 import ReparseResponse**

```python
from api.chunks.models import ChunksListResponse, ChunkResponse, UpdateChunkRequest, ReparseResponse
```

- [ ] **Step 3: 添加路由**

```python
@router.post("/{chunk_id}/reparse", response_model=ChunkResponse)
async def reparse_chunk(chunk_id: str):
    try:
        result = await ChunksService.reparse_chunk(chunk_id)
        return ChunkResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: 验证语法正确（import 不报错）**

Run: `cd server && uv run python -c "from api.chunks.router import router; print('OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add server/api/chunks/router.py
git commit -m "feat(api/chunks): add POST /{chunk_id}/reparse endpoint"
```

---

## Task 4: 补充异常路径测试

**Files:**
- Modify: `server/tests/api/chunks/test_service.py`

- [ ] **Step 1: Write tests for error cases**

```python
@pytest.mark.asyncio
async def test_reparse_chunk_not_found():
    """chunk 不存在时抛出 ValueError(404)"""
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": [], "documents": [], "metadatas": []}

    with patch("api.chunks.service.get_collection", return_value=mock_col):
        from api.chunks.service import ChunksService
        with pytest.raises(ValueError, match="chunk not found"):
            await ChunksService.reparse_chunk("nonexistent")


@pytest.mark.asyncio
async def test_reparse_chunk_transform_returns_empty():
    """transform 产出为空时抛出 ValueError"""
    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1"],
        "documents": ["旧内容"],
        "metadatas": [{
            "doc_id": "d1", "semantic_type": "scope", "structure_type": "paragraph",
            "section_path": "1|1.1", "standard_no": "GB 2762", "doc_type": "food",
            "raw_content": "原始", "segment_raw_content": "seg原始",
            "transform_strategy": "plain_embed", "prompt_template": "",
            "cross_refs": [], "failed_table_refs": [],
        }],
    }

    with patch("api.chunks.service.get_collection", return_value=mock_col), \
         patch("parser.nodes.transform_node.transform_node", new_callable=AsyncMock) as mock_transform, \
         patch("parser.nodes.merge_node.merge_node"), \
         patch("config.settings.RULES_DIR", "/rules"):
        mock_transform.return_value = {"final_chunks": [], "errors": []}

        from api.chunks.service import ChunksService
        with pytest.raises(ValueError, match="reparse produced no chunks"):
            await ChunksService.reparse_chunk("c1")
```

- [ ] **Step 2: Run tests**

Run: `cd server && uv run pytest tests/api/chunks/test_service.py::test_reparse_chunk_not_found tests/api/chunks/test_service.py::test_reparse_chunk_transform_returns_empty -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add server/tests/api/chunks/test_service.py
git commit -m "test(api/chunks): add reparse_chunk error path tests"
```

---

## 依赖关系

```
Task 1 → Task 2 → Task 3 → Task 4
```

## 快速验证命令

```bash
cd server
uv run pytest tests/api/chunks/test_service.py -v
```
