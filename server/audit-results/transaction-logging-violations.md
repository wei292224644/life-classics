# 审计报告：事务边界（Section IV）与日志规范（Section IX）

**审计范围**: `server/` 下所有 `.py` 文件
**规范文件**: `docs/architecture/server-architecture.md`
**审计日期**: 2026-04-02

---

## Section IV — 事务边界违规

> 规则：事务在 L1（Router）开启/关闭；L2/L3 禁止 commit/rollback（只能操作）。

### 1. L3 Repository 层执行 commit — 5 处违规

#### `server/db_repositories/ingredient.py`

| 行号 | 问题 |
|------|------|
| 30 | `await self._session.commit()` — upsert 分支，更新已有记录后提交 |
| 36 | `await self._session.commit()` — upsert 分支，新建记录后提交 |
| 85 | `await self._session.commit()` — update_full 全量更新后提交 |
| 97 | `await self._session.commit()` — update_partial 部分更新后提交 |
| 107 | `await self._session.commit()` — soft_delete 软删除后提交 |

**说明**: `IngredientRepository` 位于 `db_repositories/`，属于 L3 层，以上 commit 均应移至 L1（Router 层通过 `session.commit()` 统一管理）。

---

#### `server/db_repositories/ingredient_analysis.py`

| 行号 | 问题 |
|------|------|
| 73 | `await self._session.commit()` — insert_new_version 写入新版本记录后提交 |

**说明**: L3 Repository 不应自行提交事务。

---

### 2. L1（api/）Service 层执行 commit — 1 处违规

#### `server/api/ingredient_alias/service.py`

| 行号 | 问题 |
|------|------|
| 44 | `await self._session.commit()` — create_alias 创建别名后提交 |
| 69 | `await self._session.commit()` — delete_alias 删除别名后提交 |

**说明**: 该文件位于 `api/ingredient_alias/service.py`，属于 L1 层。L1 层中只有 **Router** 可以管理事务提交/回滚，Service 子层不应自行调用 `session.commit()`。事务应在 Router 层（依赖注入的 session 生命周期）统一处理。

---

### 3. 非架构层文件（豁免）

以下文件的 commit/rollback 不计入违规：

| 文件 | 原因 |
|------|------|
| `server/scripts/seed_data.py` | 命令行脚本，不在 L1/L2/L3 架构层内 |
| `server/scripts/batch_upload.py` | 命令行脚本 |
| `server/kb/writer/fts_writer.py` | Infra 层（SQLite FTS 内 部事务），隔离于主 PostgreSQL 事务之外 |

---

## Section IX — 日志规范违规

> 规则：L3 禁止记录日志；L1 之外禁止记录异常栈。

### 1. L1 层记录异常栈 — 1 处违规

#### `server/api/shared.py`

| 行号 | 问题代码 | 说明 |
|------|----------|------|
| 11 | `logger.exception("API error %s [%d]: %s", code, status_code, str(exc))` | 使用 `exception()` 即 `exc_info=True`，会记录完整异常栈。Section IX 禁止在 L1 之外记录异常栈（此处虽在 L1，但异常栈泄露给外部调用方有安全风险，且规范的本意是异常栈不应跨越层边界传播）。应改用 `logger.error()` 仅记录上下文信息。 |

**修复建议**: 将 `logger.exception()` 改为 `logger.error()`，避免栈信息泄露。

---

### 2. 豁免的 Infra 层日志（不算违规）

以下文件属于 `workflow_parser_kb/` 和 `workflow_ingredient_analysis/`（Infra 层），日志记录属正常行为：

- `workflow_parser_kb/structured_gateway.py` — L2 业务编排
- `workflow_parser_kb/nodes/*.py` — 各 Parser 节点（Infra 实现）
- `workflow_ingredient_analysis/entry.py` — L2 入口
- `workflow_ingredient_analysis/nodes/*.py` — 各 Ingredient 分析节点
- `observability/middleware.py` — 可观测性基础设施

---

### 3. 命令行脚本日志（豁免）

| 文件 | 说明 |
|------|------|
| `scripts/batch_upload.py` | 使用 `logger.info/error/warning`，属运维脚本，正常行为 |

---

## 汇总

| 类别 | 违规数 | 严重程度 |
|------|--------|----------|
| L3 commit/rollback（db_repositories/） | 6 处 | 高 — 违反事务边界 |
| L1 service commit（api/ingredient_alias/service.py） | 2 处 | 高 — 违反 L1 事务管理规则 |
| L1 异常栈日志（api/shared.py） | 1 处 | 中 — 信息泄露风险 |
| **合计** | **9 处** | |

---

## 修复优先级建议

1. **P0**: `db_repositories/ingredient.py`（5处）+ `db_repositories/ingredient_analysis.py`（1处）— 将 commit 移除，改为 flush，由 L1 Router 统一提交
2. **P0**: `api/ingredient_alias/service.py`（2处）— 移除 service 层 commit，事务管理上收至 Router 层
3. **P1**: `api/shared.py`（1处）— 将 `logger.exception()` 改为 `logger.error()`
