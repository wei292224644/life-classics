# 食品安全 AI 助手 Agent 设计文档

**日期**：2026-03-19
**状态**：已确认，待实现

---

## 背景

知识库已搭建完成，包含：
- **ChromaDB 向量知识库**：国家食品安全标准（GB 系列）文本 chunks
- **Neo4j 知识图谱**：GB2760-2024 食品添加剂使用标准，含大量关系型内容
- **PostgreSQL**：癌症相关健康风险数据
- **Web Search**：DuckDuckGo 搜索能力

现需在此基础上构建面向**普通消费者**的 AI 对话助手，能自动分析用户问题并通过多知识源专业作答。

---

## 目标用户与核心场景

**目标用户**：普通消费者，关心食品安全与健康影响。

**典型问题**：
- "苯甲酸钠安全吗？"
- "这个添加剂会致癌吗？"
- "XX 品牌最近有没有食品安全问题？"

---

## 前置条件：兼容性 Spike（实现前必须通过）

在编写任何业务代码之前，必须完成以下 Spike，结论写入本文档后方可继续。

**使用模型**：`qwen-plus`（明确支持 parallel function calling，qwen-turbo 不保证）

| 验证项 | 通过标准 |
|--------|---------|
| 依赖兼容性 | `agno` 成功加入 `pyproject.toml`，与现有 `langchain` / `deepagents` 无冲突，`uv lock` 通过 |
| 单工具调用 | Agno Agent 使用 DashScope qwen-plus 成功调用一个 FunctionTool 并返回结果 |
| Async 工具支持 | 现有 `async def` 工具（knowledge_base）在 Agno 中被正确调用（需确认 Agno 是否支持 async FunctionTool，或需包装为同步） |
| 并行工具调用 | 同一次请求中 Agno 触发 2 个以上工具并行执行 |

**Spike 失败处理**：
- 并行调用不兼容 → 改为顺序调用（性能下降，功能等价）
- 工具调用格式完全不兼容 → 重新评估框架（备选：LangGraph + LangChain tools）

---

## MVP 工具范围

**当前现实**：`neo4j_query` 和 `postgres_query` 工具尚未真实实现（桩）。

**MVP 迭代策略**：

| 迭代 | 工具 | 覆盖意图 |
|------|------|---------|
| MVP（本次）| vector_search + web_search | general_info + company_news |
| 迭代 2 | + neo4j_query（真实实现）| + compliance |
| 迭代 3 | + pg_query（真实实现 + schema）| + health_risk |

本文档仅覆盖 MVP 迭代，迭代 2/3 需要单独的实现计划。

---

## 设计决策

| 决策项 | 选择 | 原因 |
|--------|------|------|
| Agent 框架 | **Agno** | 内置工具库；支持 OpenAI 兼容接口；无多 agent 抽象开销 |
| LLM 提供商 | **DashScope qwen-plus** | 成本合理，支持 parallel function calling |
| 意图分类方式 | **Agno 自主工具选择** | instructions 中引导 Agent 选择工具，无需独立分类 LLM 调用 |
| 技能定义方式 | **Markdown 文件，数字前缀排序** | 非技术人员可维护；加载顺序明确 |
| 多轮对话 | **Agno 原生 session，内存存储** | MVP 可接受；LRU + TTL 防内存泄漏 |
| Session 并发安全 | **`asyncio.Lock`** | FastAPI 为 async 环境，使用协程锁 |
| 无结果兜底 | **直接告知用户** | 所有已激活工具均无结果时触发 |
| Web search 定位 | **company_news 专属，绝对排他** | 不与其他工具组合；即使组合意图出现，web_search 只在 company_news 为主导时触发 |
| python_exec | **不在本次范围** | 消费者场景暂无明确计算需求 |
| LangGraph 关系 | **并存** | 通过 `agent_type` 参数路由；`thread_id` 保留给现有 agent，新 agent 使用 `session_id` |

---

## 整体架构

```
app/skills/food-safety/*.md
      ↓ SkillLoader（按数字前缀排序 → 拼接为 instructions）
Agno Agent（DashScope qwen-plus）
      ↓ Agent 根据 instructions 自主选择工具
┌───────────────────────────────────────┐
│ vector_search（已实现）│ web_search    │
│ (ChromaDB)             │ (DuckDuckGo) │
└───────────────────────────────────────┘
      ↓ Agno 汇总工具结果后传回 LLM
答案生成：结论（通俗）→ 依据（专业）→ 来源摘要
      ↓
多轮对话记忆（Agno session，内存，asyncio.Lock + LRU 1000 + TTL 24h）
```

**模块依赖关系：**

```
app/core/agent/food_safety_agent.py
    ├── app/core/agent/skill_loader.py
    ├── app/core/tools/knowledge_base.py   (vector_search，需确认 async 兼容性)
    └── app/core/tools/web_search.py       (web_search)

app/core/agent/factory.py
    ├── create_national_standard_agent()   (现有，LangGraph，不变)
    └── create_food_safety_agent()         (新增，Agno)
```

---

## 意图与工具映射（MVP）

| 意图 | 触发特征 | 调用工具 |
|------|---------|---------|
| `general_info` | 通用食品安全咨询，或未明确分类 | vector_search |
| `company_news` | 涉及品牌/企业/召回/事件/舆情 | web_search（绝对排他，不与其他工具组合） |
| 组合 | 同时涉及多类（非 company_news）| 并行调用对应工具集合 |

**组合规则说明**：
- `general_info` 与 `company_news` 同时出现时，分别独立处理：先用 vector_search 回答知识问题，再用 web_search 回答舆情问题，在答案中分段呈现
- 所有已激活工具均无结果 → 兜底提示

---

## 技能文件结构

```
app/skills/food-safety/           ← 新建子目录，与现有 skills 结构保持一致
├── 01_food_safety_assistant.md   ← 角色定义、信息权威优先级
├── 02_intent_routing.md          ← 工具选择引导规则
└── 03_answer_format.md           ← 输出格式规范
```

数字前缀确保 SkillLoader 按正确逻辑顺序加载（角色定义 → 路由规则 → 输出格式）。

### `01_food_safety_assistant.md`

```markdown
# 食品安全助手

你是一个面向普通消费者的食品安全 AI 助手。

## 信息权威优先级
- 国家标准（GB 系列）是最高权威，其他信息作为补充
- 当工具结果之间存在矛盾时：以国家标准内容为准，同时向用户说明其他来源的不同观点
- 知识库无结果时，直接告知用户，不猜测、不推断
```

### `02_intent_routing.md`

```markdown
# 工具选择规则

根据用户问题选择工具：
- 涉及食品标准、成分安全、添加剂规定 → 调用 vector_search
- 涉及品牌/企业/召回/新闻/事件/舆情 → 仅调用 web_search，不调用其他工具
- 问题同时涉及多类特征（不含舆情）→ 同时调用对应工具
- 所有工具均无结果时，直接输出无结果回复，不再调用其他工具
```

### `03_answer_format.md`

```markdown
# 输出格式

## 标准回答
**结论**：[一句话通俗说明]
**依据**：[标准条款 / 数据 / 具体说明]
**来源**：[简短说明，如"信息来自国家食品安全标准知识库"]

## 无结果时
"抱歉，暂未找到关于「XXX」的相关信息，建议咨询专业机构或查阅官方标准文件。"
```

---

## 新增文件

```
app/core/agent/
├── food_safety_agent.py    # Agno agent 定义、工具注册、工厂函数
└── skill_loader.py         # 读取 app/skills/food-safety/*.md，排序拼接
```

### `skill_loader.py` 接口

```python
DEFAULT_SKILLS_DIR = "app/skills/food-safety"

def load_skills(skills_dir: str = DEFAULT_SKILLS_DIR) -> str:
    """读取目录下所有 .md 文件，按文件名排序后拼接返回。"""
```

### `food_safety_agent.py` 核心结构

```python
def create_food_safety_agent() -> Agent:
    instructions = load_skills()
    return Agent(
        model=DashScope(id="qwen-plus"),
        instructions=instructions,
        tools=[vector_search_tool, web_search_tool],
    )
```

---

## Session 管理

- **存储**：内存，使用 `cachetools.LRUCache`（最多 1000 个 session）+ `asyncio.Lock` 保证并发安全
- **TTL**：24 小时无活动后清除（可通过 `cachetools.TTLCache` 或手动维护时间戳）
- **session_id**：
  - 客户端首次请求时生成 UUID4 并传入，后续请求携带同一 ID
  - 客户端不传 → 服务端自动生成（单轮对话模式，无历史）
  - session_id 不存在（如服务重启后）→ 静默创建新 session，不报错
- **与 thread_id 的区别**：现有 LangGraph agent 使用 `thread_id`，新 Agno agent 使用 `session_id`；两者独立，无关联

---

## 数据流

```
用户输入 + session_id（可选）
  ↓
查找或创建 Agno session（asyncio.Lock 保护）
  ↓
Agno Agent（携带对话历史 + instructions）
  ↓
LLM 根据 instructions 自主选择工具调用（可并行）
  ↓
Agno 汇总所有工具结果后传回 LLM
  ↓
LLM 生成最终答案（结论 → 依据 → 来源摘要）
  ↓
返回用户 + 更新 session 历史
```

---

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 单个工具异常或超时 | 捕获，视为空结果继续；记录 WARNING 日志 |
| 所有工具均无结果 | LLM 输出兜底提示 |
| DashScope 速率限制（429）| 不重试；Agno 异常向上冒泡，FastAPI 捕获后返回 HTTP 503 |
| LLM 调用失败（网络等）| Agno 异常向上冒泡，FastAPI 捕获后返回 HTTP 502 |

---

## API 变更

`POST /api/agent/chat` 请求体新增字段（向后兼容）：

```json
{
  "message": "苯甲酸钠安全吗？",
  "agent_type": "food_safety",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_type` | string，可选 | 缺省时路由现有 LangGraph agent（向后兼容，使用 `thread_id`） |
| `session_id` | string，可选 | UUID4；缺省时服务端自动生成（单轮模式） |

---

## 测试策略

沿用项目现有 TDD 风格，pytest + `uv run`。测试在 Spike 完成后根据 Agno 实际 API 细化。

```
tests/core/agent/
├── test_skill_loader.py          # 纯单元测试：文件加载、排序、拼接
├── test_food_safety_agent.py     # 单元测试：mock Agno + 工具，验证路由逻辑
└── fixtures/
    ├── sample_questions.json     # 覆盖所有意图 + 组合意图 + 无结果场景
    └── expected_tool_calls.json  # 预期工具调用组合
```

**测试分层**：
- `test_skill_loader.py`：无外部依赖，CI 可直接运行
- `test_food_safety_agent.py`：mock Agno Agent 和所有工具，不真实调用 DashScope；具体 mock 点在 Spike 后根据 Agno API 确定
- 真实 DashScope 集成测试仅在本地手动执行，不纳入 CI

**场景覆盖**：
- 单意图（general_info、company_news）
- 多意图组合
- 所有工具空结果 → 兜底回复
- 单个工具异常 → 其他工具正常
- 多轮上下文保持（session 历史）
- session_id 不存在 → 静默创建新 session

---

## 不在本次范围内

- neo4j_query 真实实现（迭代 2）
- pg_query 真实实现及 PostgreSQL schema（迭代 3）
- python_exec 工具
- 前端 UI 变更
- 现有 LangGraph agent 修改
- Session 持久化（Redis/DB）
- 用户认证/权限控制
