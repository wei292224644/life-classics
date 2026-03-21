# chunk-quality-reviewer Skill 改造设计

**日期：** 2026-03-21
**状态：** 已审阅

## 背景

chunk-quality-reviewer skill 原来通过读取本地 JSON 文件获取 chunks。现在知识库数据只能通过 HTTP API 获取，需要改造 Phase 1（数据获取）以适配接口。

## 变更范围

**仅改造 Phase 1（参数解析 + 数据获取）**，Phase 2（情境问诊）、Phase 3（多维分析）、Phase 4（三层输出）完全不变。

## 新参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `doc_id` | 是 | 要评估的文档 ID |
| 当前切分策略 | 否 | 用于改进建议方向，与原版相同 |

移除：JSON 文件路径、字段路径、标识字段（这些参数不再需要）。

## Phase 1 新实现

### 接口信息

- 地址：`http://localhost:9999/api/chunks`（固定，服务始终在本地运行）
- 方法：`GET`
- 参数：`doc_id`、`limit`（最大 100）、`offset`
- 响应结构：
  ```json
  {
    "chunks": [{ "id": "...", "content": "...", "metadata": {} }],
    "total": 123,
    "limit": 100,
    "offset": 0
  }
  ```

### 分页逻辑

1. 调用 `GET /api/chunks?doc_id=<doc_id>&limit=100&offset=0`
2. 读取 `total`，计算需要的分页次数：`ceil(total / 100)`
3. 循环请求直到取完所有 chunks（每次 offset += 100）
4. 用 `id` 作为 chunk 标识，`content` 作为正文，`metadata` 作为 meta

### 错误处理

若接口返回非 200 或 chunks 列表为空，输出：
> "无法获取 chunks，请确认服务已启动且 doc_id `[id]` 存在。"
然后停止。

### 成功提示（与原版一致）

> "已读取 X 个 chunks。在开始评估前，我需要了解两个问题以确定评估重点。"

## 不变部分

- Phase 2：情境问诊（Q1 查询类型 + Q2 文档结构类型）
- Phase 3：六维度分析（自包含性、语义完整性、信息密度、主题聚焦性、上下文可理解性、结构完整性）
- Phase 4：三层输出（问题清单、整体质量评估、改进建议）
- 超过 50 个 chunks 时的抽样策略
