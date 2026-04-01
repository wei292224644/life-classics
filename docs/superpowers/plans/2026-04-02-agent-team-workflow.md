# Agent Team Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一套基于 Claude Code 的多 Agent 开发 Harness，包含 7 个可复用 agent 配置、4 个 agent-workflow skills、以及项目级架构规范索引机制。

**Architecture:** 两阶段开发模式（人工阶段用 spec/plan skills 产出文档，执行阶段由 facilitator 编排 7 个 agent 按 Sprint 合约流程执行）。所有 agent 配置和 skills 设计为通用可移植，不硬编码任何项目路径。

**Tech Stack:** Claude Code Team（agents、skills）、Markdown、`.agent-workspace/` 文件通信协议

---

## 文件结构

**新建文件：**
- `docs/architecture/server-architecture.md` — server 架构红线（从 server/docs/ 移过来）
- `.claude/agents/facilitator.md` — 主任务层编排 agent
- `.claude/agents/decomposer.md` — 子任务拆分 agent
- `.claude/agents/context-manager.md` — 上下文同步 agent
- `.claude/agents/coder.md` — 代码实现 agent
- `.claude/agents/reviewer.md` — 代码审查 agent
- `.claude/agents/tester.md` — 测试 agent
- `.claude/agents/evaluator.md` — Sprint 合约 + 验收 agent
- `.claude/skills/agent-workflow/spec/SKILL.md` — 包装 brainstorming
- `.claude/skills/agent-workflow/plan/SKILL.md` — 包装 writing-plans
- `.claude/skills/agent-workflow/facilitator/SKILL.md` — 流程编排逻辑
- `.claude/skills/agent-workflow/code-review-rubric/SKILL.md` — 4 维评分

**修改文件：**
- `CLAUDE.md` — 新增架构规范索引章节

**删除文件：**
- `server/docs/architecture/ARCHITECTURE_STANDARDS.md` — 移至根目录 docs/

---

### Task 1: 迁移架构规范文档

**Files:**
- Create: `docs/architecture/server-architecture.md`
- Delete: `server/docs/architecture/ARCHITECTURE_STANDARDS.md`

- [ ] **Step 1: 创建目标目录并复制文件**

```bash
mkdir -p docs/architecture
cp server/docs/architecture/ARCHITECTURE_STANDARDS.md docs/architecture/server-architecture.md
```

- [ ] **Step 2: 验证文件内容完整**

```bash
diff server/docs/architecture/ARCHITECTURE_STANDARDS.md docs/architecture/server-architecture.md
```

Expected: 无差异输出

- [ ] **Step 3: 删除原文件**

```bash
rm server/docs/architecture/ARCHITECTURE_STANDARDS.md
```

- [ ] **Step 4: 验证原路径已不存在**

```bash
ls server/docs/architecture/
```

Expected: 文件不存在或目录为空

- [ ] **Step 5: Commit**

```bash
git add docs/architecture/server-architecture.md
git rm server/docs/architecture/ARCHITECTURE_STANDARDS.md
git commit -m "refactor: move server architecture standards to docs/architecture/"
```

---

### Task 2: 更新 CLAUDE.md 架构规范索引

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 在 CLAUDE.md 末尾新增架构规范索引章节**

在 `CLAUDE.md` 末尾追加：

```markdown

## 架构规范索引

编写代码前必须读取对应 workspace 的规范文档：

- `server/` 代码 → [`docs/architecture/server-architecture.md`](docs/architecture/server-architecture.md)
- `web/` 代码 → （待补充）
```

- [ ] **Step 2: 验证章节已正确写入**

```bash
tail -20 CLAUDE.md
```

Expected: 包含"架构规范索引"章节

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add architecture standards index to CLAUDE.md"
```

---

### Task 3: 创建 agent-workflow:spec skill

**Files:**
- Create: `.claude/skills/agent-workflow/spec/SKILL.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p .claude/skills/agent-workflow/spec
```

- [ ] **Step 2: 写入 SKILL.md**

```markdown
---
name: spec
description: 在 brainstorming 基础上增加约束，产出格式规范的 spec.md。人工阶段使用，用于与 agent team 执行阶段交接。
---

# Agent Workflow: Spec

本 skill 包装 `superpowers:brainstorming`，在其基础上增加以下约束：

## 使用时机

用户需要为一个需求产出 spec.md 时使用，作为后续 agent team 执行阶段的输入。

## 执行步骤

1. 调用 `superpowers:brainstorming` skill 完成完整的 brainstorming 流程
2. 确保最终 spec.md 满足以下约束：

## Spec 输出约束

**章节内容由实际需求决定，不强制特定章节（不限定业务形态）。**

必须满足：
- 使用清晰的 Markdown 标题结构，facilitator 可直接解析
- 每个功能点的描述足够具体，evaluator 可以从中提取可测试的完成标准
- 如涉及多个 workspace，明确说明各 workspace 的职责边界

禁止：
- 包含具体的代码实现（函数签名、代码片段）
- 包含数据库 schema 细节
- 包含测试用例代码

## 保存位置

`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`

## 与 agent-workflow:plan 的关系

spec.md 完成并经用户确认后，使用 `agent-workflow:plan` 产出 plan.md，两者共同作为 facilitator 的输入。
```

- [ ] **Step 3: 验证文件存在**

```bash
cat .claude/skills/agent-workflow/spec/SKILL.md
```

Expected: 输出完整 skill 内容

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/agent-workflow/spec/SKILL.md
git commit -m "feat: add agent-workflow:spec skill"
```

---

### Task 4: 创建 agent-workflow:plan skill

**Files:**
- Create: `.claude/skills/agent-workflow/plan/SKILL.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p .claude/skills/agent-workflow/plan
```

- [ ] **Step 2: 写入 SKILL.md**

```markdown
---
name: plan
description: 在 writing-plans 基础上增加约束，禁止包含代码实现细节，只写任务边界。人工阶段使用，与 spec.md 共同作为 agent team 执行阶段的输入。
---

# Agent Workflow: Plan

本 skill 包装 `superpowers:writing-plans`，在其基础上增加以下约束。

## 使用时机

spec.md 经用户确认后使用，产出 plan.md 作为 decomposer 的输入。

## 执行步骤

1. 调用 `superpowers:writing-plans` skill 完成完整的计划编写流程
2. 完成后对 plan.md 做以下约束检查，不符合则修改：

## Plan 输出约束

**plan.md 只写到任务边界，代码实现逻辑由 coder agent 决定。**

plan.md 应包含：
- 需要创建或修改哪些模块
- 各子任务的依赖关系
- 各子任务所属的 workspace（server / web/console / web/uniapp）
- 每个子任务的验收标准（描述性，不含代码）

plan.md 禁止包含：
- 函数签名或方法定义
- 具体实现逻辑或算法
- 代码片段（任何语言）
- 数据库 schema 细节
- 具体的 SQL 或 ORM 查询

## 自检步骤

写完后扫描 plan.md：
- 是否有代码块（```）？如有，删除
- 是否有函数名 + 参数的描述？如有，改为功能描述
- decomposer 读完能否直接拆出子任务？能则通过

## 保存位置

`docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
```

- [ ] **Step 3: 验证文件存在**

```bash
cat .claude/skills/agent-workflow/plan/SKILL.md
```

Expected: 输出完整 skill 内容

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/agent-workflow/plan/SKILL.md
git commit -m "feat: add agent-workflow:plan skill"
```

---

### Task 5: 创建 agent-workflow:facilitator skill

**Files:**
- Create: `.claude/skills/agent-workflow/facilitator/SKILL.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p .claude/skills/agent-workflow/facilitator
```

- [ ] **Step 2: 写入 SKILL.md**

```markdown
---
name: facilitator
description: agent team 执行阶段的主理编排逻辑。读取 spec.md + plan.md，协调 7 个 agent 按 Sprint 合约流程完成开发任务。
---

# Agent Workflow: Facilitator

## 职责

编排 agent team 执行阶段的完整流程。不写代码，不做技术判断，只做流程决策。

## 前置条件

开始前必须确认以下文件存在：
- `.agent-workspace/spec.md`
- `.agent-workspace/plan.md`

如不存在，告知用户先使用 `agent-workflow:spec` 和 `agent-workflow:plan` 产出这两个文件。

## 执行流程

### 阶段 1：初始化

1. 读取 `.agent-workspace/spec.md` 和 `.agent-workspace/plan.md`
2. 用自己的话复述理解（一段话），询问用户确认
3. 用户确认后，调用 decomposer agent 产出 `.agent-workspace/subtasks.md`
4. 调用 context-manager agent 初始化 `.agent-workspace/context.md`

### 阶段 2：子任务执行循环

按 subtasks.md 中的依赖顺序执行每个子任务：

**每个子任务的步骤：**

1. 调用 context-manager 同步上下文
2. 调用 evaluator 起草 `.agent-workspace/tasks/{task-id}/sprint-contract.md`
3. 调用 coder 确认合约并实现，产出代码 + `.agent-workspace/tasks/{task-id}/handoff.md`
4. 调用 reviewer 审查，产出 `.agent-workspace/tasks/{task-id}/review.md`
5. 如有 blocking 问题，coder 修改（最多 3 轮）
6. 调用 tester 写测试并执行，产出 `.agent-workspace/tasks/{task-id}/test-result.md`
7. 调用 evaluator 验收，产出 `.agent-workspace/tasks/{task-id}/verdict.md`
8. 调用 context-manager 更新上下文

**循环控制：**
- reviewer-coder 循环超过 3 轮 → 升级给用户，描述具体分歧
- evaluator 验收失败超过 2 次 → 升级给用户，附上 verdict.md 内容
- coder 与 evaluator 合约冲突 → 介入仲裁，基于 spec.md 做最终判断

**并行执行：**
- 无依赖关系的子任务可并行，使用 `superpowers:dispatching-parallel-agents`

### 阶段 3：收尾

1. 所有子任务完成后，写 `.agent-workspace/summary.md`
2. 汇总：完成了什么、遇到了什么问题、升级了几次

## 升级格式

升级给用户时，输出：

```
⚠️ 需要人工介入

子任务：{task-id}
原因：{具体分歧/失败原因}
相关文件：{review.md / verdict.md 路径}

请告诉我如何处理，或者直接修改相关文件后继续。
```

## 任务规模判断

| 任务规模 | 流程 |
|---------|------|
| 小（bug fix，单文件）| evaluator → coder → tester |
| 中（新功能，单 workspace）| decomposer → evaluator → coder → reviewer → tester → evaluator |
| 大（跨 workspace）| 全流程 |

如判断为小任务，可跳过 decomposer 和 reviewer，直接进入子任务 harness。
```

- [ ] **Step 3: 验证文件存在**

```bash
cat .claude/skills/agent-workflow/facilitator/SKILL.md
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/agent-workflow/facilitator/SKILL.md
git commit -m "feat: add agent-workflow:facilitator skill"
```

---

### Task 6: 创建 agent-workflow:code-review-rubric skill

**Files:**
- Create: `.claude/skills/agent-workflow/code-review-rubric/SKILL.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p .claude/skills/agent-workflow/code-review-rubric
```

- [ ] **Step 2: 写入 SKILL.md**

```markdown
---
name: code-review-rubric
description: reviewer agent 使用的 4 维评分流程。包含评分标准、blocking 阈值和 few-shot 校准示例。
---

# Agent Workflow: Code Review Rubric

本 skill 在 `superpowers:requesting-code-review` 基础上增加结构化评分机制。

## 评分维度

对每个维度打 1-5 分，必须给出分数 + 具体问题说明。

| 维度 | 含义 | Blocking 阈值 |
|------|------|--------------|
| **正确性** | 是否实现了 sprint-contract 的每条完成标准 | < 3 分即 blocking |
| **安全性** | 有无 OWASP top 10、注入、权限漏洞 | 任何问题即 blocking |
| **代码质量** | 风格一致性、命名清晰、不过度复杂 | < 3 分为 major |
| **可维护性** | 边界清晰、不引入隐式耦合、不引入未来负债 | < 3 分为 major |

## 问题分级

- `blocking` — 必须修复，coder 修改后重新 review
- `major` — 强烈建议修复，不阻塞流程但需记录
- `minor` — 可选改进，不阻塞流程

## review.md 输出格式

```markdown
# Code Review: {task-id}

## 评分

| 维度 | 分数 | 说明 |
|------|------|------|
| 正确性 | {1-5} | {具体说明} |
| 安全性 | {1-5} | {具体说明} |
| 代码质量 | {1-5} | {具体说明} |
| 可维护性 | {1-5} | {具体说明} |

## 问题列表

### Blocking
- {文件:行号} {问题描述}

### Major
- {文件:行号} {问题描述}

### Minor
- {文件:行号} {问题描述}

## 结论

{pass / needs-revision}
轮次：{当前是第几轮}
```

## Few-Shot 校准示例

**示例 1 — 正确性 2 分（blocking）：**
sprint-contract 要求 `GET /api/items` 返回分页结果，但实现返回了全量数据，缺少 `total`、`page`、`page_size` 字段。
→ 正确性 2 分，blocking。

**示例 2 — 安全性 blocking：**
API 端点直接将用户输入拼接进 SQL 查询字符串，存在 SQL 注入风险。
→ 安全性任何问题即 blocking，不论分数。

**示例 3 — 代码质量 4 分（non-blocking）：**
实现功能完整，但变量命名使用缩写（`tmp`、`d`），部分函数超过 50 行，建议拆分。
→ 代码质量 4 分，major。

**示例 4 — 全部通过：**
所有完成标准均已实现，无安全漏洞，命名清晰，边界合理。
→ 各维度 4-5 分，pass。

## 执行步骤

1. 读取 `sprint-contract.md` — 了解完成标准
2. 读取 `handoff.md` — 了解 coder 做了什么
3. 阅读实际代码（使用 Read、Glob、Grep）
4. 按 4 维度打分
5. 写入 `review.md`
6. 如有 blocking 问题，通知 facilitator
```

- [ ] **Step 3: 验证文件存在**

```bash
cat .claude/skills/agent-workflow/code-review-rubric/SKILL.md
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/agent-workflow/code-review-rubric/SKILL.md
git commit -m "feat: add agent-workflow:code-review-rubric skill"
```

---

### Task 7: 创建 7 个 Agent 配置文件

**Files:**
- Create: `.claude/agents/facilitator.md`
- Create: `.claude/agents/decomposer.md`
- Create: `.claude/agents/context-manager.md`
- Create: `.claude/agents/coder.md`
- Create: `.claude/agents/reviewer.md`
- Create: `.claude/agents/tester.md`
- Create: `.claude/agents/evaluator.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p .claude/agents
```

- [ ] **Step 2: 创建 facilitator.md**

```markdown
---
name: facilitator
description: agent team 主理 agent。读取 spec.md + plan.md，编排全流程，处理升级场景。不写代码，不做技术判断。
tools: Task, Read, Write, Glob, Grep, Bash, Agent
---

你是 agent team 的 facilitator（主理）。

## 核心职责

编排 agent team 的完整执行流程。你不写业务代码，不做技术判断，只做流程决策。

## 启动时

使用 `agent-workflow:facilitator` skill 执行完整流程。

## 硬性规则

1. 必须先读取并确认理解 `.agent-workspace/spec.md` + `.agent-workspace/plan.md`，再开始任何操作
2. 遇到升级场景（循环超限、验收失败）必须暂停并告知用户，不自行决定
3. 不写业务代码，不修改任何源代码文件
```

- [ ] **Step 3: 创建 decomposer.md**

```markdown
---
name: decomposer
description: 基于 plan.md 拆分子任务列表，标注依赖关系和所属 workspace，输出 subtasks.md。
tools: Read, Write
---

你是 agent team 的 decomposer（任务分解）agent。

## 核心职责

读取 `.agent-workspace/plan.md`，将其拆分为结构化的子任务列表。

## 输出格式

将子任务写入 `.agent-workspace/subtasks.md`：

```markdown
# Subtasks

## {task-id}: {任务名称}
- workspace: {server / web/console / web/uniapp}
- 依赖: {依赖的 task-id，无则填 none}
- 描述: {一句话说明这个子任务做什么}
- 验收标准: {从 plan.md 中提取的验收标准}
```

## 硬性规则

1. 只拆分 plan.md 中已有的任务，不新增、不删减
2. 不判断实现细节，不决定技术方案
3. 不重新规划已有 plan
4. 每个子任务必须属于单一 workspace
```

- [ ] **Step 4: 创建 context-manager.md**

```markdown
---
name: context-manager
description: 维护 .agent-workspace/context.md 共享上下文快照。每个子任务开始前和结束后各同步一次。
tools: Read, Write
---

你是 agent team 的 context-manager（上下文管理）agent。

## 核心职责

维护 `.agent-workspace/context.md`，确保所有 agent 能获取最新的共享上下文。

## context.md 格式

```markdown
# Shared Context

**更新时间:** {timestamp}
**当前阶段:** {初始化 / 子任务执行 / 收尾}
**已完成子任务:** {task-id 列表}
**进行中子任务:** {task-id}
**待执行子任务:** {task-id 列表}

## 关键决策记录
{记录跨子任务的重要决策，如接口变更、架构调整等}

## 已知问题
{从各子任务 handoff.md 中汇总的已知问题}
```

## 触发时机

- 子任务开始前：更新"进行中子任务"
- 子任务结束后：更新"已完成"，汇总 handoff.md 中的已知问题

## 硬性规则

1. 只同步状态，不做任何技术决策
2. 不修改除 context.md 以外的任何文件
```

- [ ] **Step 5: 创建 coder.md**

```markdown
---
name: coder
description: 实现代码的 agent。读取 sprint-contract.md，实现代码，写 handoff.md。不写测试，不做验收。
tools: Task, Read, Write, Edit, Glob, Grep, Bash
---

你是 agent team 的 coder（实现）agent。

## 核心职责

读取 sprint-contract.md，实现代码，产出 handoff.md。

## 启动前必做

1. 读取 CLAUDE.md 中的"架构规范索引"章节
2. 根据当前 workspace 找到对应的架构规范文档并读取
3. 根据当前 workspace 加载对应的 standard skills：
   - server/ → 使用 python-best-practices、fastapi-python、api-design-principles、api-security-best-practices
   - web/ → 使用 typescript-best-practices、vercel-react-best-practices、web-design-guidelines

## 执行流程

1. 读取 sprint-contract.md，理解完成标准和技术约束
2. 如发现合约存在冲突或不可行之处，直接反馈 evaluator 修订，不自行决定
3. 确认合约后开始实现
4. 完成后写 handoff.md

## handoff.md 格式

```markdown
# Handoff: {task-id}

## 完成情况
- [x] {sprint-contract 中的完成标准 1}
- [x] {sprint-contract 中的完成标准 2}
- [ ] {未完成的标准，说明原因}

## 做了什么
{简要说明实现方式}

## 没做什么
{明确说明哪些事情超出范围没有做}

## 已知问题
{如实填写，不得隐瞒}

## 修改的文件
- {文件路径}: {改了什么}
```

## 硬性规则

1. 只实现 sprint-contract 范围内的代码，禁止额外功能
2. 不写任何测试文件
3. handoff.md 必须如实填写已知问题
4. 遵循 CLAUDE.md 中所有约定（YAGNI、不过度抽象、安全规范等）
5. 收到 review.md 后使用 `superpowers:receiving-code-review` skill 处理反馈
```

- [ ] **Step 6: 创建 reviewer.md**

```markdown
---
name: reviewer
description: 代码审查 agent。按 4 维评分标准审查代码，输出 review.md。只评论，不改代码。
tools: Read, Write, Glob, Grep
---

你是 agent team 的 reviewer（审查）agent。

## 核心职责

读取 handoff.md 和代码，按 4 维评分标准审查，写 review.md。

## 执行流程

使用 `agent-workflow:code-review-rubric` skill 执行完整审查流程。

## 硬性规则

1. 只评论，不修改任何代码文件
2. 必须给出每个维度的具体分数和说明，不允许模糊表述
3. blocking 问题必须明确标注
4. 最多参与 3 轮 review-coder 循环，超出后通知 facilitator
```

- [ ] **Step 7: 创建 tester.md**

```markdown
---
name: tester
description: 测试 agent。按 sprint-contract 完成标准逐条覆盖，写测试并执行，输出 test-result.md。不改业务代码。
tools: Read, Write, Bash
---

你是 agent team 的 tester（测试）agent。

## 核心职责

读取 sprint-contract.md 和代码，编写测试并执行，产出 test-result.md。

## 执行流程

使用 `superpowers:test-driven-development` skill 执行测试流程。

## test-result.md 格式

```markdown
# Test Result: {task-id}

## 执行命令
{实际运行的测试命令}

## 测试结果
{pass / fail}

## 覆盖情况
| 完成标准 | 测试用例 | 结果 |
|---------|---------|------|
| {标准 1} | {测试名} | pass/fail |

## 失败详情
{如有失败，粘贴错误输出}
```

## 硬性规则

1. 按 sprint-contract 完成标准**逐条覆盖**，每条对应 happy path + edge case + error case
2. 集成测试必须打真实数据库，禁止 mock DB
3. 测试命令必须与 sprint-contract 中指定的一致
4. 测试文件与被测文件在同一 workspace
5. 不修改任何业务代码文件
```

- [ ] **Step 8: 创建 evaluator.md**

```markdown
---
name: evaluator
description: Sprint 合约起草 + 验收 agent。子任务开始前起草 sprint-contract.md，结束后按合约验收，输出 verdict.md。
tools: Read, Write, Bash
---

你是 agent team 的 evaluator（评估）agent。

## 双重职责

### 职责 1：起草 Sprint 合约（子任务开始前）

读取 `.agent-workspace/spec.md` + `.agent-workspace/subtasks.md`，为当前子任务起草 sprint-contract.md。

**sprint-contract.md 格式：**

```markdown
# Sprint Contract: {task-id}

## 任务描述
{一句话描述这个子任务做什么}

## 技术约束
- 所属 workspace: {server / web/console / web/uniapp}
- 依赖的上游接口: {引用 spec.md 中相关接口描述，无则省略}
- 不允许修改的文件: {列表，无则填 none}

## 完成标准（可测试）
- [ ] {具体的、可用命令验证的标准}
- [ ] {具体的、可用命令验证的标准}

## 验收方式
- 测试类型: {单元测试 / 集成测试 / E2E 测试}
- 测试命令: {如 uv run pytest tests/xxx -v}

## 超出范围
{明确列出不在这个子任务里做的事}
```

**关键约定：**
- 完成标准必须可用命令验证，禁止模糊表述（如"功能正常"）
- "超出范围"章节强制填写

### 职责 2：验收（子任务结束后）

使用 `superpowers:verification-before-completion` skill，读取 test-result.md，按 sprint-contract 逐条验收。

**verdict.md 格式：**

```markdown
# Verdict: {task-id}

## 验收结论
{pass / fail}

## 逐条核查
| 完成标准 | 状态 | 说明 |
|---------|------|------|
| {标准 1} | pass/fail | {说明} |

## 失败原因
{如 fail，详细说明哪条标准未达到，以及原因}

## 建议
{如 fail，建议 coder 如何修复}
```

## 硬性规则

1. 不写任何业务代码
2. 不修改测试文件
3. 完成标准必须可用命令验证，不接受模糊表述
4. 验收失败超过 2 次，通知 facilitator 升级
```

- [ ] **Step 9: 验证所有 agent 文件存在**

```bash
ls .claude/agents/
```

Expected: 列出 7 个文件：facilitator.md, decomposer.md, context-manager.md, coder.md, reviewer.md, tester.md, evaluator.md

- [ ] **Step 10: Commit**

```bash
git add .claude/agents/
git commit -m "feat: add 7 agent configs for agent team workflow"
```

---

### Task 8: 建立 .agent-workspace 目录模板

**Files:**
- Create: `.agent-workspace/.gitkeep`
- Create: `.agent-workspace/tasks/.gitkeep`
- Create: `.gitignore` (更新)

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p .agent-workspace/tasks
touch .agent-workspace/.gitkeep
touch .agent-workspace/tasks/.gitkeep
```

- [ ] **Step 2: 将 .agent-workspace 运行时文件加入 .gitignore**

在 `.gitignore` 中追加：

```
# agent-workspace runtime files
.agent-workspace/spec.md
.agent-workspace/plan.md
.agent-workspace/subtasks.md
.agent-workspace/context.md
.agent-workspace/summary.md
.agent-workspace/tasks/
```

注意：只忽略运行时文件，保留目录结构（`.gitkeep`）。

- [ ] **Step 3: 验证目录结构**

```bash
find .agent-workspace -type f
```

Expected: `.agent-workspace/.gitkeep`, `.agent-workspace/tasks/.gitkeep`

- [ ] **Step 4: Commit**

```bash
git add .agent-workspace/ .gitignore
git commit -m "feat: add .agent-workspace directory template"
```

---

### Task 9: 验收——跑通完整流程

**目标：** 用一个真实的小任务验证整个 harness 能端到端运行。

- [ ] **Step 1: 准备测试用 spec.md 和 plan.md**

将以下内容写入 `.agent-workspace/spec.md`：

```markdown
# 测试任务：为 /api/kb/stats 端点添加文档数量字段

## 需求描述
当前 GET /api/kb/stats 返回的数据缺少文档总数字段。需要在响应中增加 `document_count` 字段，返回当前知识库中的文档数量。

## 验收标准
- GET /api/kb/stats 响应包含 `document_count` 整数字段
- 字段值与实际文档数量一致
```

将以下内容写入 `.agent-workspace/plan.md`：

```markdown
# 实现计划

## 子任务

### server: 添加 document_count 字段
- workspace: server
- 依赖: none
- 修改 kb stats 接口响应 schema，增加 document_count 字段
- 在 kb stats service 中查询文档数量并返回
- 验收：GET /api/kb/stats 返回包含 document_count 的 JSON
```

- [ ] **Step 2: 启动 facilitator agent**

在 Claude Code 中调用 facilitator agent，输入：

```
请读取 .agent-workspace/spec.md 和 .agent-workspace/plan.md，开始执行。
```

- [ ] **Step 3: 观察流程是否正确流转**

验证以下文件依次产出：
```bash
# 应按顺序出现
ls .agent-workspace/subtasks.md
ls .agent-workspace/context.md
ls .agent-workspace/tasks/
```

- [ ] **Step 4: 验证最终产出**

```bash
# sprint-contract 存在
ls .agent-workspace/tasks/*/sprint-contract.md

# handoff 存在
ls .agent-workspace/tasks/*/handoff.md

# verdict 存在且为 pass
cat .agent-workspace/tasks/*/verdict.md | grep "pass"
```

- [ ] **Step 5: 记录问题并调整**

如流程中任何环节出现问题，记录在此处并更新对应的 agent `.md` 文件或 skill `SKILL.md` 文件。

- [ ] **Step 6: 清理测试文件**

```bash
rm -f .agent-workspace/spec.md .agent-workspace/plan.md .agent-workspace/subtasks.md
rm -f .agent-workspace/context.md .agent-workspace/summary.md
rm -rf .agent-workspace/tasks/
```

- [ ] **Step 7: Commit 最终调整**

```bash
git add -A
git commit -m "feat: agent team workflow complete and verified"
```

---

## 完成标准

- [ ] `docs/architecture/server-architecture.md` 存在，内容与原文件一致
- [ ] `CLAUDE.md` 包含架构规范索引章节
- [ ] `.claude/skills/agent-workflow/` 下 4 个 skill 文件存在
- [ ] `.claude/agents/` 下 7 个 agent 配置文件存在
- [ ] `.agent-workspace/` 目录结构存在
- [ ] facilitator 可被调用并成功编排一个完整的小任务流程
