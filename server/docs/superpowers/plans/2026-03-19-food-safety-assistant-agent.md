# 食品安全 AI 助手 Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 Agno 框架构建面向普通消费者的食品安全 AI 助手，支持多轮对话，通过向量知识库和 Web 搜索自动回答食品安全问题。

**Architecture:** SkillLoader 从 `app/skills/food-safety/` 加载 Markdown 技能文件拼接为 system prompt，注入 Agno Agent；Agent 根据 instructions 自主选择工具（vector_search / web_search）并行调用；Session 以内存 TTLCache + asyncio.Lock 管理。

**Tech Stack:** Python 3.12, FastAPI, Agno, DashScope qwen-plus, cachetools, pytest

> ⚠️ **已知设计决策（spec 阶段已确认，勿重复讨论）**：
> - **框架选 Agno**：spec 讨论时已确认 DeepAgents 不支持 Markdown 技能文件方式，用户明确选择 Agno
> - **skill 文件用 3 个独立 .md**：spec 已确认，非复用现有 SKILL.md 结构
> - **session_id 与 thread_id 并存**：spec 已确认，thread_id 保留给 LangGraph agent，新 agent 用 session_id
> - **MVP 工具仅 vector_search + web_search**：spec 已确认，neo4j/pg 在迭代 2/3

---

## 文件清单

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 新建 | `agent-server/spike/test_agno_dashscope.py` | Spike 验证脚本（完成后可删除） |
| 修改 | `agent-server/pyproject.toml` | 添加 agno, cachetools 依赖 |
| 新建 | `agent-server/app/skills/food-safety/01_food_safety_assistant.md` | 角色定义技能文件 |
| 新建 | `agent-server/app/skills/food-safety/02_intent_routing.md` | 工具选择引导技能文件 |
| 新建 | `agent-server/app/skills/food-safety/03_answer_format.md` | 输出格式技能文件 |
| 新建 | `agent-server/app/core/agent/skill_loader.py` | 读取并拼接 .md 技能文件 |
| 新建 | `agent-server/app/core/agent/session_store.py` | 内存 Session 管理（TTLCache + asyncio.Lock） |
| 新建 | `agent-server/app/core/agent/food_safety_agent.py` | Agno agent 定义和工厂函数 |
| 修改 | `agent-server/app/api/agent/models.py` | AgentRequest 新增 agent_type, session_id 字段 |
| 修改 | `agent-server/app/api/agent/router.py` | 按 agent_type 路由到 food_safety_agent |
| 新建 | `agent-server/tests/core/agent/test_skill_loader.py` | skill_loader 单元测试 |
| 新建 | `agent-server/tests/core/agent/test_session_store.py` | session_store 单元测试 |
| 新建 | `agent-server/tests/core/agent/test_food_safety_agent.py` | food_safety_agent 单元测试（mock Agno）|

---

## Task 1: Spike — DashScope + Agno 兼容性验证

> ⚠️ **本 Task 必须通过后才能继续后续 Task。** 验证结果决定工具封装方式。

**Files:**
- Create: `agent-server/spike/test_agno_dashscope.py`
- Modify: `agent-server/pyproject.toml`

- [ ] **Step 1: 添加 agno 和 cachetools 依赖**

在 `agent-server/` 目录下执行：

```bash
cd agent-server
uv add agno cachetools
```

预期：`pyproject.toml` 中出现 `agno` 和 `cachetools`，`uv lock` 通过，无依赖冲突。
若报冲突，检查 agno 与 langchain/deepagents 的版本约束，按需调整版本号。

- [ ] **Step 2: 创建 Spike 脚本目录和文件**

```bash
mkdir -p agent-server/spike
```

创建 `agent-server/spike/test_agno_dashscope.py`：

```python
"""
Spike：验证 DashScope qwen-plus + Agno 兼容性。
运行：cd agent-server && uv run python3 spike/test_agno_dashscope.py
需要在 .env 中配置 DASHSCOPE_API_KEY。
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
assert DASHSCOPE_API_KEY, "请在 .env 中配置 DASHSCOPE_API_KEY"


def run_test_1_single_sync_tool():
    """验证 1：单个同步工具调用"""
    from agno.agent import Agent
    from agno.models.openai.like import OpenAILike

    def get_food_info(food_name: str) -> str:
        """获取食品信息（模拟工具）"""
        return f"{food_name} 是一种常见食品。"

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        tools=[get_food_info],
        instructions="你是食品助手，用工具回答问题。",
    )

    response = agent.run("苯甲酸钠是什么？")
    print(f"✅ Test 1 通过：单同步工具调用\n响应：{response.content[:100]}\n")


def run_test_2_async_tool():
    """验证 2：async 工具调用"""
    from agno.agent import Agent
    from agno.models.openai.like import OpenAILike

    async def async_search(query: str) -> str:
        """模拟 async 工具"""
        await asyncio.sleep(0)
        return f"搜索结果：{query} 相关信息。"

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        tools=[async_search],
        instructions="用工具回答问题。",
    )

    response = agent.run("查询苯甲酸钠")
    print(f"✅ Test 2 通过：async 工具调用\n响应：{response.content[:100]}\n")


def run_test_3_parallel_tools():
    """验证 3：并行工具调用（两个工具在同一请求中被调用）"""
    from agno.agent import Agent
    from agno.models.openai.like import OpenAILike

    call_log = []

    def tool_a(query: str) -> str:
        """知识库检索"""
        call_log.append("tool_a")
        return f"知识库结果：{query}"

    def tool_b(query: str) -> str:
        """网络搜索"""
        call_log.append("tool_b")
        return f"网络结果：{query}"

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        tools=[tool_a, tool_b],
        instructions="同时使用 tool_a 和 tool_b 回答问题。",
    )

    response = agent.run("苯甲酸钠的安全性和最新新闻")
    print(f"调用的工具：{call_log}")
    parallel_ok = len(call_log) >= 2
    status = "✅" if parallel_ok else "⚠️ (仅调用了一个工具，可能为顺序调用)"
    print(f"{status} Test 3：并行工具调用\n响应：{response.content[:100]}\n")


if __name__ == "__main__":
    print("=== Agno + DashScope 兼容性 Spike ===\n")
    try:
        run_test_1_single_sync_tool()
    except Exception as e:
        print(f"❌ Test 1 失败：{e}\n")

    try:
        run_test_2_async_tool()
    except Exception as e:
        print(f"❌ Test 2 失败：{e}\n")

    try:
        run_test_3_parallel_tools()
    except Exception as e:
        print(f"❌ Test 3 失败：{e}\n")

    print("=== Spike 完成，请根据结果更新 spec 文档 ===")
```

- [ ] **Step 3: 运行 Spike**

```bash
cd agent-server
uv run python3 spike/test_agno_dashscope.py
```

- [ ] **Step 4: 根据结果决策并更新文档**

| 结果 | 处理方式 |
|------|---------|
| Test 1/2/3 全部 ✅ | 继续后续 Task，async 工具直接用 |
| Test 2 ❌（async 不支持）| 后续工具封装时将 async 工具包装为同步（`asyncio.run()` 或 `loop.run_until_complete()`）|
| Test 3 ⚠️（无并行）| 继续，Agno 顺序调用即可，功能等价 |
| Test 1 ❌（基础不兼容）| 停止，切换备选方案：LangGraph + LangChain tools |

将 Spike 结论（✅/❌ + 使用的 Agno 版本）更新到 spec 文档：
`agent-server/docs/superpowers/specs/2026-03-19-food-safety-assistant-agent-design.md`

- [ ] **Step 5: Commit**

```bash
git add agent-server/pyproject.toml agent-server/uv.lock agent-server/spike/test_agno_dashscope.py
git commit -m "spike: verify DashScope qwen-plus + Agno compatibility"
```

---

## Task 2: 创建 SkillLoader

**Files:**
- Create: `agent-server/app/core/agent/skill_loader.py`
- Create: `agent-server/tests/core/agent/test_skill_loader.py`

- [ ] **Step 1: 创建测试目录**

```bash
mkdir -p agent-server/tests/core/agent
touch agent-server/tests/core/agent/__init__.py
```

- [ ] **Step 2: 写失败测试**

创建 `agent-server/tests/core/agent/test_skill_loader.py`：

```python
"""
SkillLoader 单元测试：从目录加载 .md 文件并按文件名排序拼接。
"""
import os
import tempfile

import pytest

from app.core.agent.skill_loader import load_skills


def test_load_skills_returns_concatenated_content(tmp_path):
    """按文件名排序拼接所有 .md 文件内容"""
    (tmp_path / "02_routing.md").write_text("routing content", encoding="utf-8")
    (tmp_path / "01_role.md").write_text("role content", encoding="utf-8")
    (tmp_path / "03_format.md").write_text("format content", encoding="utf-8")

    result = load_skills(str(tmp_path))

    assert "role content" in result
    assert "routing content" in result
    assert "format content" in result
    # 顺序：01 -> 02 -> 03
    assert result.index("role content") < result.index("routing content")
    assert result.index("routing content") < result.index("format content")


def test_load_skills_ignores_non_md_files(tmp_path):
    """非 .md 文件应被忽略"""
    (tmp_path / "01_role.md").write_text("role content", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("should be ignored", encoding="utf-8")

    result = load_skills(str(tmp_path))

    assert "role content" in result
    assert "should be ignored" not in result


def test_load_skills_empty_dir_returns_empty_string(tmp_path):
    """空目录返回空字符串"""
    result = load_skills(str(tmp_path))
    assert result == ""


def test_load_skills_default_dir_exists():
    """默认目录 app/skills/food-safety/ 存在时可加载（不报错）"""
    # 此测试在技能文件创建后才有意义，此处仅验证不抛出 FileNotFoundError
    from app.core.agent.skill_loader import DEFAULT_SKILLS_DIR
    assert isinstance(DEFAULT_SKILLS_DIR, str)
    assert "food-safety" in DEFAULT_SKILLS_DIR
```

- [ ] **Step 3: 运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/agent/test_skill_loader.py -v
```

预期：`ModuleNotFoundError: No module named 'app.core.agent.skill_loader'`

- [ ] **Step 4: 实现 skill_loader.py**

创建 `agent-server/app/core/agent/skill_loader.py`：

```python
"""
SkillLoader：从目录读取 Markdown 技能文件并按文件名排序拼接为 system prompt。
"""
import os

DEFAULT_SKILLS_DIR = "app/skills/food-safety"


def load_skills(skills_dir: str = DEFAULT_SKILLS_DIR) -> str:
    """
    读取目录下所有 .md 文件，按文件名排序后拼接返回。

    Args:
        skills_dir: 技能文件目录路径

    Returns:
        所有技能文件内容按顺序拼接的字符串，文件间以两个换行分隔
    """
    if not os.path.isdir(skills_dir):
        return ""

    md_files = sorted(
        f for f in os.listdir(skills_dir) if f.endswith(".md")
    )

    parts = []
    for filename in md_files:
        filepath = os.path.join(skills_dir, filename)
        with open(filepath, encoding="utf-8") as f:
            parts.append(f.read())

    return "\n\n".join(parts)
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/agent/test_skill_loader.py -v
```

预期：4 个测试全部 PASSED

- [ ] **Step 6: Commit**

```bash
git add agent-server/app/core/agent/skill_loader.py agent-server/tests/core/agent/test_skill_loader.py agent-server/tests/core/agent/__init__.py
git commit -m "feat: add SkillLoader for markdown skill files"
```

---

## Task 3: 创建技能文件

**Files:**
- Create: `agent-server/app/skills/food-safety/01_food_safety_assistant.md`
- Create: `agent-server/app/skills/food-safety/02_intent_routing.md`
- Create: `agent-server/app/skills/food-safety/03_answer_format.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p agent-server/app/skills/food-safety
```

- [ ] **Step 2: 创建 01_food_safety_assistant.md**

```
agent-server/app/skills/food-safety/01_food_safety_assistant.md
```

内容：

```markdown
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
```

- [ ] **Step 3: 创建 02_intent_routing.md**

```
agent-server/app/skills/food-safety/02_intent_routing.md
```

内容：

```markdown
# 工具选择规则

根据用户问题的内容，选择合适的工具：

## 工具说明

- `knowledge_base`：检索国家食品安全标准知识库（ChromaDB），适合回答标准规定、成分安全性、添加剂用量等问题
- `web_search`：搜索互联网，**仅用于**查询品牌、企业、召回事件、舆情等时效性信息

## 选择规则

- 问题涉及"食品标准/成分安全/添加剂规定/是否合规/用量限制" → 调用 `knowledge_base`
- 问题涉及"品牌/企业/召回/新闻/事件/舆情/近期" → 仅调用 `web_search`，不调用 `knowledge_base`
- 问题同时涉及标准知识和品牌舆情 → 分别调用各自工具，在答案中分段呈现

## 无结果处理

- 所有已调用的工具均无结果时，直接输出无结果回复
- 不要因为无结果而调用其他工具尝试补救
```

- [ ] **Step 4: 创建 03_answer_format.md**

```
agent-server/app/skills/food-safety/03_answer_format.md
```

内容：

```markdown
# 输出格式规范

## 有结果时的标准格式

**结论**：[一句话通俗说明，直接回答用户的核心问题]

**依据**：[来自知识库的标准条款、数据或具体说明]

**来源**：[简短说明，如"信息来自国家食品安全标准知识库"或"信息来自网络搜索"]

## 无结果时

"抱歉，暂未找到关于「[用户询问的内容]」的相关信息，建议咨询专业机构或查阅官方标准文件。"

## 注意事项

- 不要在答案中提及工具名称（如 knowledge_base、web_search）
- 来源说明保持简短，不超过一句话
- 如果同时有知识库和网络搜索结果，分段呈现
```

- [ ] **Step 5: 验证 SkillLoader 可加载这三个文件**

```bash
cd agent-server
uv run python3 -c "
from app.core.agent.skill_loader import load_skills
result = load_skills()
print(f'加载成功，总字符数：{len(result)}')
print(result[:200])
"
```

预期：打印出合并后内容，第一行为 `# 食品安全助手`。

- [ ] **Step 6: Commit**

```bash
git add agent-server/app/skills/food-safety/
git commit -m "feat: add food-safety skill files (role/routing/format)"
```

---

## Task 4: Session 存储

**Files:**
- Create: `agent-server/app/core/agent/session_store.py`
- Create: `agent-server/tests/core/agent/test_session_store.py`

- [ ] **Step 1: 写失败测试**

创建 `agent-server/tests/core/agent/test_session_store.py`：

```python
"""
SessionStore 单元测试：内存 session 管理，LRU + TTL + asyncio.Lock。
"""
import asyncio
import pytest

from app.core.agent.session_store import SessionStore


@pytest.fixture
def store():
    return SessionStore(max_size=3, ttl_seconds=3600)


@pytest.mark.asyncio
async def test_get_or_create_creates_new_session(store):
    """不存在的 session_id 应创建新 session"""
    session = await store.get_or_create("abc")
    assert session is not None


@pytest.mark.asyncio
async def test_get_or_create_returns_same_session(store):
    """同一 session_id 返回同一对象"""
    s1 = await store.get_or_create("abc")
    s2 = await store.get_or_create("abc")
    assert s1 is s2


@pytest.mark.asyncio
async def test_get_or_create_unknown_id_creates_new(store):
    """未知 session_id（如重启后）静默创建新 session，不报错"""
    session = await store.get_or_create("nonexistent-id-after-restart")
    assert session is not None


@pytest.mark.asyncio
async def test_max_size_evicts_oldest(store):
    """超过 max_size 时，最旧的 session 被驱逐"""
    s1 = await store.get_or_create("id1")
    s2 = await store.get_or_create("id2")
    s3 = await store.get_or_create("id3")
    # 添加第 4 个，应驱逐 id1
    s4 = await store.get_or_create("id4")
    # id1 再次访问时，应创建新 session（不是原来的对象）
    s1_new = await store.get_or_create("id1")
    assert s1_new is not s1


@pytest.mark.asyncio
async def test_concurrent_access_same_id(store):
    """并发访问同一 session_id 不产生竞态条件"""
    results = await asyncio.gather(*[store.get_or_create("shared") for _ in range(10)])
    # 所有结果应是同一个对象
    assert all(r is results[0] for r in results)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/agent/test_session_store.py -v
```

预期：`ModuleNotFoundError: No module named 'app.core.agent.session_store'`

- [ ] **Step 3: 实现 session_store.py**

创建 `agent-server/app/core/agent/session_store.py`：

```python
"""
SessionStore：基于内存的 Agno session 存储，使用 cachetools + asyncio.Lock。
"""
import asyncio
import uuid
from typing import Any, Dict, Optional

from cachetools import TTLCache


class SessionStore:
    """
    管理 Agno Agent 的 session 对象。

    - 最多 max_size 个 session（LRU 驱逐）
    - ttl_seconds 内无访问的 session 自动清除
    - asyncio.Lock 保证并发安全
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 86400):
        self._cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: Optional[str] = None) -> Any:
        """
        获取已有 session 或创建新 session。

        Args:
            session_id: 客户端传入的 session ID；为 None 时自动生成

        Returns:
            session 对象（dict，供 Agno Agent 使用）
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        async with self._lock:
            if session_id not in self._cache:
                self._cache[session_id] = {"session_id": session_id, "history": []}
            return self._cache[session_id]

    async def clear(self, session_id: str) -> None:
        """清除指定 session"""
        async with self._lock:
            self._cache.pop(session_id, None)


# 全局单例
_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """获取全局 SessionStore 单例"""
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/agent/test_session_store.py -v
```

预期：5 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add agent-server/app/core/agent/session_store.py agent-server/tests/core/agent/test_session_store.py
git commit -m "feat: add in-memory SessionStore with TTL and asyncio.Lock"
```

---

## Task 5: Food Safety Agent

> ⚠️ **依赖 Task 1（Spike）结果**。若 Spike 显示 async 工具不支持，需在此 Task 中将 `knowledge_base` 包装为同步函数。

**Files:**
- Create: `agent-server/app/core/agent/food_safety_agent.py`
- Create: `agent-server/tests/core/agent/test_food_safety_agent.py`

- [ ] **Step 1: 写失败测试**

创建 `agent-server/tests/core/agent/test_food_safety_agent.py`：

```python
"""
FoodSafetyAgent 单元测试：验证 agent 创建和基本属性（mock Agno）。
不调用真实 DashScope API。
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.agent.food_safety_agent import create_food_safety_agent


@patch("app.core.agent.food_safety_agent.Agent")
@patch("app.core.agent.food_safety_agent.load_skills", return_value="mocked instructions")
def test_create_food_safety_agent_returns_agent(mock_load_skills, mock_agent_class):
    """create_food_safety_agent 应调用 load_skills 并创建 Agno Agent"""
    mock_agent_instance = MagicMock()
    mock_agent_class.return_value = mock_agent_instance

    agent = create_food_safety_agent()

    mock_load_skills.assert_called_once()
    mock_agent_class.assert_called_once()
    assert agent is mock_agent_instance


@patch("app.core.agent.food_safety_agent.Agent")
@patch("app.core.agent.food_safety_agent.load_skills", return_value="mocked instructions")
def test_create_food_safety_agent_uses_correct_instructions(mock_load_skills, mock_agent_class):
    """Agent 应使用 load_skills 返回的内容作为 instructions"""
    mock_agent_class.return_value = MagicMock()

    create_food_safety_agent()

    call_kwargs = mock_agent_class.call_args[1]
    assert call_kwargs.get("instructions") == "mocked instructions"


@patch("app.core.agent.food_safety_agent.Agent")
@patch("app.core.agent.food_safety_agent.load_skills", return_value="")
def test_create_food_safety_agent_registers_two_tools(mock_load_skills, mock_agent_class):
    """Agent 应注册 knowledge_base 和 web_search 两个工具"""
    mock_agent_class.return_value = MagicMock()

    create_food_safety_agent()

    call_kwargs = mock_agent_class.call_args[1]
    tools = call_kwargs.get("tools", [])
    assert len(tools) == 2
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/agent/test_food_safety_agent.py -v
```

预期：`ModuleNotFoundError: No module named 'app.core.agent.food_safety_agent'`

- [ ] **Step 3: 实现 food_safety_agent.py**

> 注意：`knowledge_base` 是 `async def`，`web_search` 是同步的。
> 若 Spike Task 1 显示 Agno 不支持 async 工具，用下面的 `_sync_knowledge_base` 包装。
> 若支持 async，直接传入 `knowledge_base` 即可。

创建 `agent-server/app/core/agent/food_safety_agent.py`：

```python
"""
食品安全 AI 助手 Agent（Agno + DashScope qwen-plus）。
"""
import asyncio
import logging
import os
from typing import Optional

from agno.agent import Agent
from agno.models.openai.like import OpenAILike

from app.core.agent.skill_loader import load_skills
from app.core.config import settings

logger = logging.getLogger(__name__)

_agent: Optional[Agent] = None


def _make_sync_knowledge_base():
    """
    将 async knowledge_base 工具包装为同步函数（Spike 发现 async 不支持时使用）。
    若 Spike 验证 async 可用，直接使用原始 knowledge_base 工具。
    """
    from app.core.tools.knowledge_base import knowledge_base as _kb

    def sync_knowledge_base(query: str, top_k: int = 5) -> str:
        """从知识库中检索与查询最相关的文档片段（国家标准等）。"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _kb.ainvoke({"query": query, "top_k": top_k}))
                    return future.result()
            else:
                return loop.run_until_complete(_kb.ainvoke({"query": query, "top_k": top_k}))
        except Exception as e:
            logger.warning(f"knowledge_base 工具调用失败: {e}")
            return "知识库检索失败。"

    return sync_knowledge_base


def _make_web_search_tool():
    """获取 web_search 工具函数（同步）。"""
    from app.core.tools.web_search import web_search_tool_function

    def web_search(query: str, num_results: int = 5) -> str:
        """
        搜索互联网，仅用于查询品牌、企业召回、食品安全事件等时效性信息。
        不用于查询标准知识。
        """
        try:
            return web_search_tool_function(query, num_results)
        except Exception as e:
            logger.warning(f"web_search 工具调用失败: {e}")
            return "网络搜索失败。"

    return web_search


def create_food_safety_agent() -> Agent:
    """
    创建食品安全 AI 助手 Agent。

    Returns:
        配置好的 Agno Agent 实例
    """
    instructions = load_skills()

    vector_search = _make_sync_knowledge_base()
    web_search = _make_web_search_tool()

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        instructions=instructions,
        tools=[vector_search, web_search],
    )

    return agent


def get_food_safety_agent() -> Agent:
    """获取全局 FoodSafetyAgent 单例（懒加载）"""
    global _agent
    if _agent is None:
        _agent = create_food_safety_agent()
    return _agent
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/agent/test_food_safety_agent.py -v
```

预期：3 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add agent-server/app/core/agent/food_safety_agent.py agent-server/tests/core/agent/test_food_safety_agent.py
git commit -m "feat: add FoodSafetyAgent with Agno + DashScope qwen-plus"
```

---

## Task 6: API 变更

**Files:**
- Modify: `agent-server/app/api/agent/models.py`
- Modify: `agent-server/app/api/agent/router.py`

- [ ] **Step 1: 写失败测试**

在 `agent-server/tests/core/agent/test_food_safety_agent.py` 末尾添加（或新建文件 `tests/api/agent/test_router.py`）：

```python
# 追加到 test_food_safety_agent.py 末尾，或新建 tests/api/agent/test_router.py

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def test_agent_request_accepts_agent_type_and_session_id():
    """AgentRequest 应接受 agent_type 和 session_id 字段"""
    from app.api.agent.models import AgentRequest

    req = AgentRequest(
        message="苯甲酸钠安全吗？",
        agent_type="food_safety",
        session_id="test-session-123",
    )
    assert req.agent_type == "food_safety"
    assert req.session_id == "test-session-123"


def test_agent_request_defaults_agent_type_to_none():
    """agent_type 缺省应为 None（向后兼容）"""
    from app.api.agent.models import AgentRequest

    req = AgentRequest(message="test")
    assert req.agent_type is None
    assert req.session_id is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/agent/test_food_safety_agent.py::test_agent_request_accepts_agent_type_and_session_id -v
```

预期：`ValidationError` 或 `AssertionError`，因为 `AgentRequest` 暂无这两个字段。

- [ ] **Step 3: 更新 AgentRequest 模型**

修改 `agent-server/app/api/agent/models.py`，添加两个可选字段：

```python
class AgentRequest(BaseModel):
    """Agent 对话请求"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    thread_id: Optional[str] = None          # 现有字段，保留（LangGraph agent 使用）
    agent_type: Optional[str] = None         # 新增：路由到哪个 agent（"food_safety" 或 None）
    session_id: Optional[str] = None         # 新增：Agno session ID（多轮对话）
    config: Optional[Dict[str, Any]] = None
```

- [ ] **Step 4: 更新 router.py 添加路由逻辑**

修改 `agent-server/app/api/agent/router.py`，在文件顶部添加 food_safety agent 单例，并在 `agent_chat` 中添加分支：

在全局变量区域添加：

```python
_food_safety_agent = None

def _get_food_safety_agent():
    global _food_safety_agent
    if _food_safety_agent is None:
        from app.core.agent.food_safety_agent import create_food_safety_agent
        _food_safety_agent = create_food_safety_agent()
    return _food_safety_agent
```

将 `agent_chat` 函数改为：

```python
@router.post("/chat", response_model=AgentResponse)
async def agent_chat(request: AgentRequest) -> AgentResponse:
    """
    Agent 对话。agent_type="food_safety" 时路由到食品安全助手（Agno）。
    """
    try:
        if request.agent_type == "food_safety":
            return await _handle_food_safety_chat(request)
        else:
            return await _handle_national_standard_chat(request)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_national_standard_chat(request: AgentRequest) -> AgentResponse:
    """现有 LangGraph agent 处理逻辑（不变）"""
    messages = _build_messages(request)
    thread_id = request.thread_id or "default"
    loop = asyncio.get_event_loop()
    state = await loop.run_in_executor(
        None,
        _invoke_agent_sync,
        messages,
        thread_id,
    )
    content = _extract_response_content(state)
    return AgentResponse(content=content or "", sources=None, tool_calls=None)


async def _handle_food_safety_chat(request: AgentRequest) -> AgentResponse:
    """食品安全助手（Agno）处理逻辑"""
    from app.core.agent.session_store import get_session_store

    store = get_session_store()
    session = await store.get_or_create(request.session_id)

    agent = _get_food_safety_agent()

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: agent.run(request.message, session_id=session["session_id"]),
    )

    content = response.content if hasattr(response, "content") else str(response)
    return AgentResponse(content=content or "", sources=None, tool_calls=None)
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/agent/test_food_safety_agent.py -v
```

预期：所有测试 PASSED（包括新增的 API 模型测试）

- [ ] **Step 6: 基本冒烟测试（可选，本地有 DASHSCOPE_API_KEY 时执行）**

```bash
cd agent-server
uv run python3 -c "
import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post('/api/agent/chat', json={
    'message': '苯甲酸钠是什么？',
    'agent_type': 'food_safety',
    'session_id': 'test-001'
})
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
"
```

- [ ] **Step 7: Commit**

```bash
git add agent-server/app/api/agent/models.py agent-server/app/api/agent/router.py
git commit -m "feat: route agent_type=food_safety to Agno FoodSafetyAgent"
```

---

## Task 7: 补充测试夹具文件

**Files:**
- Create: `agent-server/tests/core/agent/fixtures/sample_questions.json`
- Create: `agent-server/tests/core/agent/fixtures/expected_tool_calls.json`

- [ ] **Step 1: 创建 fixtures 目录**

```bash
mkdir -p agent-server/tests/core/agent/fixtures
```

- [ ] **Step 2: 创建 sample_questions.json**

```json
[
  {
    "id": "q1",
    "question": "苯甲酸钠安全吗？",
    "intent": "general_info",
    "expected_tools": ["knowledge_base"]
  },
  {
    "id": "q2",
    "question": "XX 品牌最近有没有食品安全召回事件？",
    "intent": "company_news",
    "expected_tools": ["web_search"]
  },
  {
    "id": "q3",
    "question": "苯甲酸钠的国标用量是多少，有没有健康风险？",
    "intent": "general_info",
    "expected_tools": ["knowledge_base"]
  },
  {
    "id": "q4",
    "question": "查询一个根本不存在的神秘添加剂XYZ999",
    "intent": "general_info",
    "expected_tools": ["knowledge_base"],
    "expected_fallback": true
  }
]
```

- [ ] **Step 3: 创建 expected_tool_calls.json**

```json
{
  "q1": {
    "should_call": ["knowledge_base"],
    "should_not_call": ["web_search"]
  },
  "q2": {
    "should_call": ["web_search"],
    "should_not_call": ["knowledge_base"]
  },
  "q3": {
    "should_call": ["knowledge_base"],
    "should_not_call": []
  },
  "q4": {
    "should_call": ["knowledge_base"],
    "should_not_call": ["web_search"],
    "fallback_expected": true
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add agent-server/tests/core/agent/fixtures/
git commit -m "test: add fixtures for food safety agent test scenarios"
```

---

## 完成检查清单

在所有 Task 完成后运行：

```bash
cd agent-server
uv run pytest tests/core/agent/ -v
```

预期：所有测试通过，无 FAILED。

关键验证点：
- [ ] `uv run pytest tests/core/agent/test_skill_loader.py -v` → 全 PASSED
- [ ] `uv run pytest tests/core/agent/test_session_store.py -v` → 全 PASSED
- [ ] `uv run pytest tests/core/agent/test_food_safety_agent.py -v` → 全 PASSED
- [ ] `POST /api/agent/chat` 不传 `agent_type` 时行为与原来一致（向后兼容）
- [ ] `POST /api/agent/chat` 传 `agent_type: "food_safety"` 时路由到 Agno agent

---

## 后续迭代（不在本计划范围）

- **迭代 2**：neo4j_query 真实实现（动态 Cypher + 白名单安全校验）
- **迭代 3**：pg_query 真实实现（PostgreSQL schema + 查询模板）
- session 持久化（Redis）
- 用户认证
