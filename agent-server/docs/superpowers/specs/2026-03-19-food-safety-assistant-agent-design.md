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
- "我每天吃多少克才会超标？"

---

## 设计决策

| 决策项 | 选择 | 原因 |
|--------|------|------|
| Agent 框架 | **Agno** | 内置 Neo4j、Python 执行、向量检索等工具；支持 OpenAI 兼容接口；无不必要的多 agent 抽象 |
| LLM 提供商 | **DashScope（通义千问）** | 成本低，已有 OpenAI 兼容接口配置 |
| 技能定义方式 | **Markdown 文件** | 非技术人员可维护；与现有 `app/skills/` 目录一致 |
| 信息权威优先级 | **国家标准优先** | GB 标准是法定依据，其他信息作补充参考 |
| 多轮对话 | **Agno 原生 session** | 无需额外实现，`session_id` 管理上下文 |
| 无结果兜底 | **直接告知用户** | Web search 结果真实性无法保证，不用于兜底 |
| Web search 定位 | **企业舆情/外围信息** | 专门用于查品牌召回、食品安全事件等，非科学文献补充 |

---

## 整体架构

```
app/skills/*.md
      ↓ SkillLoader（读文件 → 拼接 system prompt）
Agno Agent（DashScope 通义千问）
      ↓ 意图分析（LLM 基于 system prompt 指令判断）
      ↓ 按需并行调用工具
┌────────────────────────────────────────────────────────┐
│ vector_search │ neo4j_query │ pg_query │ web_search     │
│ (ChromaDB)    │ (动态Cypher)│ (癌症数据)│ (企业舆情)     │
│               │             │          │                │
│               │ python_exec │          │                │
│               │ (脚本执行)  │          │                │
└────────────────────────────────────────────────────────┘
      ↓ 结果汇总
答案生成：结论（通俗）→ 依据（专业）→ 来源摘要
      ↓
多轮对话记忆（Agno session）
```

---

## 意图分类体系

4 类意图，可组合触发：

| 意图标签 | 触发条件 | 调用工具 |
|---------|---------|---------|
| `compliance` | 涉及"是否允许/用量限制/合规" | vector_search + neo4j_query |
| `health_risk` | 涉及"健康/致癌/副作用/安全性" | pg_query + vector_search |
| `company_news` | 涉及"品牌/企业/召回/事件/舆情" | web_search |
| `data_analysis` | 涉及计算、数据分析、比较 | python_exec + 上述任意工具 |

---

## 技能文件结构

```
app/skills/
├── food_safety_assistant.md     # 角色定义、回答风格、数据源优先级规则
├── intent_routing.md            # 意图分析规则
└── answer_format.md             # 输出格式规范
```

### `food_safety_assistant.md` 核心内容

```markdown
# 食品安全助手

你是一个面向普通消费者的食品安全 AI 助手。

## 角色定位
- 权威依据：国家标准（GB 系列）是最高权威，其他信息作为补充
- 遇到矛盾信息时，以标准为准并说明差异
- 知识库无结果时，直接告知用户，不猜测、不推断

## 回答风格
先给结论（一句话通俗语言），再给依据（专业内容），最后附简短来源说明。
```

### `intent_routing.md` 核心内容

```markdown
# 意图路由规则

收到用户问题后，先判断意图再调用工具：
- 涉及"允许用量/是否合规/标准规定" → compliance
- 涉及"健康/致癌/副作用/对身体" → health_risk
- 涉及"品牌/企业/召回/新闻/事件" → company_news
- 涉及计算或数据分析 → data_analysis
- 意图可叠加，例如"苯甲酸钠致癌吗"同时触发 compliance + health_risk
```

### `answer_format.md` 核心内容

```markdown
# 输出格式规范

## 标准格式
**结论**：[一句话通俗说明]

**依据**：[标准条款 / 数据 / 研究说明]

**来源**：[简短来源说明，如"信息来自 GB2760-2024 及健康风险数据库"]

## 无结果时
"抱歉，暂未找到关于「XXX」的相关信息，建议咨询专业机构或查阅官方标准文件。"
```

---

## 工具层设计

| 工具 | 实现来源 | 说明 |
|------|---------|------|
| `vector_search` | 复用 `app/core/tools/knowledge_base.py` | 包装为 Agno 工具 |
| `neo4j_query` | 升级 `app/core/tools/neo4j_query.py` | 支持动态 Cypher 生成 |
| `pg_query` | 复用 `app/core/tools/postgres_query.py` | 直接包装 |
| `web_search` | 复用 `app/core/tools/web_search.py` | 直接包装 |
| `python_exec` | Agno 内置 PythonTools | 沙盒执行 |

**新增文件：**

```
app/core/agent/
├── food_safety_agent.py    # Agno agent 定义 + 工具注册
└── skill_loader.py         # 读取 app/skills/*.md 拼接 system prompt
```

`app/core/agent/factory.py` 新增 `create_food_safety_agent()` 工厂函数，与现有 agent 并存。

---

## 数据流

### 单次问答

```
用户输入
  ↓
Agno Agent（携带对话历史 + system prompt）
  ↓
LLM 分析意图 → 输出 tool_calls（可多个并行）
  ↓
并行执行工具 → 收集结果
  ↓
LLM 生成最终答案（结论 → 依据 → 来源摘要）
  ↓
返回用户
```

### 多轮对话

- Agno 原生 `session_id` 管理对话历史
- `POST /api/agent/chat` 请求体传入 `session_id`，后端通过 Agno session 自动维护上下文

---

## 错误处理

工具级隔离原则：单个工具失败不影响整体答案。

| 场景 | 处理方式 |
|------|---------|
| Neo4j 连接失败 | 该工具返回空结果，其他工具继续，答案中不提及 |
| Python 执行超时/异常 | 返回错误描述给 LLM，由 LLM 告知用户"计算失败" |
| Web search 超时 | 静默跳过，不影响主答案 |
| 所有工具均失败 | 触发无结果兜底提示 |

---

## 测试策略

沿用项目现有 TDD 风格，pytest + uv run。

```
tests/core/agent/
├── test_skill_loader.py          # 单元测试：Markdown 文件加载和拼接
├── test_food_safety_agent.py     # 集成测试：典型问题端到端验证
└── fixtures/
    ├── sample_questions.json     # 覆盖 4 类意图的测试问题集
    └── expected_tool_calls.json  # 预期工具调用组合
```

集成测试用 mock 替换实际 LLM 调用，只验证工具路由逻辑是否正确。

---

## API 变更

`POST /api/agent/chat` 请求体新增字段：

```json
{
  "message": "苯甲酸钠安全吗？",
  "session_id": "user-session-abc123"
}
```

新增路由或复用现有路由（由实现阶段决定）。

---

## 不在本次范围内

- 前端 UI 变更
- 现有 agent（国家标准查询 agent）的修改
- 知识库录入流程变更
- 用户认证/权限控制
