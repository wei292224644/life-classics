# 国家标准 RAG + Agent 完整重构 — 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成数据管道（MinerU PDF → 按标题切分 → Chroma + Neo4j）与 Agent 模块（Deep Agents + Skills + Tools）的完整实现，形成可运行的国家标准 RAG 服务。

**Architecture:** PDF 经 MinerU 服务得 MD → 按 `##`/`###` 粗粒度切分 → 写入 Chroma 与 Neo4j；Agent 层用 Deep Agents 编排知识库 / 网络 / Neo4j / PostgreSQL 四类工具，Skills 用 Markdown 定义；保留现有 `/api/doc/*` 与纯 RAG `/chat`，新增 `/api/agent/chat`。

**Tech Stack:** FastAPI, MinerU（HTTP）, ChromaDB, Neo4j, Deep Agents (LangChain/LangGraph), 现有 LLM/Embedding。

**设计参考:** 数据管道见设计文档（若有 `docs/plans/2026-03-02-national-standard-rag-refactor-design.md`）；Agent 见 `docs/plans/2026-03-02-agent-module-design.md`（若有）。

---

## Phase 1：MinerU 适配器

### Task 1.1：MinerU 适配器 HTTP 调用实现

**Files:**
- Modify: `app/core/pdf/mineru_adapter.py`
- Create: `tests/core/pdf/test_mineru_adapter.py`（可选，mock 请求）

**Step 1：写失败用例（可选）**

在 `tests/core/pdf/test_mineru_adapter.py` 中：

```python
import pytest
from unittest.mock import patch, mock_open
from app.core.pdf.mineru_adapter import pdf_to_markdown

@patch("app.core.pdf.mineru_adapter.requests.post")
def test_pdf_to_markdown_returns_markdown_string(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"markdown": "## 测试\n内容"}
    result = pdf_to_markdown("/tmp/test.pdf")
    assert "## 测试" in result
```

**Step 2：运行测试确认失败**

Run: `pytest tests/core/pdf/test_mineru_adapter.py -v`  
Expected: FAIL（或 test file not found / pdf_to_markdown 当前 raise NotImplementedError）。

**Step 3：最小实现**

在 `app/core/pdf/mineru_adapter.py` 中实现：使用 `requests.post(service_url/convert, files={"file": (filename, f, "application/pdf")}, timeout=timeout)`，`r.raise_for_status()`，`return r.json().get("markdown", r.json().get("content", ""))`。若实际 MinerU API 为异步 job，则改为上传 → 轮询 result → 取 MD。

**Step 4：运行测试通过**

Run: `pytest tests/core/pdf/test_mineru_adapter.py -v`  
Expected: PASS（或跳过无 test 时仅确认 `pdf_to_markdown` 可调用）。

**Step 5：Commit**

```bash
git add app/core/pdf/mineru_adapter.py tests/core/pdf/
git commit -m "feat(pdf): implement MinerU adapter HTTP call"
```

---

## Phase 2：按标题粗粒度切分

### Task 2.1：实现 split_heading_from_markdown（MD 字符串 → List[DocumentChunk]）

**Files:**
- Modify: `app/core/kb/strategy/heading_strategy.py`
- Create: `tests/core/kb/strategy/test_heading_strategy.py`

**Step 1：写失败用例**

在 `tests/core/kb/strategy/test_heading_strategy.py` 中：

```python
from app.core.kb.strategy.heading_strategy import split_heading_from_markdown

def test_heading_split_single_section():
    md = "## 适用范围\n\n本标准适用于食品添加剂。"
    chunks = split_heading_from_markdown(md, doc_id="d1", doc_title="test", source="test.md")
    assert len(chunks) >= 1
    assert chunks[0].section_path
    assert "适用范围" in (chunks[0].section_path or []) or "适用范围" in str(chunks[0].content)
```

**Step 2：运行测试确认失败**

Run: `pytest tests/core/kb/strategy/test_heading_strategy.py -v`  
Expected: FAIL（split_heading_from_markdown 未定义或行为不符）。

**Step 3：实现 split_heading_from_markdown**

在 `app/core/kb/strategy/heading_strategy.py` 中：新增函数 `split_heading_from_markdown(markdown_content: str, doc_id: str, doc_title: str, source: str, markdown_id: Optional[str] = None) -> List[DocumentChunk]`。按 `^#{1,6}\s+.+` 识别标题，从当前标题到下一同级或更高级标题之间的内容为一个 chunk；`section_path` 为当前标题层级列表；`content_type` 统一 `ContentType.GENERAL_RULE` 或 `ContentType.NOTE`；`content` 为字符串；使用 `DocumentChunk(doc_id, doc_title, section_path, content_type, content, meta={"source": source}, markdown_id=markdown_id or doc_id)`。

**Step 4：运行测试通过**

Run: `pytest tests/core/kb/strategy/test_heading_strategy.py -v`  
Expected: PASS.

**Step 5：Commit**

```bash
git add app/core/kb/strategy/heading_strategy.py tests/core/kb/strategy/test_heading_strategy.py
git commit -m "feat(kb): heading-based chunking from markdown string"
```

---

### Task 2.2：PDF 流水线改为 MinerU + 按标题切分

**Files:**
- Modify: `app/core/kb/__init__.py`

**Step 1：新增 import_pdf_via_mineru**

在 `app/core/kb/__init__.py` 中：新增 `import_pdf_via_mineru(file_path: str, original_filename: str = None, **kwargs) -> List[DocumentChunk]`。内部：`from app.core.pdf import pdf_to_markdown` 得到 `md_content`；生成 `doc_id`（uuid）、`doc_title`（Path(original_filename).stem）；调用 `split_heading_from_markdown(md_content, doc_id, doc_title, source=original_filename or Path(file_path).name)`；`vector_store_manager.add_chunks(chunks)`；return chunks。

**Step 2：PDF 分支走 import_pdf_via_mineru**

在 `import_file_step` 中，当 `file_ext == ".pdf"` 时：调用 `import_pdf_via_mineru(file_path, original_filename=original_filename, **kwargs)` 并 return，不再执行下方 `import_pdf`、pre-parse、`split_step`。

**Step 3：验证**

Run: 若有对 `import_file_step` 的集成测试则运行；否则手动或单元测试验证 PDF 分支不报错（MinerU 不可用时会抛，属预期）。

**Step 4：Commit**

```bash
git add app/core/kb/__init__.py
git commit -m "refactor(kb): PDF pipeline via MinerU and heading split"
```

---

## Phase 3：Neo4j 写入

### Task 3.1：Neo4j 依赖与 write_document_chunks 实现

**Files:**
- Modify: `pyproject.toml`（或 requirements.txt）
- Modify: `app/core/kg/neo4j_store.py`

**Step 1：添加依赖**

在 `pyproject.toml` 的 dependencies 中增加 `neo4j>=5.0.0`。

**Step 2：实现 write_document_chunks**

在 `app/core/kg/neo4j_store.py` 中：使用 `neo4j.GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))`；在 `write_document_chunks` 内 MERGE Document 节点（doc_id, doc_title, source, created_at），对每个 chunk MERGE Chunk 节点（chunk_id, doc_id, content_type, section_path 序列化, content_preview=content[:200]），MERGE `(Document)-[:CONTAINS]->(Chunk)`。同一 doc_id 可先 DELETE 再 CREATE 以保持与 Chroma 一致（可选）。

**Step 3：在 import_pdf_via_mineru 中调用**

在 `app/core/kb/__init__.py` 的 `import_pdf_via_mineru` 内，在 `vector_store_manager.add_chunks(chunks)` 之后调用 `from app.core.kg import write_document_chunks`；`write_document_chunks(doc_id, doc_title, chunks, source=...)`；try/except 记录日志，Neo4j 失败不阻断导入。

**Step 4：Commit**

```bash
git add app/core/kg/neo4j_store.py app/core/kb/__init__.py pyproject.toml
git commit -m "feat(kg): Neo4j write for document and chunks"
```

---

## Phase 4：Agent 依赖与 LLM 适配

### Task 4.1：添加 deepagents 与 langgraph 依赖

**Files:**
- Modify: `pyproject.toml`

**Step 1：添加依赖**

在 dependencies 中增加 `deepagents>=0.4.0`、`langgraph>=0.2.0`（若 deepagents 未覆盖）。

**Step 2：安装验证**

Run: `uv sync` 或 `pip install -e .`  
Expected: 安装成功。

**Step 3：Commit**

```bash
git add pyproject.toml
git commit -m "deps: add deepagents and langgraph"
```

---

### Task 4.2：LLM 适配器（现有 LLM → LangChain ChatModel）

**Files:**
- Modify: `app/core/agent/llm_adapter.py`
- Create: `tests/core/agent/test_llm_adapter.py`（可选）

**Step 1：实现 get_langchain_chat_model**

在 `app/core/agent/llm_adapter.py` 中：根据 `settings.CHAT_PROVIDER` 返回对应 LangChain 模型。若为 dashscope：使用 `langchain_openai.ChatOpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=settings.DASHSCOPE_API_KEY, model=settings.CHAT_MODEL)`；若为 ollama：使用 `langchain_ollama.ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.CHAT_MODEL)`。return 实例。

**Step 2：验证**

Run: `python -c "from app.core.agent.llm_adapter import get_langchain_chat_model; m=get_langchain_chat_model(); print(m)"`  
Expected: 打印模型对象。

**Step 3：Commit**

```bash
git add app/core/agent/llm_adapter.py
git commit -m "feat(agent): LLM adapter for Deep Agents"
```

---

## Phase 5：Agent Tools

### Task 5.1：knowledge_base Tool

**Files:**
- Create: `app/core/tools/knowledge_base.py`
- Modify: `app/core/tools/__init__.py`

**Step 1：实现 knowledge_base Tool**

在 `app/core/tools/knowledge_base.py` 中：定义 `@tool` 函数 `knowledge_base(query: str, top_k: int = 5) -> str`。内部调用 `from app.core.kb.vector_store import vector_store_manager`；`vector_store_manager.search_with_rerank(query, top_k=top_k, retrieve_k=top_k*2)`；将返回的 chunk 的 `document.page_content` 与 metadata 格式化为字符串并 return。

**Step 2：导出**

在 `app/core/tools/__init__.py` 中：`from app.core.tools.knowledge_base import knowledge_base` 或 `get_knowledge_base_tool`；加入 `__all__`。

**Step 3：Commit**

```bash
git add app/core/tools/knowledge_base.py app/core/tools/__init__.py
git commit -m "feat(tools): add knowledge_base tool for Agent"
```

---

### Task 5.2：neo4j_query 与 postgres_query Tools（占位）

**Files:**
- Create: `app/core/tools/neo4j_query.py`
- Create: `app/core/tools/postgres_query.py`
- Modify: `app/core/tools/__init__.py`

**Step 1：实现占位 Tool**

在 `neo4j_query.py` 中：`@tool` 函数 `neo4j_query(query: str) -> str`，当前 return "Neo4j query not implemented" 或只读执行简单 Cypher（如 MATCH (d:Document) RETURN d LIMIT 5）。在 `postgres_query.py` 中：`@tool` 函数 `postgres_query(query: str) -> str`，当前 return "PostgreSQL query not implemented" 或占位。

**Step 2：在 __init__.py 中导出**

**Step 3：Commit**

```bash
git add app/core/tools/neo4j_query.py app/core/tools/postgres_query.py app/core/tools/__init__.py
git commit -m "feat(tools): add neo4j_query and postgres_query stubs"
```

---

## Phase 6：Agent Factory 与 API

### Task 6.1：create_national_standard_agent 实现

**Files:**
- Modify: `app/core/agent/factory.py`

**Step 1：实现 create_national_standard_agent**

在 `app/core/agent/factory.py` 中：`from deepagents import create_deep_agent`；`from app.core.agent.llm_adapter import get_langchain_chat_model`；`from app.core.tools import get_web_search_tool, knowledge_base`（及 neo4j_query、postgres_query）；`model = get_langchain_chat_model()`；`tools = [knowledge_base, get_web_search_tool(), neo4j_query, postgres_query]`；`return create_deep_agent(model=model, tools=tools, skills=[skills_path], system_prompt="...")`。skills_path 默认 `settings.AGENT_SKILLS_PATH` 或 `"app/skills"`。

**Step 2：验证**

Run: `python -c "from app.core.agent.factory import create_national_standard_agent; g=create_national_standard_agent(); print(g)"`  
Expected: 打印 LangGraph 图或 Agent 对象（若依赖 Chroma/Rerank 导致网络问题可先 mock）。

**Step 3：Commit**

```bash
git add app/core/agent/factory.py
git commit -m "feat(agent): implement create_national_standard_agent"
```

---

### Task 6.2：/api/agent/chat 实现

**Files:**
- Modify: `app/api/agent/router.py`

**Step 1：实现 agent_chat**

在 `app/api/agent/router.py` 中：在 `agent_chat` 内获取或创建 agent（单例或每次 create_national_standard_agent()）；构建 `messages` 从 `request.conversation_history` 与 `request.message`；调用 `agent.invoke({"messages": messages}, config={"configurable": {"thread_id": request.thread_id or "default"}})`；从返回的 state 中取最后一条 AI 消息的 content，构造 `AgentResponse(content=..., sources=..., tool_calls=...)` 并 return。

**Step 2：验证**

Run: 启动服务后 `curl -X POST http://localhost:9999/api/agent/chat -H "Content-Type: application/json" -d '{"message":"你好"}'`  
Expected: 200 与 JSON 回复（或 501 若 agent 未完全接好）。

**Step 3：Commit**

```bash
git add app/api/agent/router.py
git commit -m "feat(api): implement /api/agent/chat"
```

---

## Phase 7：清理与文档

### Task 7.1：移除 PDF 路径对 convert_to_structured 的依赖

**Files:**
- Modify: `app/core/kb/__init__.py`

**Step 1：确认 PDF 不经过 pre-parse**

在 `import_file_step` 中，PDF 已由 Task 2.2 单独走 `import_pdf_via_mineru` 并 return，故不会执行到 `for i, document in enumerate(documents): ... convert_to_structured(document)`。若需保留 .md 的 structured 策略，则保留该循环仅对非 PDF 的 documents；否则可删除该 pre-parse 循环或加 `if file_ext != ".pdf"`。

**Step 2：Commit**

```bash
git add app/core/kb/__init__.py
git commit -m "chore(kb): remove convert_to_structured from PDF path"
```

---

### Task 7.2：更新 README 与设计引用

**Files:**
- Modify: `README.md`

**Step 1：更新功能说明**

在 README 中：补充「Agent 模块：/api/agent/chat，支持知识库 / 网络 / Neo4j / PostgreSQL」；补充 MinerU、Neo4j、Agent 配置项说明；补充实施计划文档路径 `docs/plans/2026-03-02-full-refactor-implementation-plan.md`。

**Step 2：Commit**

```bash
git add README.md
git commit -m "docs: README update for Agent and refactor plan"
```

---

## 执行方式说明

**Plan complete and saved to `docs/plans/2026-03-02-full-refactor-implementation-plan.md`.**

两种执行方式：

1. **本会话内按任务推进（Subagent-Driven）** — 按 Phase 1 → Phase 7 顺序，每完成一个 Task 做一次 commit，你可在每步后 review，适合边做边改。
2. **新会话中批量执行（Parallel Session）** — 在新会话中打开本仓库，使用 executing-plans 技能按计划逐项执行，并在检查点做 review。

你更倾向哪一种？若选 1，我将从 Task 1.1 开始在本会话内逐步实现并提交。
