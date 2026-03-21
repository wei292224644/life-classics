# chunk-quality-reviewer API 迁移实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 chunk-quality-reviewer skill 的数据获取方式从读取本地 JSON 文件改为通过 HTTP API（`GET /api/chunks`）获取。

**Architecture:** 仅修改 `.claude/skills/chunk-quality-reviewer/SKILL.md`，替换 frontmatter description、参数解析、Phase 1 三个部分，并同步更新 Phase 4 的 chunk 标识逻辑和注意事项的重复抽样描述。Phase 2、Phase 3 完全不变。新实现通过 WebFetch tool 调用本地服务，支持分页拉取和抽样两条执行路径。

**Tech Stack:** Markdown skill 文件，WebFetch tool，`GET http://localhost:9999/api/chunks`

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | `.claude/skills/chunk-quality-reviewer/SKILL.md` |

变更点：
1. frontmatter `description` 字段——更新为 doc_id 参数描述
2. `## 参数解析` 章节——替换为 doc_id 参数
3. `## Phase 1：读取数据` 章节——替换为 API 获取逻辑
4. `## Phase 4` 中 chunk 标识描述（第 135 行）——更新为 section_path/id
5. `## 注意事项` 中的抽样说明——删除（已由 Phase 1 覆盖）

---

### Task 1: 更新 frontmatter description 和参数解析章节

**Files:**
- Modify: `.claude/skills/chunk-quality-reviewer/SKILL.md`（第 1-14 行）

- [ ] **Step 1: 替换 frontmatter description**

将第 3 行：
```
description: 评估知识库 chunk 的质量——是否最大化检索有效信息同时最小化噪音。用户提供 JSON 文件路径和字段路径，skill 通过对话式诊断分析 chunks 并输出问题清单、整体评估和改进建议。
```

替换为：
```
description: 评估知识库 chunk 的质量——是否最大化检索有效信息同时最小化噪音。用户提供 doc_id，skill 通过 API 获取该文档的 chunks，经对话式诊断分析后输出问题清单、整体评估和改进建议。
```

- [ ] **Step 2: 替换"## 参数解析"章节**

将当前内容（第 8-14 行）：

```markdown
## 参数解析

从 `ARGUMENTS` 中解析以下信息（用户在调用时以自然语言描述）：
- **JSON 文件路径**：包含 chunks 的文件路径
- **字段路径**：需要读取的字段（如 `node_output.final_chunks[*].content` 和 `.meta`）
- **标识字段**（可选）：用于标识 chunk 的字段名（如 `chunk_id`）；未指定时使用数组下标 `#0`、`#1`...
- **当前切分策略**（可选）：用户正在使用的策略名称（如 `heading_strategy`、`structured_strategy`）
```

替换为：

```markdown
## 参数解析

从 `ARGUMENTS` 中解析以下信息（用户在调用时以自然语言描述）：
- **doc_id**（必填）：要评估的文档 ID，用于通过 API 获取该文档下的所有 chunks
- **当前切分策略**（可选）：用户正在使用的策略名称（如 `heading_strategy`、`structured_strategy`）
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/chunk-quality-reviewer/SKILL.md
git commit -m "feat(skill): update chunk-quality-reviewer params to use doc_id"
```

---

### Task 2: 替换 Phase 1（核心改造）

**Files:**
- Modify: `.claude/skills/chunk-quality-reviewer/SKILL.md`（## Phase 1 章节）

- [ ] **Step 1: 定位并替换整个"## Phase 1：读取数据"章节**

将当前 Phase 1 章节（从 `## Phase 1：读取数据` 到 `## Phase 2：情境问诊` 之前的全部内容）替换为以下内容：

````markdown
## Phase 1：获取数据

使用 `WebFetch` tool 调用本地 API 获取指定文档下的所有 chunks。

服务地址固定为 `http://localhost:9999`，请求路径：`GET /api/chunks?doc_id=<doc_id>&limit=<limit>&offset=<offset>`

响应结构：
```json
{
  "chunks": [{ "id": "...", "content": "...", "metadata": {} }],
  "total": 123,
  "limit": 100,
  "offset": 0
}
```

`metadata` 包含字段：`doc_id`、`title`、`standard_no`、`doc_type`、`semantic_type`、`section_path`、`raw_content`

### 错误处理

**请求失败（非 200）：**
> "服务请求失败（HTTP [状态码]），请确认服务是否正常运行于 localhost:9999。"
然后停止。

**请求成功但 chunks 为空（total=0）：**
> "doc_id `[doc_id]` 下没有 chunks，请确认该文档已上传并完成处理。"
然后停止。

### 执行路径

**先发起一次请求**（`limit=100&offset=0`）读取 `total`，再根据 `total` 选择路径：

**路径 A：抽样（total > 50）**

不拉取全量，只发起两次请求：
1. `GET /api/chunks?doc_id=<doc_id>&limit=20&offset=0`，取前 20 个 chunks
2. `GET /api/chunks?doc_id=<doc_id>&limit=10&offset=<floor(total/2)>`，取中间段最多 10 个 chunks（超出范围时 API 自动截断返回剩余部分）

合并两次结果，共最多 30 个 chunks。

**路径 B：全量（total ≤ 50）**

第一次请求已取得全部 chunks（total ≤ 50 ≤ limit=100），直接使用该结果。

### chunk 字段映射

| 用途 | 字段 |
|------|------|
| chunk 标识（在问题清单中标识 chunk） | `metadata.section_path`（如有）；否则用 `id` |
| 分析正文 | `content` |
| 辅助信息 | `metadata`（作为分析上下文的参考） |

`metadata.semantic_type` 作为分析先验：类型为 `metadata` 的 chunk 通常信息密度低，在问题清单中注明"此 chunk 为文档元数据，信息密度低属预期行为"，而非视为缺陷。

### 成功提示

**抽样模式：**
> "已抽样 Y 个 chunks（共 X 个）。在开始评估前，我需要了解两个问题以确定评估重点。"

**全量模式：**
> "已读取 X 个 chunks。在开始评估前，我需要了解两个问题以确定评估重点。"
````

- [ ] **Step 2: 验证 Phase 1 内容正确**

阅读修改后的章节，逐项确认：
- [ ] 错误处理：区分了"非 200"与"total=0"两种情况
- [ ] 执行路径：total > 50 走抽样，total ≤ 50 走全量
- [ ] 抽样：两次请求，取前 20 + 中间最多 10，共最多 30 个
- [ ] 字段映射：section_path 作标识，semantic_type 作先验
- [ ] 成功提示：抽样和全量两种提示文案均已列出

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/chunk-quality-reviewer/SKILL.md
git commit -m "feat(skill): replace Phase 1 file-read with API fetch in chunk-quality-reviewer"
```

---

### Task 3: 更新 Phase 4 的 chunk 标识描述，删除注意事项中的重复抽样说明

**Files:**
- Modify: `.claude/skills/chunk-quality-reviewer/SKILL.md`（Phase 4 和注意事项）

- [ ] **Step 1: 更新 Phase 4 的 chunk 标识描述**

在 Phase 4 的"### 4.1 问题清单"小节，找到以下文字：

```
按严重程度分组，每条标注 chunk 标识（优先使用用户指定的标识字段值，否则用 `#下标`）、问题维度、具体表现。
```

替换为：

```
按严重程度分组，每条标注 chunk 标识（优先使用 `metadata.section_path`，否则用 `id`）、问题维度、具体表现。
```

- [ ] **Step 2: 删除注意事项中的重复抽样说明**

在"## 注意事项"章节，找到以下条目：

```
- chunks 数量超过 50 个时**必须**抽样检查（前 20 个 + 从中间段抽取 10 个），在输出开头注明："本次为抽样评估（共 X 个 chunks，抽取 30 个）"
```

直接删除该行（抽样逻辑已在 Phase 1 完整描述，此处重复且措辞不一致）。

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/chunk-quality-reviewer/SKILL.md
git commit -m "fix(skill): sync Phase 4 chunk id format and remove duplicate sampling note"
```
