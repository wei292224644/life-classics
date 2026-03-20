# Agent Agno 统一化重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 deepagents，将双 Agent（factory.py + food_safety_agent.py）合并为单一 Agno Agent，用 Agno 内置工具替换自定义工具实现。

**Architecture:** 新建 `agent/agent.py` 作为唯一入口，使用 Agno `Agent` + `OpenAILike` 模型 + 内置工具（DuckDuckGoTools / Neo4jTools / PostgresTools）+ 自定义 `knowledge_base`，通过 Agno 原生 `LocalSkills` 加载 `agent/skills/` 下所有 6 个 skill 目录（全部保留）。router.py 只保留单一 Agent 路径。

**Tech Stack:** agno>=2.5.10, agno.tools.duckduckgo.DuckDuckGoTools, agno.tools.neo4j.Neo4jTools, agno.tools.postgres.PostgresTools, agno.models.openai.like.OpenAILike, agno.skills.Skills + agno.skills.loaders.local.LocalSkills, psycopg[binary]（PostgresTools 依赖）

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `server/config.py` | 新增 PostgreSQL 分项配置字段；修正 AGENT_SKILLS_PATH 默认值 |
| 修改 | `server/agent/tools/knowledge_base.py` | 移除 LangChain `@tool` 装饰器，改为纯 async 函数 |
| 修改 | `server/agent/tools/__init__.py` | 只导出 `knowledge_base` |
| 修改 | `server/agent/skills/food-safety/` | 3 个 .md 合并为单一 `SKILL.md` |
| 新建 | `server/agent/agent.py` | 统一 Agno Agent 工厂函数 |
| 修改 | `server/agent/__init__.py` | 导出新 `get_agent` 替换旧 factory |
| 修改 | `server/api/agent/router.py` | 删除双路由，单一 Agent 路径 |
| 修改 | `server/api/agent/models.py` | 清理废弃字段（thread_id, agent_type） |
| 修改 | `server/pyproject.toml` | 删除 `deepagents`，新增 `psycopg[binary]` |
| 保留 | `server/agent/session_store.py` | Agno session 管理，继续复用 |
| 保留 | `server/agent/skills/`（全部子目录） | LocalSkills 全部加载（food-safety/national-standard-rag/neo4j-graph/postgres-query/web-search/document-type） |
| 删除 | `server/agent/factory.py` | deepagents 实现 |
| 删除 | `server/agent/food_safety_agent.py` | 旧 Agno 实现 |
| 删除 | `server/agent/llm_adapter.py` | 只为 factory.py 服务 |
| 删除 | `server/agent/skill_loader.py` | 手动加载逻辑，被 LocalSkills 替代 |
| 删除 | `server/agent/tools/web_search.py` | 被 DuckDuckGoTools 替代 |
| 删除 | `server/agent/tools/neo4j_query.py` | 被 Neo4jTools 替代（原本未实现） |
| 删除 | `server/agent/tools/postgres_query.py` | 被 PostgresTools 替代 |
| 删除/修改 | `server/tests/core/agent/` | 删除过期测试，重写 knowledge_base 测试 |

---

## Task 1: 修复 config.py（新增 PostgreSQL 字段，修正 AGENT_SKILLS_PATH）

**Files:**
- Modify: `server/config.py`

两处修复：
1. `AGENT_SKILLS_PATH` 默认值是 `"server/agent/skills"`，但服务 cwd 是 `server/`，导致路径变成 `server/server/agent/skills`。改为 `"agent/skills"`。
2. PostgreSQL 配置当前无任何字段，但 `PostgresTools` 需要分项连接参数。

- [ ] **Step 1: 修改 config.py**

在 `CHAT_TEMPERATURE` 字段下方，将 `AGENT_SKILLS_PATH` 默认值改为 `"agent/skills"`，并新增 PostgreSQL 字段：

```python
    # ── 对话Agent配置 ────────────────────────────────────────────────────────────
    CHAT_PROVIDER: str = "openai"
    CHAT_MODEL: str = "qwen3-max-2026-01-23"
    AGENT_SKILLS_PATH: str = "agent/skills"   # 相对于 server/ 目录
    AGENT_MAX_ITERATIONS: int = 10
    CHAT_TEMPERATURE: float = 0.4

    # ── PostgreSQL 连接 ────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
```

- [ ] **Step 2: Commit**

```bash
git add server/config.py
git commit -m "fix(config): correct AGENT_SKILLS_PATH default and add PostgreSQL fields"
```

---

## Task 2: 修复 knowledge_base 工具（移除 LangChain 依赖）

**Files:**
- Modify: `server/agent/tools/knowledge_base.py`
- Modify: `server/agent/tools/__init__.py`

`knowledge_base.py` 当前用 `@tool`（LangChain 装饰器），Agno 只需要纯 async 函数，装饰器需要去掉。

- [ ] **Step 1: 修改 knowledge_base.py**

```python
"""
知识库检索工具：供 Agent 基于混合检索（向量 + BM25 + Rerank）查询国家标准等内容。
"""

from kb.retriever import search


async def knowledge_base(query: str, top_k: int = 5) -> str:
    """
    从知识库中检索与查询最相关的文档片段（国家标准等）。适合回答与已入库文档相关的问题。

    Args:
        query: 检索查询文本
        top_k: 返回条数，默认 5

    Returns:
        格式化后的检索结果文本，包含内容与来源信息
    """
    try:
        results = await search(query, top_k=top_k)
    except Exception as e:
        return f"知识库检索失败: {e!s}"

    if not results:
        return "未检索到相关文档。"

    lines = []
    for i, r in enumerate(results, 1):
        part = f"[{i}] 标准号: {r['standard_no']}\n内容: {r['raw_content']}\n相关度: {r['score']:.2f}"
        lines.append(part)

    return "\n\n".join(lines)
```

- [ ] **Step 2: 更新 tools/__init__.py**

```python
"""
工具模块 - 提供各种工具函数供 Agent 使用
"""
from agent.tools.knowledge_base import knowledge_base

__all__ = ["knowledge_base"]
```

- [ ] **Step 3: Commit**

```bash
git add server/agent/tools/knowledge_base.py server/agent/tools/__init__.py
git commit -m "refactor(agent): remove LangChain @tool decorator from knowledge_base"
```

---

## Task 3: 迁移 food-safety skills 为 Agno SKILL.md 格式

**Files:**
- Create: `server/agent/skills/food-safety/SKILL.md`
- Delete: `server/agent/skills/food-safety/01_food_safety_assistant.md`
- Delete: `server/agent/skills/food-safety/02_intent_routing.md`
- Delete: `server/agent/skills/food-safety/03_answer_format.md`

`LocalSkills` 加载 `agent/skills/` 时，只识别含 `SKILL.md` 的子目录。其他 5 个子目录（`national-standard-rag`、`neo4j-graph`、`postgres-query`、`web-search`、`document-type`）已有正确格式，全部保留。只需将 `food-safety/` 的 3 个零散文件合并为一个 `SKILL.md`。

- [ ] **Step 1: 创建 SKILL.md（合并 3 个文件内容）**

```markdown
---
name: food-safety
description: 面向消费者的食品安全助手，回答食品标准、成分安全、添加剂规定、品牌召回等问题
allowed-tools: ["knowledge_base", "web_search"]
---

# 食品安全助手

你是一个面向普通消费者的食品安全 AI 助手。你的目标是用通俗易懂的语言帮助用户了解食品安全相关信息。

## 信息权威优先级

- 国家标准（GB 系列）是最高权威，其他信息作为补充
- 当工具结果之间存在矛盾时：以国家标准内容（knowledge_base 检索结果）为准，同时向用户说明其他来源的不同观点和差异
- 知识库无结果时，直接告知用户"暂未找到相关信息"，不猜测、不推断

## 语言风格

- 先给结论（一句话通俗说明），再给依据（专业内容）
- 使用日常用语，避免堆砌专业术语
- 对复杂概念主动提供类比或例子

# 工具选择规则

## 工具说明

- `knowledge_base`：检索国家食品安全标准知识库，适合回答标准规定、成分安全性、添加剂用量等问题
- `web_search`：搜索互联网，**仅用于**查询品牌、企业、召回事件、舆情等时效性信息

## 选择规则

- 问题涉及"食品标准/成分安全/添加剂规定/是否合规/用量限制" → 调用 `knowledge_base`
- 问题涉及"品牌/企业/召回/新闻/事件/舆情/近期" → 仅调用 `web_search`
- 问题同时涉及标准知识和品牌舆情 → 分别调用各自工具，在答案中分段呈现
- 所有工具均无结果时，直接输出无结果回复，不要尝试补救

# 输出格式

**结论**：[一句话通俗说明]

**依据**：[来自知识库的标准条款或网络信息]

**来源**：[一句话说明来源]

无结果时："抱歉，暂未找到关于「[内容]」的相关信息，建议咨询专业机构或查阅官方标准文件。"

注意：不要在答案中提及工具名称。
```

- [ ] **Step 2: 删除旧的 3 个文件**

```bash
rm server/agent/skills/food-safety/01_food_safety_assistant.md
rm server/agent/skills/food-safety/02_intent_routing.md
rm server/agent/skills/food-safety/03_answer_format.md
```

- [ ] **Step 3: Commit**

```bash
git add server/agent/skills/food-safety/
git commit -m "refactor(agent): migrate food-safety skills to Agno SKILL.md format"
```

---

## Task 4: 新建统一 agent/agent.py

**Files:**
- Create: `server/agent/agent.py`

- [ ] **Step 1: 创建 agent/agent.py**

```python
"""
统一 Agno Agent：国家标准 RAG + 食品安全助手。
"""

from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.skills import Skills
from agno.skills.loaders.local import LocalSkills
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.neo4j import Neo4jTools
from agno.tools.postgres import PostgresTools

from agent.tools.knowledge_base import knowledge_base
from config import settings

_agent: Optional[Agent] = None


def create_agent() -> Agent:
    """
    创建统一 Agno Agent。

    模型从环境变量读取（CHAT_MODEL / LLM_BASE_URL / LLM_API_KEY）。
    工具：knowledge_base（自定义 RAG）+ DuckDuckGo + Neo4j + PostgreSQL。
    Skills：从 agent/skills/ 目录按 Agno LocalSkills 格式加载。
    """
    model = OpenAILike(
        id=settings.CHAT_MODEL,
        base_url=settings.LLM_BASE_URL or None,
        api_key=settings.LLM_API_KEY,
        temperature=settings.CHAT_TEMPERATURE,
    )

    # 路径解析：AGENT_SKILLS_PATH 相对于 server/ 目录
    skills_path = Path(settings.AGENT_SKILLS_PATH)
    if not skills_path.is_absolute():
        skills_path = Path(__file__).parent.parent / settings.AGENT_SKILLS_PATH
    skills = Skills(loaders=[LocalSkills(path=str(skills_path))])

    return Agent(
        model=model,
        tools=[
            knowledge_base,
            DuckDuckGoTools(),
            Neo4jTools(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD,
            ),
            PostgresTools(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                db_name=settings.POSTGRES_DB,
            ),
        ],
        skills=skills,
    )


def get_agent() -> Agent:
    """获取全局 Agent 单例（懒加载）"""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent
```

- [ ] **Step 2: Commit**

```bash
git add server/agent/agent.py
git commit -m "feat(agent): create unified Agno agent with built-in tools and LocalSkills"
```

---

## Task 5: 更新 agent/__init__.py

**Files:**
- Modify: `server/agent/__init__.py`

- [ ] **Step 1: 替换导出**

```python
"""
Agent 模块：基于 Agno 的统一智能助手（知识库 / 网络 / Neo4j / PostgreSQL）。
"""

from agent.agent import create_agent, get_agent

__all__ = ["create_agent", "get_agent"]
```

- [ ] **Step 2: Commit**

```bash
git add server/agent/__init__.py
git commit -m "refactor(agent): update __init__ to export unified Agno agent"
```

---

## Task 6: 简化 api/agent/router.py 和 models.py

**Files:**
- Modify: `server/api/agent/router.py`
- Modify: `server/api/agent/models.py`

删除双路由，清理废弃的 `thread_id`、`agent_type` 字段。`session_store.py` 继续复用（它负责 TTL/LRU session 管理，Agno 自身不提供）。

- [ ] **Step 1: 更新 models.py**

```python
"""
Agent 请求/响应模型。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentRequest(BaseModel):
    """Agent 对话请求"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    session_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """检索来源项"""
    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None


class AgentResponse(BaseModel):
    """Agent 对话响应"""
    content: str
    session_id: Optional[str] = None
    sources: Optional[List[SearchResult]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
```

- [ ] **Step 2: 重写 router.py**

```python
"""
Agent 路由：/api/agent/chat
"""

from fastapi import APIRouter, HTTPException

from api.agent.models import AgentRequest, AgentResponse
from agent.session_store import get_session_store

router = APIRouter()

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        from agent.agent import get_agent
        _agent = get_agent()
    return _agent


@router.post("/chat", response_model=AgentResponse)
async def agent_chat(request: AgentRequest) -> AgentResponse:
    """Agent 对话（单一 Agno Agent）"""
    try:
        store = get_session_store()
        session = await store.get_or_create(request.session_id)
        session_id = session["session_id"]

        agent = _get_agent()
        response = await agent.arun(
            request.message,
            session_id=session_id,
        )

        content = response.content if hasattr(response, "content") else str(response)
        return AgentResponse(content=content or "", session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: Commit**

```bash
git add server/api/agent/router.py server/api/agent/models.py
git commit -m "refactor(api): simplify agent router to single Agno agent path"
```

---

## Task 7: 删除废弃文件并修复受影响测试

**Files:**
- Delete: `server/agent/factory.py`
- Delete: `server/agent/food_safety_agent.py`
- Delete: `server/agent/llm_adapter.py`
- Delete: `server/agent/skill_loader.py`
- Delete: `server/agent/tools/web_search.py`
- Delete: `server/agent/tools/neo4j_query.py`
- Delete: `server/agent/tools/postgres_query.py`
- Delete: `server/tests/core/agent/test_food_safety_agent.py`（若存在）
- Delete: `server/tests/core/agent/test_skill_loader.py`（若存在）
- Modify: `server/tests/core/agent/test_knowledge_base.py`（若存在，重写调用方式）

- [ ] **Step 1: 删除废弃实现文件**

```bash
cd server
rm agent/factory.py
rm agent/food_safety_agent.py
rm agent/llm_adapter.py
rm agent/skill_loader.py
rm agent/tools/web_search.py
rm agent/tools/neo4j_query.py
rm agent/tools/postgres_query.py
```

- [ ] **Step 2: 删除过期测试（这些测试的被测对象已不存在）**

```bash
cd server
rm -f tests/core/agent/test_food_safety_agent.py
rm -f tests/core/agent/test_skill_loader.py
```

- [ ] **Step 3: 若存在 test_knowledge_base.py，更新调用方式**

旧测试用 `await knowledge_base.ainvoke({...})`（LangChain 专有），改为直接调用：

```python
# 旧写法（删除）
result = await knowledge_base.ainvoke({"query": "苯甲酸", "top_k": 3})

# 新写法
result = await knowledge_base(query="苯甲酸", top_k=3)
```

同时将 patch 路径从旧路径改为：`agent.tools.knowledge_base.search`

- [ ] **Step 4: 验证无残留引用**

```bash
cd server
grep -r "factory\|food_safety_agent\|llm_adapter\|skill_loader\|web_search\|neo4j_query\|postgres_query" \
  --include="*.py" agent/ api/ tests/
```

预期输出：无匹配

- [ ] **Step 5: Commit**

```bash
git add -A server/agent/ server/tests/
git commit -m "refactor(agent): delete deepagents factory, old Agno agent, and replaced custom tools; fix tests"
```

---

## Task 8: 更新依赖

**Files:**
- Modify: `server/pyproject.toml`

- [ ] **Step 1: 删除 deepagents，新增 psycopg**

在 `server/pyproject.toml` 中：
- 删除行：`"deepagents>=0.4.0",`
- 新增行：`"psycopg[binary]>=3.0.0",`（PostgresTools 依赖 psycopg v3）

- [ ] **Step 2: 同步依赖**

```bash
cd server
uv sync
```

预期：正常完成，无报错

- [ ] **Step 3: 验证 Agent 可导入**

```bash
cd server
uv run python3 -c "from agent.agent import get_agent; print('OK')"
```

预期输出：`OK`

- [ ] **Step 4: Commit**

```bash
git add server/pyproject.toml server/uv.lock
git commit -m "chore(deps): remove deepagents, add psycopg for PostgresTools"
```

---

## Task 9: 冒烟测试

验证整体链路正常。

- [ ] **Step 1: 启动服务**

```bash
cd server
uv run python3 run.py
```

预期：服务启动无报错，监听 http://localhost:9999

- [ ] **Step 2: 单轮问答测试**

```bash
curl -X POST http://localhost:9999/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "GB2760 中苯甲酸的限量是多少？"}'
```

预期：返回 `{"content": "...", "session_id": "..."}` 正常回答

- [ ] **Step 3: 验证 session 多轮对话**

固定 session_id 发两条消息，验证第二条回复能引用第一条上下文：

```bash
# 第一轮
curl -X POST http://localhost:9999/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "我想了解苯甲酸在饮料中的限量", "session_id": "smoke-test-001"}'

# 第二轮（依赖第一轮上下文）
curl -X POST http://localhost:9999/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "那它在果酱中呢？", "session_id": "smoke-test-001"}'
```

预期：第二轮回复能理解"它"指苯甲酸，并给出果酱中的限量。

- [ ] **Step 4: 若测试通过，最终 Commit**

```bash
git add -A
git commit -m "chore: unified Agno agent smoke test passed"
```
