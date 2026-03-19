# Chunk Quality Reviewer Skill 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个 Claude Code skill 文件，通过对话式诊断帮助用户评估知识库 chunk 质量，发现切分噪音并给出改进建议。

**Architecture:** 单个 Markdown skill 文件，存放于 `~/.claude/skills/chunk-quality-reviewer/SKILL.md`。Skill 分三阶段执行：情境问诊（2 问）→ 多维度 chunk 分析（6 维度）→ 三层输出（问题清单 + 整体评分 + 改进建议）。

**Tech Stack:** Claude Code Skill（Markdown prompt 文件），无外部依赖，通过 `Read` tool 读取 JSON 文件。

---

## 文件结构

| 操作 | 路径 | 说明 |
|------|------|------|
| 创建 | `~/.claude/skills/chunk-quality-reviewer/SKILL.md` | Skill 主文件，包含完整的评估流程提示词 |

---

## Task 1：创建 skill 文件

**Files:**
- Create: `~/.claude/skills/chunk-quality-reviewer/SKILL.md`

- [ ] **Step 1：创建目录并写入 skill 文件**

在 `/Users/wwj/.claude/skills/chunk-quality-reviewer/SKILL.md` 创建以下内容：

````markdown
---
name: chunk-quality-reviewer
description: 评估知识库 chunk 的质量——是否最大化检索有效信息同时最小化噪音。用户提供 JSON 文件路径和字段路径，skill 通过对话式诊断分析 chunks 并输出问题清单、整体评估和改进建议。
---

你正在执行 chunk-quality-reviewer skill。请严格按以下步骤操作。

## 参数解析

从 `ARGUMENTS` 中解析以下信息（用户在调用时以自然语言描述）：
- **JSON 文件路径**：包含 chunks 的文件路径
- **字段路径**：需要读取的字段（如 `node_output.final_chunks[*].content` 和 `.meta`）
- **标识字段**（可选）：用于标识 chunk 的字段名（如 `chunk_id`）；未指定时使用数组下标 `#0`、`#1`...
- **当前切分策略**（可选）：用户正在使用的策略名称（如 `heading_strategy`、`structured_strategy`）

## Phase 1：读取数据

使用 `Read` tool 读取指定 JSON 文件。根据用户指定的字段路径，提取所有 chunks 的 `content` 和 `meta`（或用户指定的其他字段）。

字段路径支持两种格式：
- 点分路径：`node_output.final_chunks` → 按层级逐级访问
- 带 `[*]` 的数组展开：`node_output.final_chunks[*].content` → 提取数组中每个元素的指定字段

若读取失败或路径不存在，告知用户：
> "无法在文件中找到路径 `[路径]`，请检查路径是否正确。文件顶层字段为：[列出顶层 key]"
然后停止。

读取成功后，告知用户：
> "已读取 X 个 chunks。在开始评估前，我需要了解两个问题以确定评估重点。"

## Phase 2：情境问诊

**逐一提问，等待用户回答后再问下一题。**

**Q1（查询类型）：**
> 这个知识库主要用来回答哪类问题？
> - A. 事实查询（如某指标的限量值是多少）
> - B. 流程指导（如某检验方法的操作步骤）
> - C. 对比分析（如不同产品类别的指标对比）
> - D. 综合问答（多条款联合推理）

等待用户回答。

**Q2（文档结构类型）：**
> 文档主要是什么结构？
> - A. 条款型（法规/标准，有编号条款）
> - B. 步骤型（操作手册、检验规程）
> - C. 表格密集型（大量指标表格）
> - D. 混合型

等待用户回答。

根据两个回答确定**额外重点维度**（在全维度均衡基础上额外关注）：
- 事实查询 + 条款型 → 重点：自包含性、结构完整性（数值与单位完整）
- 流程指导 + 步骤型 → 重点：语义完整性、结构完整性（步骤序列连续）
- 对比分析 + 表格密集型 → 重点：结构完整性（表格行列完整）、主题聚焦性
- 其他组合 → 全维度均衡，无额外侧重

## Phase 3：多维度 Chunk 分析

对所有 chunks 逐一检查以下六个维度。每个维度检查全部 chunks，记录发现的问题。

### 维度 1：自包含性（Self-Containedness）
**定义：** chunk 在逻辑上是否完整——能否独立回答某个具体问题，不依赖文档其他部分的内容（事实、数据、规则）。

**问题信号：**
- 出现"如前所述"、"上述要求"、"见第X条"，且被引用内容不在本 chunk 内
- 结论/规定依赖另一 chunk 中的前提（"因此本产品不适用"但判断依据不在本 chunk）

**严重程度：** 高

### 维度 2：语义完整性（Semantic Completeness）
**定义：** chunk 是否在完整的语义边界处截断，没有切断句子、段落或逻辑单元。

**问题信号：**
- chunk 以未完结的条件句结尾（"如果…"但无"则…"）
- 编号列表只有部分项目（"1. … 2. …"但后续项在其他 chunk）
- 步骤序列中间截断

**严重程度：** 高

### 维度 3：信息密度（Information Density）
**定义：** chunk 中有效信息（事实、规则、数据）与噪音（模板文字、格式残留、页眉页脚）的比值。

**问题信号：**
- chunk 内容几乎全是样板文字（"本章节将介绍……"）
- 仅包含章节标题，无实质内容
- 包含页码、版权声明、目录条目

**低密度参考：** 有效信息占比低于 30% 视为低密度问题。

**严重程度：** 中

### 维度 4：主题聚焦性（Topical Coherence）
**定义：** 一个 chunk 只讨论一个明确的主题，不混杂多个不相关的概念。

**问题信号：**
- 单个 chunk 同时涵盖不同检测类别（如理化指标和微生物指标）
- 将定义条款与限量指标合并在同一 chunk

**严重程度：** 中

### 维度 5：上下文可理解性（Contextual Interpretability）
**定义：** chunk 内的词汇、代词、缩写能否在本 chunk 内完成语言层面的解析，无需依赖外部文档。

**问题信号：**
- 代词所指对象不在本 chunk 内（"该物质"、"上述方法"）
- 使用未定义的缩写（首次出现但无释义）
- 专有名词仅凭本 chunk 无法确定含义

**与维度 1 的区别：** 可理解性问题可通过添加上下文前缀修复，不需重新切分；自包含性问题需调整切分边界或合并 chunk。

**严重程度：** 中

### 维度 6：结构完整性（Structure Integrity）
**定义：** 表格、公式、步骤等结构化内容保持完整，不被截断。

**问题信号：**
- 表格只有数据行，缺少表头（列名/单位）
- 数学公式与其变量定义分散在不同 chunk
- 图注与对应图表编号分离

**严重程度：** 高

## Phase 4：三层输出

完成分析后，按以下格式输出结果。

### 4.1 问题清单

按严重程度分组，每条标注 chunk 标识（优先使用用户指定的标识字段，否则用 `#下标`）、问题维度、具体表现。

```
## 问题清单

### 严重问题（需立即修复）
- Chunk [标识] [维度名称]：[具体表现]

### 中等问题（建议修复）
- Chunk [标识] [维度名称]：[具体表现]

### 轻微问题（可选优化）
- Chunk [标识] [维度名称]：[具体表现]

（无问题时注明"无"）
```

### 4.2 整体质量评估

各维度 1-5 分评分（5 分 = 无问题，1 分 = 普遍存在严重问题），附简要说明。

```
## 整体质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 自包含性 | X/5 | ... |
| 语义完整性 | X/5 | ... |
| 信息密度 | X/5 | ... |
| 主题聚焦性 | X/5 | ... |
| 上下文可理解性 | X/5 | ... |
| 结构完整性 | X/5 | ... |

**总体评分：X.X/5**
**主要瓶颈：[最低分的 1-2 个维度]**
```

### 4.3 改进建议

针对发现的具体问题，给出可操作的切分策略调整建议，按优先级排序。如果用户提供了当前切分策略名称，建议应直接对应该策略的调整方向。

```
## 改进建议

### 最优先（解决严重问题）
1. [建议标题]：[具体操作方法]

### 次优先（解决中等问题）
2. ...

### 可选优化
3. ...
```

## 注意事项

- 不评估 embedding 质量或向量相似度（仅评估文本层面）
- 不自动修复 chunks，只提供评估和建议
- 如果 chunks 数量超过 50 个，优先抽样检查（前 20 个 + 随机抽取 10 个），在输出中注明
````

- [ ] **Step 2：确认 skill 文件包含以下核心内容**

检查 SKILL.md 是否包含：
- [ ] 6 个评估维度，每个维度有定义 + 问题信号 + 严重程度
- [ ] 场景权重矩阵（4 种典型组合 + 兜底规则）
- [ ] 三层输出格式模板（问题清单 / 整体评分表 / 改进建议）
- [ ] 字段路径读取失败时的容错提示逻辑

- [ ] **Step 3：验证文件创建成功**

```bash
ls ~/.claude/skills/chunk-quality-reviewer/
cat ~/.claude/skills/chunk-quality-reviewer/SKILL.md | head -5
```

Expected 输出：
```
SKILL.md
---
name: chunk-quality-reviewer
```

- [ ] **Step 3：提交**

```bash
# skill 文件在 ~/.claude 目录，不在 git repo 中，无需 commit
# 但记录到 memory 中
echo "skill file created at ~/.claude/skills/chunk-quality-reviewer/SKILL.md"
```

---

## Task 2：在真实数据上验证 skill

**Files:**
- 使用现有测试数据：`agent-server/tests/artifacts/parser_workflow_nodes_20260319_110209/08_final_chunks.json`

- [ ] **Step 1：调用 skill 进行验证**

执行以下调用：

```
/chunk-quality-reviewer
文件路径: agent-server/tests/artifacts/parser_workflow_nodes_20260319_110209/08_final_chunks.json
字段路径: node_output.final_chunks[*] 下的 content 和 meta
标识字段: chunk_id
当前切分策略: structured_strategy
```

- [ ] **Step 2：验证 skill 行为是否符合设计**

检查 skill 是否正确执行了以下步骤：
- [ ] 告知读取了多少个 chunks（应为 26 个）
- [ ] 先问 Q1（查询类型），**等待回答后**再问 Q2（不能一次性提两个问题）
- [ ] 根据 Q1+Q2 的回答组合，确定了对应的额外重点维度（场景权重矩阵生效）
- [ ] 对 chunks 进行了六维度分析，各维度有独立的分析结论
- [ ] 输出包含问题清单、整体评分、改进建议三个部分
- [ ] 问题清单中的 chunk 使用了 `chunk_id` 字段作为标识（非数组下标）
- [ ] 改进建议与 `structured_strategy` 策略的特点相关联

- [ ] **Step 3：根据验证结果调整 skill 提示词（如需要）**

如果 skill 行为与设计有偏差，修改 `SKILL.md` 相应部分：
- 如果没有逐一提问而是一次提了两个问题 → 在 Q1 后加强"等待用户回答"的指令
- 如果没有使用 chunk_id 作为标识 → 在参数解析部分加强标识字段的说明
- 如果维度分析过于简略 → 在各维度的"问题信号"部分增加更多示例

- [ ] **Step 4：记录验证结论**

在 spec 文档末尾追加验证记录：
```markdown
## 验证记录

- 日期：2026-03-19
- 测试数据：parser_workflow_nodes_20260319_110209/08_final_chunks.json（26 个 chunks）
- 验证结论：[通过 / 需要调整，说明调整内容]
```

- [ ] **Step 5：commit spec 更新**

```bash
git add agent-server/docs/superpowers/specs/2026-03-19-chunk-quality-reviewer-design.md
git commit -m "docs: add validation record to chunk-quality-reviewer spec"
```
