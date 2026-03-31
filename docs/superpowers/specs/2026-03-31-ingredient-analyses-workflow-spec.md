# Ingredient Analyses Workflow Spec

**Date:** 2026-03-31  
**Status:** Draft  
**Scope:** `ingredient_analyses` 的 workflow 内部设计与数据契约（不包含 CLI/API 触发方式）

---

## 1. 目标与边界

`ingredient_analyses` 负责把单条 `ingredient_detail` 转换为可复用的 `IngredientAnalysis` 结构化结果，供 `product_analyses` 在线分析消费。

### 1.1 In Scope

- 基于 `ingredient_detail` 的证据检索、推理、结构化输出
- 结果版本化（历史保留）与 active 版本切换
- 幂等策略与重跑语义（workflow 视角）
- 失败降级与可追溯信息（evidence/decision trace）

### 1.2 Out of Scope

- 外部触发方式（命令行、HTTP、定时任务）与参数解析
- 控制台页面交互与权限 UI
- 与 parser_kb 的实现细节（本 spec 仅约定依赖接口）

---

## 2. 上下游关系

```
ingredient_detail
   -> ingredient_analyses workflow
       -> IngredientAnalysis(active)
           -> product_analyses workflow (在线消费，缺失则 unknown 降级)
```

- 上游输入实体：`ingredient_detail`（由外部提供 `ingredient_detail_id`，workflow 内部拉取）
- 下游消费方：`product_analyses`
- 约束：`product_analyses` 不依赖 `ingredient_analyses` 历史版本，只读取 active 版本

---

## 3. Workflow 输入输出契约

## 3.1 业务输入契约（内部 DTO）

```python
class IngredientAnalysisInput(TypedDict):
    ingredient_detail_id: int
```

说明：

- `ingredient_detail_id` 是唯一业务入口键

### 3.2 运行上下文（非业务字段）

```python
class RunContext(TypedDict):
    run_id: str
```

说明：

- workflow 仅消费该上下文，不负责解析外部命令或 HTTP 参数

### 3.3 输出契约（内部 DTO）

```python
class IngredientAnalysisOutput(TypedDict):
    ingredient_detail_id: int
    level: Literal["t0", "t1", "t2", "t3", "t4", "unknown"]
    safety_info: str
    alternatives: list[dict[str, Any]]  # 仅 t2+ 有意义
    confidence_score: float
    evidence_refs: list[dict[str, Any]]
    decision_trace: dict[str, Any]
    analysis_version: str
    ai_model: str
    is_active: bool
```

约束：

- `unknown` 允许用于成分级结果
- `alternatives` 必须引用可追溯候选，不允许无来源自由生成

---

## 4. 状态机与执行语义

## 4.1 状态枚举

- `queued`
- `running`
- `succeeded`
- `failed`
- `skipped`

### 4.2 状态转移

```
queued -> running
running -> succeeded | failed | skipped
```

### 4.3 跳过与重跑

- 幂等键：`ingredient_detail_id + analysis_version`
- 当存在同键成功且 active 的记录 -> `skipped`
- 若外部适配层明确请求重跑（例如命令行 `--force`），workflow 直接走重跑分支并在成功后切换 active
- 重跑请求信号由适配层处理，不进入 workflow 业务输入与运行上下文字段

### 4.4 内部版本决议

- `analysis_version` 不由外部直接传入，由 workflow 内部版本决议器生成：
  - `analysis_version = resolve_version(model_id, prompt_version, ruleset_version)`
- 该版本参与幂等键计算，并写入输出与日志
- 目标：避免不同调用方传入不一致版本导致结果漂移

---

## 5. 核心节点设计

1. `load_detail_node`
   - 按 `ingredient_detail_id` 拉取 `ingredient_detail` 快照
   - 未找到 -> `failed(detail_not_found)`

2. `retrieve_evidence_node`
   - 从知识库检索证据，返回结构化 `evidence_refs`
   - 证据必须包含来源标识（source_id/source_type）

3. `analyze_node`
   - 基于 detail + evidence 产出 `level`、`confidence_score`、`decision_trace`
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
- 每个 `ingredient_detail_id` 在每个 `analysis_version` 下最多一个 active
- 重跑不覆盖历史记录，新增版本行并切 active

### 6.2 查询约定

- 默认查询 active 记录
- 回溯分析或调试时可按 `ingredient_detail_id` 查看历史

---

## 7. 错误与降级

| error_code             | 触发条件                 | 处理策略                                    |
| ---------------------- | ------------------------ | ------------------------------------------- |
| `detail_not_found`     | 输入 ID 无对应 detail    | 标记 failed                                 |
| `evidence_unavailable` | 知识库不可用或无可用证据 | 可降级为 `unknown` 并 succeeded（需 trace） |
| `schema_invalid`       | 结构化输出校验失败       | 标记 failed 或重试                          |
| `persist_failed`       | 写库失败                 | 标记 failed                                 |

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

- `ingredient_analysis_run_total{status,version}`
- `ingredient_analysis_duration_ms{version}`
- `ingredient_analysis_unknown_rate{version}`
- `ingredient_analysis_force_rerun_total{version}`

日志必须包含：

- `ingredient_detail_id`
- `analysis_version`
- `run_id`
- `error_code`（失败时）

---

## 10. 设计决策记录

| 决策                      | 结论                      | 原因                                 |
| ------------------------- | ------------------------- | ------------------------------------ |
| workflow 是否感知调用方式 | 不感知                    | 保持核心编排与触发适配层解耦         |
| 入口键                    | `ingredient_detail_id`    | 输入唯一、可追溯、避免前后端数据漂移 |
| 幂等策略                  | 默认跳过，支持 force 重跑 | 降低重复计算，同时保留人工纠偏能力   |
| 存储策略                  | append-only + active 版本 | 支持回溯、回滚与版本对比             |
| 缺证据行为                | 允许 `unknown`            | 保证下游产品分析可降级继续           |
