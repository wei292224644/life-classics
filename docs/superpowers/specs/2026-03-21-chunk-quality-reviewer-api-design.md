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
| `doc_id` | 是 | 要评估的文档 ID（字符串，直接拼入 URL，WebFetch 时需 URL 编码） |
| 当前切分策略 | 否 | 用于改进建议方向，与原版相同 |

移除：JSON 文件路径、字段路径、标识字段（这些参数不再需要，API 已提供结构化字段）。

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
- `metadata` 包含字段：`doc_id`、`title`、`standard_no`、`doc_type`、`semantic_type`、`section_path`、`raw_content`

### 执行路径判断

先发起一次请求读取 `total`，再根据 `total` 选择路径：

```
if total > 50:
    走抽样路径（见"抽样策略"小节，共 2 次请求，取 30 个 chunks）
else:
    走全量路径（total <= 50，单次请求即可，无需分页）
```

全量路径下，若 `total > 100`（理论上不触发，因为已被抽样路径截断），则需分页拉取，从 `offset=100` 开始循环，每次 offset += 100，直到取完所有 chunks，再合并为完整列表。

### chunk 字段映射

| 用途 | 字段 |
|------|------|
| chunk 标识（显示给用户） | `metadata.section_path`（如有）；否则用 `id` |
| 分析正文 | `content` |
| 辅助信息 | `metadata`（整体传入分析上下文） |

`metadata.semantic_type` 作为分析时的先验参考（例如类型为 `metadata` 的 chunk 通常信息密度低，可在问题清单中注明而非视为缺陷）。

### 错误处理

区分两种情况：

- **接口返回非 200**：
  > "服务请求失败（HTTP [状态码]），请确认服务是否正常运行于 localhost:9999。"
  然后停止。

- **接口返回 200 但 chunks 列表为空（total=0）**：
  > "doc_id `[id]` 下没有 chunks，请确认该文档已上传并完成处理。"
  然后停止。

### 抽样策略（total > 50 时）

当 total > 50 时，**不拉取全量数据**，只发起两次请求：
1. 第一次：`offset=0&limit=20`，取前 20 个 chunks
2. 第二次：`offset=floor(total/2)&limit=10`，取中间段最多 10 个 chunks（若 offset 超出范围，API 自行截断返回剩余部分）

共抽取最多 30 个，在分析开头注明："本次为抽样评估（共 X 个 chunks，抽取 Y 个）"。

### 成功提示（与原版一致）

> "已读取 X 个 chunks。在开始评估前，我需要了解两个问题以确定评估重点。"

## 不变部分

- Phase 2：情境问诊（Q1 查询类型 + Q2 文档结构类型）
- Phase 3：六维度分析（自包含性、语义完整性、信息密度、主题聚焦性、上下文可理解性、结构完整性）
- Phase 4：三层输出（问题清单、整体质量评估、改进建议）
