# 国家标准 RAG 重构 — 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 PDF 解析改为 MinerU 本地服务调用，采用按标题的粗粒度切分替代 LLM 动态切分，并增加 Neo4j 文档-块存储；收窄为国家标准 RAG 主链路。

**Architecture:** PDF 上传后经 MinerU 服务得到 MD → 按 `##`/`###` 标题切分为 chunk → 同时写入 Chroma 与 Neo4j；不再调用 convert_to_structured；可选保留 MD 文件导入与 text 策略。

**Tech Stack:** FastAPI, MinerU（本地 HTTP 服务）, ChromaDB, Neo4j（neo4j 驱动）, 现有 DocumentChunk/VectorStore。

**设计文档:** `docs/plans/2026-03-02-national-standard-rag-refactor-design.md`

---

## 阶段一：配置与 MinerU 适配器

### Task 1: 增加 MinerU 与 Neo4j 配置项

**Files:**
- Modify: `app/core/config.py`

**Step 1: 在 Settings 中增加配置**

在 `Settings` 类中（约第 55 行后）增加：

```python
# MinerU 服务配置（本地 Docker 等）
MINERU_SERVICE_URL: str = "http://localhost:8000"  # mineru-api 默认端口
MINERU_REQUEST_TIMEOUT: int = 300  # PDF 解析可能较久

# Neo4j 配置
NEO4J_URI: str = "bolt://localhost:7687"
NEO4J_USER: str = "neo4j"
NEO4J_PASSWORD: str = "neo4j"
```

**Step 2: 确认无语法错误**

Run: `python -c "from app.core.config import settings; print(settings.MINERU_SERVICE_URL, settings.NEO4J_URI)"`  
Expected: 打印默认 URL。

**Step 3: Commit**

```bash
git add app/core/config.py
git commit -m "config: add MINERU and NEO4J settings"
```

---

### Task 2: 实现 MinerU 适配器（调用本地服务）

**Files:**
- Create: `app/core/pdf/__init__.py`（空或导出）
- Create: `app/core/pdf/mineru_adapter.py`
- Test: `tests/core/pdf/test_mineru_adapter.py`（可选，mock 请求）

**Step 1: 新建 PDF 模块与适配器骨架**

`app/core/pdf/__init__.py`:

```python
from app.core.pdf.mineru_adapter import pdf_to_markdown

__all__ = ["pdf_to_markdown"]
```

`app/core/pdf/mineru_adapter.py`:

```python
"""
MinerU 本地服务适配器：将 PDF 转为 Markdown。
调用方需已部署 mineru-api（如 Docker），本模块仅做 HTTP 调用。
"""
import requests
from pathlib import Path
from typing import Optional

from app.core.config import settings


def pdf_to_markdown(
    pdf_path: str,
    service_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """
    调用 MinerU 本地服务，将 PDF 转为 Markdown 文本。

    Args:
        pdf_path: 本地 PDF 文件路径
        service_url: MinerU API 根地址，默认从 settings 读取
        timeout: 请求超时秒数，默认从 settings 读取

    Returns:
        解析得到的 Markdown 字符串；失败时抛出或返回空字符串（由实现决定）
    """
    url = (service_url or settings.MINERU_SERVICE_URL).rstrip("/")
    # 假设 mineru-api 提供 POST /convert 或 /parse，上传文件后返回 MD 或任务 ID
    # 此处按「上传文件并同步返回 MD」的常见形态实现；若实际为异步，再拆为 poll 逻辑
    with open(pdf_path, "rb") as f:
        files = {"file": (Path(pdf_path).name, f, "application/pdf")}
        r = requests.post(
            f"{url}/convert",
            files=files,
            timeout=timeout or settings.MINERU_REQUEST_TIMEOUT,
        )
    r.raise_for_status()
    data = r.json()
    # 按实际 API 响应结构调整，常见为 {"markdown": "..."} 或 {"content": "..."}
    return data.get("markdown", data.get("content", ""))
```

若实际 MinerU API 为「上传后返回 job_id，再 GET /result/{id} 取 MD」，则需改为两步；此处先按同步返回 MD 的形态写，后续 Task 可再调整。

**Step 2: 确认模块可导入**

Run: `python -c "from app.core.pdf import pdf_to_markdown; print(pdf_to_markdown.__doc__)"`  
Expected: 打印 docstring。

**Step 3: Commit**

```bash
git add app/core/pdf/
git commit -m "feat(pdf): add MinerU adapter for PDF to Markdown"
```

---

## 阶段二：按标题的粗粒度切分

### Task 3: 实现按标题切分（MD 字符串 → List[DocumentChunk]）

**Files:**
- Modify: `app/core/kb/strategy/heading_strategy.py`
- Test: `tests/core/kb/strategy/test_heading_strategy.py`

**Step 1: 写失败用例**

在 `tests/core/kb/strategy/test_heading_strategy.py` 中：

```python
import pytest
from app.core.document_chunk import DocumentChunk, ContentType
from app.core.kb.strategy.heading_strategy import split_heading_from_markdown


def test_heading_split_single_section():
    md = "## 适用范围\n\n本标准适用于食品添加剂。"
    chunks = split_heading_from_markdown(
        md, doc_id="d1", doc_title="test", source="test.md"
    )
    assert len(chunks) >= 1
    assert chunks[0].section_path
    assert "适用范围" in chunks[0].section_path or "适用范围" in chunks[0].content
```

**Step 2: 运行测试确认失败**

Run: `pytest tests/core/kb/strategy/test_heading_strategy.py -v`  
Expected: FAIL（如 split_heading_from_markdown 未定义或行为不符）。

**Step 3: 实现 split_heading_from_markdown**

在 `app/core/kb/strategy/heading_strategy.py` 中：

- 实现 `split_heading_from_markdown(markdown_content: str, doc_id: str, doc_title: str, source: str, markdown_id: Optional[str] = None) -> List[DocumentChunk]`。
- 规则：按 `^#{1,6}\s+.+` 识别标题，从当前标题到下一个同级或更高级标题之间的内容为一个 chunk；第一个块可为标题前无标题的导语（若有）；`section_path` 为当前标题层级列表；`content_type` 统一 `ContentType.NOTE` 或 `ContentType.GENERAL_RULE`；`content` 为该段落的纯文本或保留的 Markdown 字符串（与现有 `DocumentChunk.to_documents()` 兼容，即可转为 page_content 的字符串）。
- 使用 `DocumentChunk` 现有构造函数，传入 `doc_id`, `doc_title`, `section_path`, `content_type`, `content`, `meta={"source": source}`, `markdown_id=markdown_id or doc_id`。

**Step 4: 运行测试通过**

Run: `pytest tests/core/kb/strategy/test_heading_strategy.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/strategy/heading_strategy.py tests/core/kb/strategy/test_heading_strategy.py
git commit -m "feat(kb): heading-based chunking from markdown string"
```

---

### Task 4: 导出并接入 kb 的「PDF → MD → 切分」流水线

**Files:**
- Modify: `app/core/kb/__init__.py`
- Modify: `app/core/kb/imports/import_pdf.py`（可选：保留原 import_pdf 供 .md 路径或废弃）

**Step 1: 在 kb 中增加「仅 PDF → MD → heading 切分」路径**

- 在 `app/core/kb/__init__.py` 中：
  - 新增 `import_pdf_via_mineru(file_path: str, original_filename: str = None, **kwargs) -> List[DocumentChunk]`：
    - 调用 `from app.core.pdf import pdf_to_markdown` 得到 `md_content`；
    - 生成 `doc_id`（如 uuid）、`doc_title`（来自 original_filename stem）；
    - 调用 `split_heading_from_markdown(md_content, doc_id, doc_title, source=original_filename or Path(file_path).name)` 得到 chunks；
    - 可选：将 MD 写入 `markdown_db`（与现有 import_markdown 一致），便于调试；
    - 不调用 `convert_to_structured`；
    - 调用 `vector_store_manager.add_chunks(chunks)`；
    - 返回 chunks。
  - 在 `import_file_step` 中：当 `file_ext == ".pdf"` 时，改为调用 `import_pdf_via_mineru(...)` 并 return，不再走 `import_pdf` + pre-parse + `split_step`。
  - 保留 `file_ext in [".md", ".markdown"]` 与 `.txt` 的原有逻辑；对 `.md` 可仍用现有 `import_markdown` + `split_step(..., "text")` 或后续增加 heading 选项。

**Step 2: 运行现有导入相关测试或手动验证**

Run: 若有 `tests/` 下对 `import_file_step` 的测试则执行；若无则手动用一小份 PDF 或 mock MinerU 响应验证 `import_pdf_via_mineru` 返回 chunks 且 Chroma 有数据。  
Expected: 无回归；PDF 路径走 MinerU + heading。

**Step 3: Commit**

```bash
git add app/core/kb/__init__.py
git commit -m "refactor(kb): PDF pipeline via MinerU and heading split"
```

---

## 阶段三：Neo4j 写入

### Task 5: Neo4j 客户端与写入文档/块

**Files:**
- Create: `app/core/kg/__init__.py`
- Create: `app/core/kg/neo4j_store.py`
- Test: `tests/core/kg/test_neo4j_store.py`（可选，需 Neo4j 或 testcontainers）

**Step 1: 添加依赖**

在 `pyproject.toml` 或 `requirements.txt` 中增加 `neo4j`（官方驱动）。

**Step 2: 实现 Neo4j 写入**

`app/core/kg/__init__.py`:

```python
from app.core.kg.neo4j_store import write_document_chunks

__all__ = ["write_document_chunks"]
```

`app/core/kg/neo4j_store.py`:

- 使用 `neo4j.GraphDatabase.driver(settings.NEO4J_URI, auth=(user, password))` 连接。
- 实现 `write_document_chunks(doc_id: str, doc_title: str, chunks: List[DocumentChunk], source: Optional[str] = None)`：
  - 若不存在则创建 `Document` 节点（doc_id, doc_title, source, created_at）；
  - 对每个 chunk 创建 `Chunk` 节点（chunk_id, doc_id, content_type, section_path 序列化, content_preview 取 content 前 200 字）；
  - 创建 `Document -[:CONTAINS]-> Chunk` 关系。
- 使用 MERGE 或 CREATE，保证幂等（同一 doc_id 多次写入可覆盖或跳过，由你决定；建议按 doc_id 先删后写，保证与 Chroma 一致）。

**Step 3: 在 import_pdf_via_mineru 中调用**

在 `app/core/kb/__init__.py` 的 `import_pdf_via_mineru` 内，在 `vector_store_manager.add_chunks(chunks)` 之后调用 `write_document_chunks(doc_id, doc_title, chunks, source=...)`；捕获异常可记录日志并继续（避免因 Neo4j 不可用导致整条导入失败）。

**Step 4: 验证**

Run: 本地起 Neo4j 或使用已有实例，上传一份 PDF，检查 Neo4j 中是否有对应 Document 与 Chunk 节点及 CONTAINS 关系。

**Step 5: Commit**

```bash
git add app/core/kg/ pyproject.toml
git commit -m "feat(kg): Neo4j write for document and chunks"
```

---

## 阶段四：清理与文档

### Task 6: 移除 PDF 路径对 convert_to_structured 的依赖

**Files:**
- Modify: `app/core/kb/__init__.py`

**Step 1: 确认 PDF 已不再走 pre-parse**

在 `import_file_step` 中，PDF 已在 Task 4 中单独走 `import_pdf_via_mineru`，因此不会进入下方的 `for i, document in enumerate(documents): if strategy == "structured": documents[i] = convert_to_structured(document)`。若仍有其他入口对 PDF 调用 `convert_to_structured`，删除或条件化（仅对非 PDF 的 structured 策略保留）。

**Step 2: 可选 — 保留 structured 策略仅用于 .md**

若希望 .md 文件仍可使用「带 content_type 的结构化切分」，则保留 `convert_to_structured` 仅在对 `file_ext in [".md", ".markdown"]` 且 `strategy == "structured"` 时使用；否则从 `import_file_step` 中移除对 `convert_to_structured` 的调用。

**Step 3: Commit**

```bash
git add app/core/kb/__init__.py
git commit -m "chore(kb): remove convert_to_structured from PDF pipeline"
```

---

### Task 7: 更新 README 与设计文档引用

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-02-national-standard-rag-refactor-design.md`（在「下一步」处注明已进入实施计划）

**Step 1: 更新 README**

- 将「LLM 增强处理」「使用 LLM 进行文档结构分析和内容结构化转换」改为：PDF 解析由 MinerU 本地服务完成，切分采用按标题的粗粒度策略，不再使用 LLM 做全文结构化。
- 在「知识库导入流程」中：PDF → MinerU 服务 → MD → 按标题切分 → Chroma + Neo4j。
- 在「依赖与配置」中增加 MinerU 服务地址、Neo4j 连接说明。

**Step 2: 设计文档末尾**

在「下一步」增加一句：实施计划见 `docs/plans/2026-03-02-national-standard-rag-implementation-plan.md`。

**Step 3: Commit**

```bash
git add README.md docs/plans/
git commit -m "docs: README and design ref for MinerU + heading + Neo4j"
```

---

## 执行方式说明

**Plan complete and saved to `docs/plans/2026-03-02-national-standard-rag-implementation-plan.md`.**

两种执行方式：

1. **本会话内按任务推进（Subagent-Driven）** — 按 Task 1 → Task 7 顺序，每完成一个 Task 做一次 commit，你可在每步后 review，适合边做边改。
2. **新会话中批量执行（Parallel Session）** — 在新会话中打开本仓库，使用 executing-plans 技能按计划逐项执行，并在检查点做 review。

你更倾向哪一种？若选 1，我将从 Task 1 开始在本会话内逐步实现并提交。
