# Product Analysis Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现从用户拍照到产品分析结果页的完整在线分析管道，包含 OCR、成分解析、配料库匹配、LangGraph 产品分析 Agent 及配套 API。（`workflow_ingredient_analysis` 离线 workflow 暂缓，见 Task 17）

**Architecture:** 四组件顺序管道（OCR → Parse → Match → Analyze）通过 Redis 任务状态机串联，对外暴露 `POST /api/analysis/start` + `GET /api/analysis/{task_id}/status` + `POST /api/analysis/feedback` 三个接口。产品级分析由 LangGraph 驱动的 4 节点 DAG 生成，成分级 `IngredientAnalysis` 假设已由离线 workflow 预先写库（未命中时以 `level="unknown"` 降级继续）。

**Tech Stack:** FastAPI, SQLAlchemy 2.x (Mapped/mapped_column), Alembic, Redis (aioredis), LangGraph, Instructor (结构化 LLM 输出), ChromaDB (Embedding 检索), PaddleOCR-VL-1.5 (独立服务)

**Specs:**
- [Product Analysis Data Schema Design](../specs/2026-03-31-product-analysis-schema-design.md)
- [Analysis Pipeline Spec](../specs/2026-03-31-analysis-pipeline-spec.md)
- [Product Analysis Agent Spec](../specs/2026-03-31-product-analysis-agent-spec.md)
- [Ingredient Analyses Workflow Spec](../specs/2026-03-31-ingredient-analyses-workflow-spec.md)

---

## 全局约定

- 所有异步数据库操作使用 `AsyncSession`（与 `database/session.py` 现有约定一致）
- 所有 LLM 调用通过 Instructor 做结构化输出，使用 `worflow_parser_kb/structured_llm/` 中已有的 `client_factory` 模式
- Redis key 格式：`analysis:{task_id}`，TTL 终态后 3600s
- 配置项统一在 `config.py` 的 `Settings` 类追加，通过 `.env` 读取
- 测试优先使用 unit test + mock，只有必要时才做集成测试
- 每个 Task 以 commit 结束

---

## 文件结构

```
server/
├── analysis/                          # [NEW] 分析管道核心模块
│   ├── __init__.py
│   ├── types.py                       # [NEW] 所有共享 TypedDict / Pydantic 类型
│   ├── redis_store.py                 # [NEW] Redis 任务状态机
│   ├── ocr_client.py                  # [NEW] 组件 1：OCR HTTP 客户端
│   ├── ingredient_parser.py           # [NEW] 组件 2：LLM 成分解析
│   ├── ingredient_matcher.py          # [NEW] 组件 3：Embedding 成分匹配
│   ├── pipeline.py                    # [NEW] 管道编排：串联四组件
│   └── product_agent/                 # [NEW] 组件 4：产品分析 Agent
│       ├── __init__.py
│       ├── types.py                   # [NEW] Agent 内部 State 及输出模型
│       ├── nodes.py                   # [NEW] 4 个 LangGraph 节点实现
│       └── graph.py                   # [NEW] LangGraph 编译图
├── workflow_ingredient_analysis/      # [TODO] 离线：IngredientAnalysis 生成 workflow（Task 17，暂缓）
├── db_repositories/
│   ├── product_analysis.py            # [NEW] ProductAnalysis DB 操作
│   └── ingredient_analysis.py         # [NEW] IngredientAnalysis DB 操作
├── api/
│   └── analysis/                      # [NEW] 分析 API 模块
│       ├── __init__.py
│       ├── models.py                  # [NEW] Pydantic 请求/响应模型
│       ├── service.py                 # [NEW] 服务层：触发管道、查询状态
│       └── router.py                  # [NEW] 路由：start / status / feedback
├── database/
│   └── models.py                      # [MODIFY] 追加 IngredientAnalysis、ProductAnalysis ORM
├── config.py                          # [MODIFY] 追加 OCR、Redis、Analysis 配置项
├── api/main.py                        # [MODIFY] 注册 analysis router
└── tests/
    ├── workflow_product_analysis/     # [NEW] 管道各组件 unit tests
    │   ├── __init__.py
    │   ├── test_redis_store.py
    │   ├── test_ocr_client.py
    │   ├── test_ingredient_parser.py
    │   ├── test_ingredient_matcher.py
    │   ├── test_pipeline.py
    │   └── product_agent/
    │       ├── __init__.py
    │       ├── test_nodes.py
    │       └── test_graph.py
    ├── workflow_ingredient_analysis/   # [TODO] 暂缓，Task 17
    ├── db_repositories/
    │   ├── test_product_analysis_repo.py  # [NEW]
    │   └── test_ingredient_analysis_repo.py  # [NEW]
    └── api/
        └── analysis/
            ├── __init__.py
            └── test_analysis_api.py   # [NEW]
```

---

## Task 1：配置项扩展

**目标：** 在 `config.py` 中追加所有新组件需要的配置项，确保全部可通过 `.env` 覆盖。

**文件：**
- Modify: `server/config.py`

**要追加的配置项：**

```python
# ── Redis ──────────────────────────────────────────────────────────────────
REDIS_URL: str = "redis://localhost:6379/0"
ANALYSIS_TASK_TTL_SECONDS: int = 3600  # 终态后任务记录保留时长

# ── OCR 服务 ────────────────────────────────────────────────────────────────
OCR_SERVICE_URL: str = "http://localhost:8100"  # PaddleOCR-VL-1.5 内部地址
OCR_TIMEOUT_SECONDS: int = 30

# ── Embedding 成分匹配 ──────────────────────────────────────────────────────
INGREDIENT_MATCH_THRESHOLD: float = 0.85  # 低于此相似度归入 unmatched

# ── 产品分析 Agent 模型选择 ─────────────────────────────────────────────────
ANALYSIS_DEMOGRAPHICS_MODEL: str = "qwen-plus"
ANALYSIS_SCENARIOS_MODEL: str = "qwen-plus"
ANALYSIS_ADVICE_MODEL: str = "qwen-plus"
ANALYSIS_VERDICT_MODEL: str = "qwen-max"

# ── references 白名单（逗号分隔）────────────────────────────────────────────
ANALYSIS_REFERENCES_ALLOWLIST: str = "GB 2760,GB 7718,GB 28050,GB 14880,GB 2762,GB 31650"

# ── 系统写库用户 ID ─────────────────────────────────────────────────────────
SYSTEM_USER_ID: str = "00000000-0000-0000-0000-000000000001"

# ── 离线 IngredientAnalysis workflow 模型（Task 17 暂缓，先占位）──────────
INGREDIENT_ANALYSIS_MODEL: str = "qwen-max"
INGREDIENT_ANALYSIS_VERSION: str = "v1"

# ── food_id 模糊匹配置信度阈值 ──────────────────────────────────────────────
FOOD_NAME_MATCH_THRESHOLD: float = 0.80
```

**步骤：**
- [ ] 在 `config.py` 的 `Settings` 类中追加上述字段
- [ ] 在 `server/.env.example`（或 `server/.env`）中同步记录示例值（如已存在 .env 则追加注释说明）
- [ ] 运行 `uv run python3 -c "from config import settings; print(settings.REDIS_URL)"` 确认读取正常
- [ ] commit: `feat(config): add analysis pipeline config fields`

---

## Task 2：ORM 模型 — IngredientAnalysis & ProductAnalysis

**目标：** 在 `database/models.py` 中追加两个新表的 SQLAlchemy ORM 模型。

**文件：**
- Modify: `server/database/models.py`

**IngredientAnalysis 模型字段（追加到 models.py）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `BigInteger PK` | 主键 |
| `ingredient_id` | `BigInteger FK→ingredients.id` | 对应配料（无 UNIQUE，允许 append-only 多历史行） |
| `ai_model` | `String(255)` | 生成用的模型 ID |
| `version` | `String(50)` | 如 "v1" |
| `level` | `level_enum`（已有）| t0-t4 或 unknown |
| `safety_info` | `Text` | 安全摘要，喂给 ProductAgent |
| `alternatives` | `JSONB` | `[{better_ingredient_id: int, reason: str}]` |
| `confidence_score` | `Float` | 0.0-1.0 |
| `evidence_refs` | `JSONB` | `[{source_id, source_type, ...}]` |
| `decision_trace` | `JSONB` | 推理过程记录 |
| `is_active` | `Boolean default=True` | 同 ingredient_id 下只一个 active |
| `created_at` | `DateTime(tz=True)` | 创建时间 |
| `created_by_user` | `Uuid` | 写库用户（系统时用 SYSTEM_USER_ID） |
| `last_updated_at` | `DateTime(tz=True)` | 更新时间 |
| `last_updated_by_user` | `Uuid nullable` | 更新用户 |
| `deleted_at` | `DateTime(tz=True) nullable` | 软删除 |

**ProductAnalysis 模型字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `BigInteger PK` | 主键 |
| `food_id` | `BigInteger FK→foods.id UNIQUE` | 对应产品 |
| `ai_model` | `String(255)` | 生成用的模型 ID |
| `version` | `String(50)` | 如 "v1" |
| `level` | `level_enum` | 整体风险等级 |
| `description` | `Text` | verdict.description |
| `advice` | `Text` | 综合建议 |
| `demographics` | `JSONB` | `[{group, level, note}]` 5条 |
| `scenarios` | `JSONB` | `[{title, text}]` 1-3条 |
| `references` | `ARRAY(Text)` | 引用标准 |
| `created_at` | `DateTime(tz=True)` | |
| `created_by_user` | `Uuid` | |
| `last_updated_at` | `DateTime(tz=True)` | |
| `last_updated_by_user` | `Uuid nullable` | |
| `deleted_at` | `DateTime(tz=True) nullable` | |

**步骤：**
- [ ] 在 `models.py` 中追加 `IngredientAnalysis(Base)` 类
- [ ] 在 `models.py` 中追加 `ProductAnalysis(Base)` 类
- [ ] 运行 `uv run python3 -c "from database.models import IngredientAnalysis, ProductAnalysis; print('OK')"` 验证导入
- [ ] commit: `feat(db): add IngredientAnalysis and ProductAnalysis ORM models`

---

## Task 3：Alembic 数据库迁移

**目标：** 生成并应用 Alembic migration，在 PostgreSQL 中创建 `ingredient_analyses` 和 `product_analyses` 两张表。

**文件：**
- Create: `server/alembic/versions/<timestamp>_add_analysis_tables.py`（Alembic 自动生成）

**迁移内容（Alembic autogenerate 后人工确认）：**

- 创建 `ingredient_analyses` 表：含所有字段、`UNIQUE(ingredient_id)` 约束（注意：此约束需与 append-only 版本策略协商——若采用 append-only，此 UNIQUE 在历史版本实现中是否放宽？根据 spec §6.1，每个 ingredient_id + analysis_version 下最多一个 active，但 **不限制历史行数**，因此 `ingredient_analyses.ingredient_id` 不加 UNIQUE，改为在 `is_active=True` 下 `WHERE deleted_at IS NULL` 的唯一约束，或通过应用层保证）

  **实现决策：** 根据 spec "append-only 历史保留"，`ingredient_analyses` **不加** `UNIQUE(ingredient_id)`，允许多历史行，仅通过 `is_active=True` 标记当前有效行。

- 创建 `product_analyses` 表：含所有字段、`UNIQUE(food_id)` 约束（本版首写即缓存，一个 food_id 只允许一行）

- 注意：`level_enum` 在 PG 中已存在（已有 `level` 枚举），使用 `create_type=False`

**步骤：**
- [ ] 在 `server/` 目录确认 `alembic.ini` 和 `alembic/` 目录存在（若不存在则 `uv run alembic init alembic`）
- [ ] 检查 `alembic/env.py` 确认 `target_metadata = Base.metadata` 已配置
- [ ] 运行 `uv run alembic revision --autogenerate -m "add_analysis_tables"` 生成迁移文件
- [ ] 打开生成的迁移文件，确认两张表的 DDL 正确（特别是 JSONB、ARRAY、UNIQUE 约束）
- [ ] 更新 `database/models.py` 中 `IngredientAnalysis` 去掉 `UNIQUE(ingredient_id)`（根据上述决策），并重新 autogenerate
- [ ] 运行 `uv run alembic upgrade head` 应用迁移
- [ ] 验证：`uv run python3 -c "from database.session import get_async_session; print('OK')"` 
- [ ] commit: `feat(migration): add ingredient_analyses and product_analyses tables`

---

## Task 4：共享类型定义

**目标：** 在 `workflow_product_analysis/types.py` 中定义管道各组件间流转的所有数据类型，作为整个分析模块的类型中枢。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/types.py`

**需定义的类型（TypedDict + Literal）：**

```
RiskLevel = Literal["t0", "t1", "t2", "t3", "t4"]
IngredientRiskLevel = Literal["t0", "t1", "t2", "t3", "t4", "unknown"]
AnalysisStatus = Literal["ocr", "parsing", "analyzing", "done", "failed"]
AnalysisError = Literal["ocr_failed", "no_ingredients_found", "invalid_food_id", "analysis_failed"]

class IngredientInput(TypedDict):
    # 传给 ProductAgent 的单个成分数据
    ingredient_id: int          # 配料库主键（unmatched 成分为 0 或 None）
    name: str                   # 成分名
    category: str               # function_type 拼接
    level: IngredientRiskLevel
    safety_info: str            # 来自 IngredientAnalysis；未知成分为空字符串

class MatchedIngredient(TypedDict):
    ingredient_id: int
    name: str
    level: IngredientRiskLevel

class MatchResult(TypedDict):
    matched: list[MatchedIngredient]
    unmatched: list[str]        # 未匹配的原始成分名

class AlternativeItem(TypedDict):
    current_ingredient_id: int
    better_ingredient_id: int
    reason: str

class IngredientItem(TypedDict):
    # 结果页 ingredients[] 条目
    ingredient_id: int
    name: str
    category: str
    level: IngredientRiskLevel

class DemographicItem(TypedDict):
    group: str   # 固定枚举：普通成人|婴幼儿|孕妇|中老年|运动人群
    level: RiskLevel
    note: str

class ScenarioItem(TypedDict):
    title: str
    text: str

class ProductAnalysisResult(TypedDict):
    # 完整结果，对应 API 响应
    source: Literal["db_cache", "agent_generated"]
    ingredients: list[IngredientItem]
    verdict: dict                # {level: RiskLevel, description: str}
    advice: str
    alternatives: list[AlternativeItem]
    demographics: list[DemographicItem]
    scenarios: list[ScenarioItem]
    references: list[str]

class AnalysisTask(TypedDict):
    task_id: str
    status: AnalysisStatus
    error: AnalysisError | None
    result: ProductAnalysisResult | None
    created_at: str              # ISO 8601
    image_object_key: str | None # 对象存储 key，可选
```

**步骤：**
- [ ] 创建 `server/workflow_product_analysis/__init__.py`（空文件）
- [ ] 创建 `server/workflow_product_workflow_product_analysis/types.py`，定义上述所有类型
- [ ] 运行 `uv run python3 -c "from workflow_product_analysis.types import ProductAnalysisResult, AnalysisTask; print('OK')"`
- [ ] commit: `feat(analysis): add shared type definitions`

---

## Task 5：Redis 任务状态机

**目标：** 实现 `workflow_product_analysis/redis_store.py`，封装对 Redis 中分析任务 JSON 的读写，提供创建、更新、查询任务状态的接口。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/redis_store.py`
- Create: `server/tests/workflow_product_analysis/test_redis_store.py`

**函数签名与说明：**

```python
async def create_task(redis: Redis, task_id: str) -> AnalysisTask
# 在 Redis 中写入初始任务记录（status="ocr"，error=None，result=None）
# Key: analysis:{task_id}，不设 TTL（终态时由 set_task_done/failed 设置）
# 返回：新建的 AnalysisTask

async def get_task(redis: Redis, task_id: str) -> AnalysisTask | None
# 读取任务记录，JSON 反序列化后返回；key 不存在则返回 None

async def update_task_status(redis: Redis, task_id: str, status: AnalysisStatus) -> None
# 仅更新 status 字段，其余字段不变
# 用于 OCR 完成 → parsing、parsing 完成 → analyzing 的状态推进

async def set_task_done(redis: Redis, task_id: str, result: ProductAnalysisResult, ttl: int) -> None
# 将 status 置为 "done"，写入 result，并设置 TTL（秒）
# ttl 来自 settings.ANALYSIS_TASK_TTL_SECONDS

async def set_task_failed(redis: Redis, task_id: str, error: AnalysisError, ttl: int) -> None
# 将 status 置为 "failed"，写入 error，并设置 TTL

async def get_redis_client() -> Redis
# 返回已配置的 Redis 异步客户端（从 settings.REDIS_URL 读取）
# 作为 FastAPI dependency 使用
```

**测试要求（`test_redis_store.py`）：**

使用 `fakeredis` 或 mock，测试：
- `create_task` 写入正确的初始结构
- `get_task` 返回 None 当 key 不存在
- `update_task_status` 只改 status 不改其他字段
- `set_task_done` 正确写 result 并设 TTL
- `set_task_failed` 正确写 error 并设 TTL

**步骤：**
- [ ] 安装依赖：`cd server && uv add redis fakeredis`
- [ ] 创建 `server/workflow_product_workflow_product_analysis/redis_store.py`，实现上述 5 个函数
- [ ] 创建 `server/tests/workflow_product_analysis/__init__.py` 和 `server/tests/workflow_product_analysis/test_redis_store.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_redis_store.py -v`，确保全部通过
- [ ] commit: `feat(analysis): add Redis task state store`

---

## Task 6：组件 1 — OCR 客户端

**目标：** 实现 `workflow_product_analysis/ocr_client.py`，向独立部署的 PaddleOCR-VL-1.5 服务发送图片，返回原始 OCR 文字。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/ocr_client.py`
- Create: `server/tests/workflow_product_analysis/test_ocr_client.py`

**函数签名与说明：**

```python
async def run_ocr(image_bytes: bytes, settings: Settings) -> str
# 向 settings.OCR_SERVICE_URL 发送 multipart POST 请求，包含 image 字节流
# 超时：settings.OCR_TIMEOUT_SECONDS
# 成功：返回 OCR 原始文字字符串
# 失败（HTTP 错误 / 超时 / 网络异常）：raise OcrServiceError

class OcrServiceError(Exception):
    # 自定义异常，管道捕获后写入 status="failed", error="ocr_failed"
    pass
```

**PaddleOCR 服务接口约定（MVP 先假设）：**
- `POST {OCR_SERVICE_URL}/ocr`，multipart body `image=<bytes>`
- 响应 JSON：`{"text": "..."}`

**测试（`test_ocr_client.py`）：**

使用 `httpx.AsyncClient` mock（`respx` 或 `pytest-httpx`），测试：
- 正常 200 响应 → 返回 text 字符串
- HTTP 错误响应 → raise `OcrServiceError`
- 网络超时 → raise `OcrServiceError`

**步骤：**
- [ ] 安装：`uv add httpx respx`（若未安装）
- [ ] 创建 `server/workflow_product_workflow_product_analysis/ocr_client.py`，实现 `run_ocr` 和 `OcrServiceError`
- [ ] 创建 `server/tests/workflow_product_analysis/test_ocr_client.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_ocr_client.py -v`
- [ ] commit: `feat(analysis): add OCR client (component 1)`

---

## Task 7：组件 2 — LLM 成分解析

**目标：** 实现 `workflow_product_analysis/ingredient_parser.py`，用 LLM + Instructor 从 OCR 文字中提取成分名列表（兼做商品品名提取用于 food_id 匹配）。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/ingredient_parser.py`
- Create: `server/tests/workflow_product_analysis/test_ingredient_parser.py`

**函数签名与说明：**

```python
class ParseResult(TypedDict):
    ingredients: list[str]       # 成分名列表，如 ["燕麦粉", "麦芽糊精"]
    product_name: str | None     # 从 OCR 提取的商品品名，可能为 None

async def parse_ingredients(ocr_text: str, settings: Settings) -> ParseResult
# 使用已有 structured_llm 模块（worflow_parser_kb/structured_llm/client_factory）
# 向 LLM 发送 prompt，要求提取配料表成分名（去掉括号内功能说明）和商品品名
# 用 Instructor 保证结构化输出
# 若 LLM 返回空成分列表 → raise NoIngredientsFoundError

class NoIngredientsFoundError(Exception):
    # 管道捕获后写入 status="failed", error="no_ingredients_found"
    pass
```

**Instructor 结构化输出模型（在函数内定义）：**
```python
class IngredientParseOutput(BaseModel):
    ingredients: list[str]
    product_name: str | None = None
```

**使用的 LLM 配置：** 复用 `CLASSIFY_LLM_PROVIDER` + `CLASSIFY_MODEL`（或新增 `PARSE_LLM_MODEL`，以实现计划为准）

**测试（`test_ingredient_parser.py`）：**

Mock Instructor 客户端，测试：
- 正常返回 → `ParseResult` 结构正确
- LLM 返回空 ingredients → raise `NoIngredientsFoundError`
- 成分名去掉括号内容："阿斯巴甜（甜味剂）" → "阿斯巴甜"（若由 LLM 处理，mock LLM 返回正确格式即可）

**步骤：**
- [ ] 创建 `server/workflow_product_workflow_product_analysis/ingredient_parser.py`
- [ ] 创建 `server/tests/workflow_product_analysis/test_ingredient_parser.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_ingredient_parser.py -v`
- [ ] commit: `feat(analysis): add LLM ingredient parser (component 2)`

---

## Task 8：组件 3 — Embedding 成分匹配

**目标：** 实现 `workflow_product_analysis/ingredient_matcher.py`，将成分名列表通过向量检索匹配到配料库（`ingredients` 表），返回 matched + unmatched 结果。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/ingredient_matcher.py`
- Create: `server/tests/workflow_product_analysis/test_ingredient_matcher.py`

**函数签名与说明：**

```python
async def match_ingredients(
    ingredient_names: list[str],
    settings: Settings,
) -> MatchResult
# 对每个成分名：
#   1. 调用 kb/embeddings.py 中的 embedding 函数向量化
#   2. 在 ChromaDB 中做相似度检索（复用 kb/retriever/vector_retriever.py）
#   3. 若最高相似度 >= settings.INGREDIENT_MATCH_THRESHOLD：
#      - 查 DB 取对应 ingredient 的 id、name、function_type
#      - 读取该 ingredient 的 active IngredientAnalysis（level 字段）
#      - 归入 matched
#   4. 否则归入 unmatched
# 返回 MatchResult

async def fetch_ingredient_details(
    ingredient_id: int,
    session: AsyncSession,
) -> tuple[str, str, IngredientRiskLevel]
# 辅助函数：按 ingredient_id 查 DB
# 返回 (name, category_str, level)
# category_str 由 ingredient.function_type 数组拼接，如 "增稠剂 · 高升糖指数"
# level 来自该成分的 active IngredientAnalysis；无记录则返回 "unknown"
```

**注意：** ChromaDB collection 中的成分向量需预先建立（此 plan 不包含成分向量入库，假设已存在）。若 collection 为空，所有成分归入 unmatched（降级为 unknown，不报错）。

**测试（`test_ingredient_matcher.py`）：**

Mock ChromaDB 客户端和 DB session，测试：
- 相似度 >= 阈值 → 归入 matched，level 读取正确
- 相似度 < 阈值 → 归入 unmatched
- ingredient 无 IngredientAnalysis → level 为 "unknown"

**步骤：**
- [ ] 创建 `server/workflow_product_workflow_product_analysis/ingredient_matcher.py`
- [ ] 创建 `server/tests/workflow_product_analysis/test_ingredient_matcher.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_ingredient_matcher.py -v`
- [ ] commit: `feat(analysis): add embedding ingredient matcher (component 3)`

---

## Task 9：DB Repositories — ProductAnalysis & IngredientAnalysis

**目标：** 实现两个 repository 模块，封装对 `product_analyses` 和 `ingredient_analyses` 表的所有数据库操作。

**文件：**
- Create: `server/db_repositories/product_analysis.py`
- Create: `server/db_repositories/ingredient_analysis.py`
- Create: `server/tests/db_repositories/test_product_analysis_repo.py`
- Create: `server/tests/db_repositories/test_ingredient_analysis_repo.py`

**`product_analysis.py` 函数签名：**

```python
async def get_by_food_id(
    food_id: int,
    session: AsyncSession,
) -> ProductAnalysis | None
# 查询 product_analyses WHERE food_id = :food_id AND deleted_at IS NULL
# 返回 ORM 对象或 None

async def insert_if_absent(
    food_id: int,
    data: dict,              # 对应 ProductAnalysis 字段值
    created_by_user: str,    # SYSTEM_USER_ID
    session: AsyncSession,
) -> tuple[ProductAnalysis, Literal["inserted", "already_exists"]]
# 1. 先查 get_by_food_id
# 2. 有记录 → 返回 (existing, "already_exists")
# 3. 无记录 → INSERT，返回 (new_record, "inserted")
# 4. INSERT 触发 UniqueViolation（并发场景）→ 捕获后回读，返回 (existing, "already_exists")
```

**`ingredient_analysis.py` 函数签名：**

```python
async def get_active_by_ingredient_id(
    ingredient_id: int,
    session: AsyncSession,
) -> IngredientAnalysis | None
# 查询 ingredient_analyses WHERE ingredient_id = :id AND is_active = True AND deleted_at IS NULL
# 返回 ORM 对象或 None

async def insert_new_version(
    ingredient_id: int,
    data: dict,
    created_by_user: str,
    session: AsyncSession,
) -> IngredientAnalysis
# 1. 将该 ingredient_id 的所有 is_active=True 行置为 is_active=False
# 2. INSERT 新行 is_active=True
# 3. 返回新行
# append-only 语义：不删除历史行

async def get_history_by_ingredient_id(
    ingredient_id: int,
    session: AsyncSession,
) -> list[IngredientAnalysis]
# 查询该成分所有历史版本，按 created_at DESC 排序
```

**测试：** 使用 `pytest-asyncio` + `AsyncSession` mock（或 `sqlalchemy.ext.asyncio` 内存 SQLite），测试主要分支（命中、未命中、并发冲突）。

**步骤：**
- [ ] 创建 `server/db_repositories/product_analysis.py`
- [ ] 创建 `server/db_repositories/ingredient_analysis.py`
- [ ] 创建对应测试文件
- [ ] 运行 `uv run pytest tests/db_repositories/test_product_analysis_repo.py tests/db_repositories/test_ingredient_analysis_repo.py -v`
- [ ] commit: `feat(db): add ProductAnalysis and IngredientAnalysis repositories`

---

## Task 10：产品分析 Agent — 类型与节点

**目标：** 在 `workflow_product_analysis/product_agent/` 中定义 LangGraph State 和 4 个节点函数，每个节点通过 Instructor 调用 LLM 生成结构化输出。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/product_agent/__init__.py`
- Create: `server/workflow_product_workflow_product_analysis/product_agent/types.py`
- Create: `server/workflow_product_workflow_product_analysis/product_agent/nodes.py`
- Create: `server/tests/workflow_product_analysis/product_agent/test_nodes.py`

**`types.py` 定义：**

```python
class ProductAnalysisState(TypedDict):
    ingredients: list[IngredientInput]      # 输入（来自 workflow_product_analysis/types.py）
    demographics: list[DemographicItem] | None  # Node A 输出
    scenarios: list[ScenarioItem] | None        # Node B 输出
    advice: str | None                          # Node C 输出
    verdict_level: RiskLevel | None             # Node D 输出
    verdict_description: str | None             # Node D 输出
    references: list[str] | None               # Node D 输出（过滤后）

# Instructor Pydantic 输出模型（亦在此定义）
class DemographicsOutput(BaseModel):
    demographics: list[...]   # 固定 5 条

class ScenariosOutput(BaseModel):
    scenarios: list[...]      # 1-3 条

class AdviceOutput(BaseModel):
    advice: str

class VerdictOutput(BaseModel):
    level: RiskLevel
    description: str
    references: list[str]
```

**`nodes.py` 函数签名（4 个节点函数）：**

```python
async def demographics_node(state: ProductAnalysisState, settings: Settings) -> ProductAnalysisState
# 输入：state.ingredients
# 用 ANALYSIS_DEMOGRAPHICS_MODEL 调用 LLM，Instructor 输出 DemographicsOutput
# 返回：state with demographics 填充

async def scenarios_node(state: ProductAnalysisState, settings: Settings) -> ProductAnalysisState
# 输入：state.ingredients
# 用 ANALYSIS_SCENARIOS_MODEL 调用 LLM，Instructor 输出 ScenariosOutput
# 返回：state with scenarios 填充

async def advice_node(state: ProductAnalysisState, settings: Settings) -> ProductAnalysisState
# 输入：state.ingredients + state.demographics + state.scenarios
# 用 ANALYSIS_ADVICE_MODEL 调用 LLM，Instructor 输出 AdviceOutput
# 返回：state with advice 填充

async def verdict_node(state: ProductAnalysisState, settings: Settings) -> ProductAnalysisState
# 输入：state.ingredients + state.demographics + state.scenarios + state.advice
# 用 ANALYSIS_VERDICT_MODEL 调用 LLM，Instructor 输出 VerdictOutput
# 后处理：对 references 做白名单过滤（settings.ANALYSIS_REFERENCES_ALLOWLIST）
#   - 仅保留命中白名单的标准号，大小写/全半角归一化后匹配
#   - 未命中条目丢弃并打 warning 日志
# 返回：state with verdict_level, verdict_description, references 填充
```

**测试（`test_nodes.py`）：**

Mock Instructor 客户端，测试每个节点：
- 正常输出 → state 字段更新正确
- `verdict_node` 的 references 白名单过滤逻辑（有效标准号保留，无效丢弃，全部无效返回 `[]`）

**步骤：**
- [ ] 创建 `server/workflow_product_workflow_product_analysis/product_agent/__init__.py`
- [ ] 创建 `server/workflow_product_workflow_product_analysis/product_agent/types.py`
- [ ] 创建 `server/workflow_product_workflow_product_analysis/product_agent/nodes.py`，实现 4 个节点函数
- [ ] 创建 `server/tests/workflow_product_analysis/product_agent/__init__.py` 和 `test_nodes.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/product_agent/test_nodes.py -v`
- [ ] commit: `feat(analysis): add product analysis agent nodes`

---

## Task 11：产品分析 Agent — LangGraph 图编译

**目标：** 在 `workflow_product_analysis/product_agent/graph.py` 中将 4 个节点按 DAG 拓扑（A/B 并行 → C → D）编译为 LangGraph 图，并提供顶层调用入口。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/product_agent/graph.py`
- Create: `server/tests/workflow_product_analysis/product_agent/test_graph.py`

**函数签名：**

```python
def build_product_analysis_graph(settings: Settings) -> CompiledGraph
# 使用 StateGraph(ProductAnalysisState) 构建图：
#   - 添加 demographics_node、scenarios_node、advice_node、verdict_node 四个节点
#   - START → [demographics_node, scenarios_node]（并行）
#   - demographics_node, scenarios_node → advice_node（等待两者完成）
#   - advice_node → verdict_node → END
# 返回 compiled graph（可 .ainvoke）

async def run_product_analysis_agent(
    ingredients: list[IngredientInput],
    settings: Settings,
) -> dict
# 初始化 ProductAnalysisState，调用 graph.ainvoke
# 返回最终 state 中的关键字段：
#   {verdict_level, verdict_description, advice, demographics, scenarios, references}
# 若任意节点抛出异常 → raise ProductAgentError

class ProductAgentError(Exception):
    # 管道捕获后写入 status="failed", error="analysis_failed"
    pass
```

**测试（`test_graph.py`）：**

Mock 4 个节点函数，测试：
- `run_product_analysis_agent` 返回完整结构
- 节点异常 → 抛出 `ProductAgentError`

**步骤：**
- [ ] 创建 `server/workflow_product_workflow_product_analysis/product_agent/graph.py`
- [ ] 创建 `server/tests/workflow_product_analysis/product_agent/test_graph.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/product_agent/test_graph.py -v`
- [ ] commit: `feat(analysis): compile product analysis LangGraph`

---

## Task 12：结果组装器

**目标：** 实现 `workflow_product_analysis/assembler.py`，将管道各阶段产物（DB 记录 + MatchResult + Agent 输出）组装成 `ProductAnalysisResult`，供 API 层直接返回。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/assembler.py`
- Create: `server/tests/workflow_product_analysis/test_assembler.py`

**函数签名：**

```python
async def assemble_from_db_cache(
    product_analysis: ProductAnalysis,
    match_result: MatchResult,
    session: AsyncSession,
) -> ProductAnalysisResult
# source = "db_cache"
# ingredients[]: 从 match_result.matched 中取 ingredient_id，
#   查 Ingredient 表拼接 name、category (function_type join)、level
# alternatives[]: 从 matched 中 level >= t2 的成分取其 IngredientAnalysis.alternatives
# 其余字段（verdict, advice, demographics, scenarios, references）从 ProductAnalysis ORM 读取

async def assemble_from_agent_output(
    agent_output: dict,
    match_result: MatchResult,
    food_id: int,
    session: AsyncSession,
) -> ProductAnalysisResult
# source = "agent_generated"
# ingredients[]: 同上（从 match_result 组装）
# alternatives[]: 同上（从 IngredientAnalysis 读取）
# 其余字段来自 agent_output
```

**共用辅助函数（私有）：**
```python
async def _build_ingredients_list(match_result, session) -> list[IngredientItem]
async def _build_alternatives(matched_ingredients, session) -> list[AlternativeItem]
# 仅处理 level ∈ {t2, t3, t4} 的成分
```

**测试（`test_assembler.py`）：**

Mock DB session，测试：
- `assemble_from_db_cache` 返回正确的 `source: "db_cache"` 和字段映射
- `assemble_from_agent_output` 返回正确的 `source: "agent_generated"`
- alternatives 仅包含 level >= t2 的成分

**步骤：**
- [ ] 创建 `server/workflow_product_workflow_product_analysis/assembler.py`
- [ ] 创建 `server/tests/workflow_product_analysis/test_assembler.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_assembler.py -v`
- [ ] commit: `feat(analysis): add result assembler`

---

## Task 13：food_id 解析 — DB 查找与占位创建

**目标：** 实现管道中从「可选 food_id 参数 + OCR 品名」到确定性 food_id 的解析逻辑（spec §2.6）。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/food_resolver.py`
- Create: `server/tests/workflow_product_analysis/test_food_resolver.py`

**函数签名：**

```python
async def resolve_food_id(
    explicit_food_id: int | None,   # 来自请求参数
    product_name: str | None,       # 来自成分解析 ParseResult.product_name
    task_id: str,                   # 用于生成占位 barcode
    session: AsyncSession,
    settings: Settings,
) -> int
# 逻辑：
# 1. 若 explicit_food_id 不为 None：
#    - 查 foods WHERE id=explicit_food_id AND deleted_at IS NULL
#    - 存在 → 直接返回 food_id
#    - 不存在 → raise InvalidFoodIdError
# 2. 若 product_name 不为 None：
#    - 尝试模糊匹配：在 foods 表做 name LIKE 或 Embedding 检索（MVP 用 ILIKE）
#    - 唯一候选且相似度 >= settings.FOOD_NAME_MATCH_THRESHOLD → 返回该 food_id
# 3. 以上均未命中：
#    - 创建占位 Food 记录：barcode=f"PHOTO-{task_id}"，name=product_name or "未命名产品"
#    - meta 字段标记 source="photo_import"
#    - 返回新建的 food_id

class InvalidFoodIdError(Exception):
    # 管道捕获后写入 error="invalid_food_id"
    pass
```

**测试（`test_food_resolver.py`）：**

Mock DB session，测试：
- explicit_food_id 存在 → 直接返回
- explicit_food_id 不存在 → raise `InvalidFoodIdError`
- 无 explicit_food_id，品名匹配成功 → 返回匹配 food_id
- 无 explicit_food_id，品名无匹配 → 创建占位并返回新 food_id

**步骤：**
- [ ] 创建 `server/workflow_product_workflow_product_analysis/food_resolver.py`
- [ ] 创建 `server/tests/workflow_product_analysis/test_food_resolver.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_food_resolver.py -v`
- [ ] commit: `feat(analysis): add food_id resolver`

---

## Task 14：管道编排

**目标：** 实现 `workflow_product_analysis/pipeline.py`，将四组件串联为完整的异步任务函数，在 BackgroundTask 中执行，通过 Redis 实时更新状态。

**文件：**
- Create: `server/workflow_product_workflow_product_analysis/pipeline.py`
- Create: `server/tests/workflow_product_analysis/test_pipeline.py`

**函数签名：**

```python
async def run_analysis_pipeline(
    task_id: str,
    image_bytes: bytes,
    explicit_food_id: int | None,
    redis: Redis,
    session: AsyncSession,
    settings: Settings,
) -> None
# 完整管道，无返回值，通过 Redis 更新状态
#
# 执行流程（每步失败均调用 set_task_failed 后 return）：
#
# [异步旁路] 触发图片上传到对象存储（不 await，允许失败）
#
# 1. OCR（status 已是 "ocr"）
#    - run_ocr(image_bytes, settings)
#    - 失败 → set_task_failed(task_id, "ocr_failed", ttl); return
#
# 2. 解析（update_task_status → "parsing"）
#    - parse_ingredients(ocr_text, settings)
#    - 失败 → set_task_failed(task_id, "no_ingredients_found", ttl); return
#
# 3. resolve_food_id（status 仍 "parsing"）
#    - resolve_food_id(explicit_food_id, parse_result.product_name, task_id, session, settings)
#    - InvalidFoodIdError → set_task_failed(task_id, "invalid_food_id", ttl); return
#
# 4. 匹配 + 分析（update_task_status → "analyzing"）
#    - match_ingredients(parse_result.ingredients, settings)
#    - 查 product_analyses by food_id（get_by_food_id）
#      a. 命中 → assemble_from_db_cache；source="db_cache"
#      b. 未命中：
#         - 读取各 matched 成分的 IngredientAnalysis（get_active_by_ingredient_id）
#         - 构建 IngredientInput 列表（unmatched 成分 level="unknown", safety_info=""）
#         - run_product_analysis_agent(ingredient_inputs, settings)
#         - ProductAgentError → set_task_failed(task_id, "analysis_failed", ttl); return
#         - insert_if_absent(food_id, agent_output, SYSTEM_USER_ID, session)
#         - assemble_from_agent_output；source="agent_generated"
#
# 5. 完成
#    - set_task_done(task_id, product_analysis_result, ttl)

async def _upload_image_to_storage(
    task_id: str,
    image_bytes: bytes,
    settings: Settings,
) -> None
# 上传图片到对象存储（OSS/S3/MinIO），异步旁路，失败仅记 warning 日志
# key 格式：analysis_uploads/{yyyy}/{mm}/{task_id}.jpg
# MVP 可实现为 no-op（TODO 注释）
```

**测试（`test_pipeline.py`）：**

Mock 所有依赖（redis_store、ocr_client、ingredient_parser、ingredient_matcher、food_resolver、product_agent、assembler、product_analysis repo），测试：
- 正常 happy path → Redis 最终状态 "done"
- OCR 失败 → Redis 状态 "failed", error="ocr_failed"
- 无成分 → error="no_ingredients_found"
- invalid_food_id → error="invalid_food_id"
- Agent 失败 → error="analysis_failed"
- DB 缓存命中 → 跳过 Agent，source="db_cache"

**步骤：**
- [ ] 创建 `server/workflow_product_workflow_product_analysis/pipeline.py`
- [ ] 创建 `server/tests/workflow_product_analysis/test_pipeline.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_pipeline.py -v`
- [ ] commit: `feat(analysis): add pipeline orchestrator`

---

## Task 15：API 层 — 分析接口

**目标：** 实现 `api/analysis/` 模块，暴露三个端点：`POST /api/analysis/start`、`GET /api/analysis/{task_id}/status`、`POST /api/analysis/feedback`。

**文件：**
- Create: `server/api/analysis/__init__.py`
- Create: `server/api/analysis/models.py`
- Create: `server/api/analysis/service.py`
- Create: `server/api/analysis/router.py`
- Modify: `server/api/main.py`（注册 router）
- Create: `server/tests/api/analysis/__init__.py`
- Create: `server/tests/api/analysis/test_analysis_api.py`

**`models.py` — Pydantic 模型：**

```python
class StartAnalysisRequest(BaseModel):
    food_id: int | None = None   # 可选

class StartAnalysisResponse(BaseModel):
    task_id: str

class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: AnalysisStatus
    error: AnalysisError | None = None
    result: ProductAnalysisResult | None = None

class FeedbackRequest(BaseModel):
    task_id: str | None = None
    food_id: int
    category: Literal["ocr_wrong", "verdict_wrong", "ingredient_wrong", "other"]
    message: str | None = None
    client_context: dict | None = None

class FeedbackResponse(BaseModel):
    accepted: bool
```

**`service.py` — 服务层函数：**

```python
async def start_analysis(
    image_bytes: bytes,
    food_id: int | None,
    background_tasks: BackgroundTasks,
    redis: Redis,
    session: AsyncSession,
    settings: Settings,
) -> str
# 1. 生成 task_id（uuid4）
# 2. create_task(redis, task_id)
# 3. background_tasks.add_task(run_analysis_pipeline, task_id, image_bytes, food_id, redis, session, settings)
# 4. 返回 task_id

async def get_task_status(
    task_id: str,
    redis: Redis,
) -> AnalysisTask
# get_task(redis, task_id)
# task 不存在 → raise TaskNotFoundError（→ HTTP 404）

async def submit_feedback(
    req: FeedbackRequest,
    session: AsyncSession,
) -> None
# INSERT 到 analysis_feedback 表（Task 16 创建）
# 追加字段：created_at、source_ip_hash（从 Request 取）、user_agent

class TaskNotFoundError(Exception):
    pass
```

**`router.py` — 路由：**

```python
POST /api/analysis/start
  Content-Type: multipart/form-data
  Form fields: image (UploadFile), food_id (int, optional)
  Response: StartAnalysisResponse

GET /api/analysis/{task_id}/status
  Response: AnalysisStatusResponse
  404 if task not found

POST /api/analysis/feedback
  Body: FeedbackRequest (JSON)
  Response: FeedbackResponse
  限流：MVP 不强制，记录 IP hash 供后续限流
```

**`main.py` 修改：**
- 在 `app.include_router(...)` 中追加 `analysis_router`，前缀 `/api/analysis`

**测试（`test_analysis_api.py`）：**

使用 FastAPI TestClient + mock service：
- `POST /start` 正常 → 201 + task_id
- `GET /{task_id}/status` 命中 → 200 + AnalysisStatusResponse
- `GET /{task_id}/status` 未命中 → 404
- `POST /feedback` → 200

**步骤：**
- [ ] 创建 `server/api/analysis/` 目录及三个文件
- [ ] 修改 `server/api/main.py` 注册 router
- [ ] 创建测试文件
- [ ] 运行 `uv run pytest tests/api/analysis/test_analysis_api.py -v`
- [ ] 运行 `uv run python3 run.py`，打开 `http://localhost:9999/swagger` 确认三个端点可见
- [ ] commit: `feat(api): add analysis start/status/feedback endpoints`

---

## Task 16：feedback 持久化表

**目标：** 为用户反馈创建 `analysis_feedback` 表，支持 `POST /api/analysis/feedback` 写库。

**文件：**
- Modify: `server/database/models.py`（追加 `AnalysisFeedback` ORM）
- Create: Alembic migration

**`AnalysisFeedback` 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `BigInteger PK` | |
| `task_id` | `Uuid nullable` | 来自请求，可空 |
| `food_id` | `BigInteger FK→foods.id` | |
| `category` | `String(50)` | ocr_wrong / verdict_wrong / ingredient_wrong / other |
| `message` | `Text nullable` | |
| `client_context` | `JSONB nullable` | |
| `reporter_user_id` | `Uuid nullable` | 未登录可空 |
| `source_ip_hash` | `String(64) nullable` | SHA256 of IP |
| `user_agent` | `String(512) nullable` | |
| `created_at` | `DateTime(tz=True)` | |

**步骤：**
- [ ] 在 `database/models.py` 追加 `AnalysisFeedback` 类
- [ ] 运行 `uv run alembic revision --autogenerate -m "add_analysis_feedback"` 并检查
- [ ] 运行 `uv run alembic upgrade head`
- [ ] commit: `feat(db): add analysis_feedback table`

---

## Task 17：IngredientAnalysis 离线 Workflow（TODO — 暂缓实现）

> **状态：暂缓。** 当前 plan 先搭在线管道主架构（Task 1–16）。本 Task 仅作占位，不纳入当前实现批次。详细设计见 [Ingredient Analyses Workflow Spec](../specs/2026-03-31-ingredient-analyses-workflow-spec.md)。

**待实现范围（下一批次）：**
- `server/workflow_ingredient_analysis/` — 5 节点 LangGraph workflow（load_detail → check_idempotency → retrieve_evidence → analyze → compose_output → persist_version）
- 幂等检查（默认 skip，支持 force_rerun）
- append-only 版本写库
- Prometheus 可观测性指标（4 个 counter/histogram）
- 完整 unit tests

**步骤：**
- [ ] *(TODO)* 实现 `workflow_ingredient_analysis/` — 待后续批次

---

## Task 18：端对端冒烟测试

**目标：** 验证完整链路（无需真实 OCR 服务和 LLM）能在测试环境中走通。

**文件：**
- Create: `server/tests/workflow_product_analysis/test_e2e_smoke.py`

**测试场景：**

```python
async def test_pipeline_smoke_cached_food_id()
# 场景：food_id 已有 product_analyses 记录
# Mock: OCR 返回固定文本、parse_ingredients 返回固定列表
#       DB 中预置 ProductAnalysis 记录
# 验证：最终 Redis 状态为 done，result.source = "db_cache"

async def test_pipeline_smoke_agent_generated()
# 场景：food_id 无 product_analyses 记录
# Mock: 所有 LLM 调用返回固定结构
#       DB 中预置 IngredientAnalysis 记录
# 验证：最终 Redis 状态为 done，result.source = "agent_generated"，DB 有新行

async def test_pipeline_smoke_ocr_failure()
# Mock: OCR 服务抛出 OcrServiceError
# 验证：Redis 状态为 failed, error="ocr_failed"
```

**步骤：**
- [ ] 创建 `server/tests/workflow_product_analysis/test_e2e_smoke.py`
- [ ] 运行 `uv run pytest tests/workflow_product_analysis/test_e2e_smoke.py -v`
- [ ] commit: `test(analysis): add e2e smoke tests`

---

## 附录 A：未覆盖范围（下一版本）

以下内容在本 plan 中**不实现**：

1. **对象存储真实上传**：`_upload_image_to_storage` 实现为 no-op（TODO 注释），需待选型确定（OSS/S3/MinIO）后实现
2. **`product_analyses` 过期重算**：本版只读不 UPDATE，过期阈值与 stale-while-revalidate 留待下版
3. **反哺 FoodDetail**：spec §2.9，异步纠错非 MVP
4. **反馈接口限流**：MVP 只记 IP hash，不做强限流
5. **IngredientAnalysis workflow 的 CLI/HTTP 触发器**：workflow 本身已实现，触发方式（命令行 `--force`、admin API）单独实现
6. **成分向量入库**：假设 ChromaDB 中已有成分向量，入库逻辑不在本 plan 范围

---

## 附录 B：依赖安装汇总

在 `server/` 目录执行：

```bash
uv add redis fakeredis httpx respx langgraph instructor
```

若 `langgraph`、`instructor` 已在 `pyproject.toml` 中，跳过对应项。
