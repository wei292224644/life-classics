# Ingredient Analyses Workflow Spec

**Date:** 2026-03-31
**Status:** Draft
**Scope:** `ingredient_analyses` 的 workflow 内部设计与数据契约（不包含 CLI/API 触发方式）

---

## 1. 目标与边界

`ingredient_analyses` 负责把单条 `ingredient` 转换为可复用的 `IngredientAnalysis` 结构化结果，供 `product_analyses` 在线分析消费。

### 1.1 In Scope

- 基于 `ingredient` 的证据检索、推理、结构化输出
- 结果版本化（历史保留）与 active 版本切换
- 失败降级与可追溯信息（evidence/decision trace）

### 1.2 Out of Scope

- 外部触发方式（命令行、HTTP、定时任务）与参数解析
- 控制台页面交互与权限 UI
- 与 parser_kb 的实现细节（本 spec 仅约定依赖接口）
- 幂等跳过逻辑（由外部决定是否调用 workflow）

---

## 2. 上下游关系

```
ingredient
   -> ingredient_analyses workflow
       -> IngredientAnalysis(active)
           -> product_analyses workflow (在线消费，缺失则 unknown 降级)
```

- 上游输入实体：`ingredient`（由外部提供 `ingredient_id`，workflow 内部拉取）
- 下游消费方：`product_analyses`
- 约束：`product_analyses` 不依赖 `ingredient_analyses` 历史版本，只读取 active 版本

---

## 3. Workflow 输入输出契约

## 3.1 业务输入契约（内部 DTO）

```python
class IngredientAnalysisInput(TypedDict):
    ingredient_id: int
```

说明：

- `ingredient_id` 是唯一业务入口键，关联 `ingredients` 表

### 3.2 运行上下文（非业务字段）

```python
class RunContext(TypedDict):
    run_id: str
```

说明：

- workflow 仅消费该上下文，不负责解析外部命令或 HTTP 参数

### 3.3 输出契约（内部 DTO）

```python
class AlternativeItem(TypedDict):
    ingredient_id: int
    name: str
    reason: str


class IngredientAnalysisOutput(TypedDict):
    ingredient_id: int
    level: Literal["t0", "t1", "t2", "t3", "t4", "unknown"]
    safety_info: str
    alternatives: list[AlternativeItem]  # 仅 t2+ 有意义
    confidence_score: float  # [0, 1]，unknown 时为 0.0
    evidence_refs: list[dict[str, Any]]
    decision_trace: dict[str, Any]
    ai_model: str
    is_active: bool
```

约束：

- `unknown` 允许用于成分级结果
- `alternatives` 必须引用可追溯候选，不允许无来源自由生成
- `confidence_score` 范围 `[0, 1]`，证据不足导致 unknown 时为 `0.0`

---

## 4. 状态机与执行语义

## 4.1 状态枚举

- `queued`
- `running`
- `succeeded`
- `failed`

### 4.2 状态转移

```
queued -> running
running -> succeeded | failed
```

说明：幂等跳过逻辑由外部处理，不在 workflow 内部体现。

---

## 5. 核心节点设计

1. `load_ingredient_node`
   - 按 `ingredient_id` 拉取 `ingredient` 快照
   - 未找到 -> `failed(detail_not_found)`

2. `retrieve_evidence_node`
   - 从知识库检索证据，返回结构化 `evidence_refs`
   - 证据必须包含来源标识（source_id/source_type）
   - 知识库不可用 -> `failed(knowledge_base_unavailable)`
   - 知识库可用但无相关证据 -> `unknown` 降级，继续后续节点

3. `analyze_node`
   - 基于 ingredient + evidence 产出 `level`、`confidence_score`、`decision_trace`
   - 允许 `unknown` 作为证据不足时的合法结果

4. `compose_output_node`
   - 生成 `safety_info` 与 `alternatives`（遵循结构校验）

5. `persist_version_node`
   - append-only 写入新版本
   - 成功后将新记录置为 active，旧 active 置非 active

---

## 6. 版本与存储策略

## 6.1 版本策略

- 采用 append-only 历史保留
- 每个 `ingredient_id` 最多一个 active
- 重跑不覆盖历史记录，新增版本行并切 active

### 6.2 查询约定

- 默认查询 active 记录
- 回溯分析或调试时可按 `ingredient_id` 查看历史

---

## 7. 错误与降级

| error_code                  | 触发条件                               | 处理策略                                   |
| --------------------------- | -------------------------------------- | ---------------------------------------- |
| `ingredient_not_found`      | 输入 ID 无对应 ingredient               | 标记 failed                               |
| `knowledge_base_unavailable` | 知识库服务不可用                       | 标记 failed                               |
| `evidence_missing`          | 知识库可用但无相关证据                  | 降级为 `unknown` + succeeded（需 trace）  |
| `schema_invalid`            | 结构化输出校验失败                     | 标记 failed 或重试                        |
| `persist_failed`            | 写库失败                               | 标记 failed                               |

原则：

- 对业务可容忍缺失，优先 `unknown` 降级，不中断整体链路
- 对结构与持久化错误，不静默吞掉，必须失败并可观测

---

## 8. 与 product_analyses 的接口约定

`product_analyses` 仅消费以下字段：

- `level`
- `safety_info`
- `alternatives`
- `confidence_score`
- `evidence_refs`

当成分缺失 active `IngredientAnalysis` 时，`product_analyses` 以该成分 `level="unknown"` 降级继续，不触发整体失败。

---

## 9. 可观测性（最小集）

- `ingredient_analysis_run_total{status}` — status 枚举：`succeeded` | `failed`
- `ingredient_analysis_duration_ms`
- `ingredient_analysis_unknown_rate`
- `ingredient_analysis_force_rerun_total`（由外部记录，workflow 不感知）

日志必须包含：

- `ingredient_id`
- `run_id`
- `error_code`（失败时）

---

## 10. 设计决策记录

| 决策                     | 结论                      | 原因                                 |
| ------------------------ | ------------------------- | ------------------------------------ |
| workflow 是否感知调用方式 | 不感知                   | 保持核心编排与触发适配层解耦         |
| 入口键                   | `ingredient_id`           | 输入唯一、可追溯、避免前后端数据漂移 |
| 幂等策略                 | 外部控制                  | workflow 只负责执行，决策复杂度归外部 |
| 存储策略                 | append-only + active 版本 | 支持回溯、回滚与版本对比             |
| 缺证据行为               | 允许 `unknown`           | 保证下游产品分析可降级继续           |
| 版本机制                 | 不需要                   | 分析结果由 active 标识，版本字段冗余 |
