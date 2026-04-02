# working-harness-team 重构设计文档

## 状态：草稿 v2（参考 Anthropic harness design 文章更新）

---

## 参考来源

**[Harness Design for Long-Running Application Development](https://www.anthropic.com/engineering/harness-design-long-running-apps)**（Prithvi Rajasekaran, Labs team, 2026-03-24）

### 文章关键启示

| 启示 | 对本设计的影响 |
|------|--------------|
| **Context reset via handoff**：handoff 文档是唯一交接载体，不是共享 context 文件 | 删除 `context-manager`，handoff.md 包含所有必要上下文 |
| **Generator 自检后再交**：coder 交 QA 前先过一遍 | coder skill 加"自检"步骤 |
| **Sprint contract 是协商出来的**：Generator 和 Evaluator 来回迭代，不是单方面起草 | evaluator 起草 sprint-contract 后，coder 有机会质疑/协商 |
| **Evaluator 跑应用验证**：不是只读代码，要用 Playwright/API 实际验证 | evaluator 能执行 Bash 命令跑 pytest/curl；handoff 必须提供验证命令 |
| **可剥离的 construct**：小任务不需要严格流程 | 加"简化流程"分支（evaluator 只做 end-pass） |
| **Reviewer = 静态代码质量，Tester = 功能验证**，两者职责不同 | 保留 reviewer 和 tester 两个角色，职责分层 |

### 我们能借鉴什么（不依赖 Opus 4.6）

可以借鉴：handoff 作为唯一交接载体、coder 自检后交、sprint contract 协商流程、evaluator 可执行验证。

不能借鉴：去掉 sprint construct、只做 end-pass evaluator、Generator 自驱完成大任务（依赖模型能力）。

---

## 1. 问题总结

### 1.1 架构层致命缺陷

**`facilitator` 无法创建子 agent。**

Claude Code 的 team 模型中，`Agent tool` 创建出来的 agent 不能调用 `Agent tool`。所以 `facilitator` skill 里所有"调用 coder / reviewer / evaluator / tester"的描述在当前架构下**永远无法执行**。

### 1.2 上下文传递机制设计错误

原设计用 `context.md` 共享黑板，但文章揭示：sub-agent 应该通过 **handoff 文档**获得干净的工作上下文，而不是读共享文件——共享文件会导致"上下文焦虑"（context anxiety），模型在接近上下文上限时会草草收尾。

### 1.3 缺失的 skill

| skill | 现状 |
|-------|------|
| `harness:coder` | 不存在 |
| `harness:reviewer` | 不存在 |
| `harness:evaluator` | 不存在 |
| `harness:decomposer` | 不存在 |
| `harness:context-manager` | 不存在（但 v2 决定删除它） |
| `harness:tester` | 不存在 |
| `harness:review-rubric` | 原 `code-review-rubric`，未改名 |
| `chunk:reviewer` | 原 `chunk-quality-reviewer`，未改名 |

### 1.4 无命名空间隔离

所有 skill 注册到全局，存在命名冲突风险。

---

## 2. 正确的 team 执行模型

### 2.1 角色定义

| 角色 | 职责 | 运行方式 |
|------|------|---------|
| **main session**（用户） | 创建 team、建立 RUN_DIR、预先启动所有 sub-agents、初始 kickoff | 用户在终端执行 |
| **facilitator** | 协调调度——认领任务、发送指令、协调 dispute、处理升级 | 后台 idle，收到消息后启动 |
| **coder** | 读 sprint-contract、实现代码、自检、写 handoff.md（含验证命令） | 后台 idle，收到消息后干活 |
| **reviewer** | 读 handoff + sprint-contract、静态代码质量评分（4 维）、写 review.md | 后台 idle，收到消息后干活 |
| **evaluator** | 起草 sprint-contract（可协商）、verdict 验收（执行验证命令） | 后台 idle，收到消息后干活 |
| **tester** | 读 sprint-contract、逐条执行功能验证、写 test-result.md | 后台 idle，收到消息后干活 |
| **decomposer** | 将 plan.md 拆解为 TaskList | 启动阶段一次性执行，不常驻 |

### 2.2 消息驱动架构

```
main session
    │
    ├── TeamCreate("harness-team")
    ├── TaskCreate × N（设 blockedBy 依赖）
    ├── 创建 RUN_DIR，写 spec.md + plan.md
    │
    ├── Agent(name="facilitator", background=true) ──┐
    ├── Agent(name="coder",      background=true) ──┤  全部预先启动
    ├── Agent(name="reviewer",   background=true) ──┤  idle 等待
    ├── Agent(name="evaluator",  background=true) ──┤
    └── Agent(name="tester",     background=true) ──┘
           │
           └── SendMessage(to="facilitator",
                message="开始执行\nRUN_DIR: ...\nplan: ...")

facilitator（唤醒后）
    │
    ├── 读取 spec.md + plan.md
    ├── 查 TaskList，认领无依赖的 pending 任务
    ├── SendMessage(to="evaluator") → 起草 sprint-contract
    │
    ├── evaluator 起草 → SendMessage(to="coder") → 实现
    ├── coder 自检 → 写 handoff.md（含验证命令）
    ├── SendMessage(to="reviewer") → 静态评分
    ├── reviewer 通过 → SendMessage(to="tester") → 功能验证
    ├── tester 完成 → SendMessage(to="evaluator") → verdict
    │
    └── 循环直到所有任务完成或升级
```

**核心约束**：sub-agents 全部由 **main session 预先创建并置于 background idle 状态**，facilitator 只能通过 `SendMessage` 唤醒它们，不能创建它们。

### 2.3 上下文传递机制（v2：基于 handoff）

**handoff.md 是唯一交接载体，不靠共享 context 文件。**

```
SendMessage 只传路径，不塞内容：

Task: {task-id}
RUN_DIR: {RUN_DIR}
sprint-contract: {RUN_DIR}/tasks/{task-id}/sprint-contract.md
handoff: {RUN_DIR}/tasks/{task-id}/handoff.md
review: {RUN_DIR}/tasks/{task-id}/review.md
test-result: {RUN_DIR}/tasks/{task-id}/test-result.md
verdict: {RUN_DIR}/tasks/{task-id}/verdict.md
```

sub-agent 收到消息后自行读取对应文件。**不需要读 context.md**，handoff 文档已经包含所有必要信息。

### 2.4 Sprint Contract 协商流程

```
1. evaluator 读 spec + plan，起草 sprint-contract.md
2. facilitator 把 sprint-contract 发给 coder
3. coder 如有异议，写 contract-dispute.md
4. facilitator 仲裁：
   - 接受 coder 的异议 → 更新 sprint-contract
   - 拒绝 → coder 必须执行
5. 双方对齐后，coder 开始实现
```

### 2.5 Evaluator 必须执行验证

**验证不是读代码，是跑命令。** evaluator/tester 收到 handoff 后，必须用 handoff 里提供的验证命令实际执行验证。

验证手段：

| 验证类型 | 命令 |
|---------|------|
| pytest 测试 | `uv run pytest tests/... -v` |
| API endpoint | `curl -X GET "http://localhost:9999/api/..."` |
| 数据库写入 | `psql` 或 API 读回验证 |
| 解析/计算逻辑 | `uv run python -c "..."` |

**如果验证命令不可行**（如需要服务启动），evaluator 应在 sprint-contract 协商阶段明确告知，改为替代验证方案或升级。

---

## 3. 命名空间与目录结构

### 3.1 Skill 命名

| 新名称 | 原名称 | 说明 |
|--------|--------|------|
| `harness:facilitator` | `working-harness-team:facilitator` | 重命名 + 重写调度逻辑 |
| `harness:spec` | `working-harness-team:spec` | 重命名 |
| `harness:plan` | `working-harness-team:plan` | 重命名 |
| `harness:decomposer` | （不存在） | **新建** |
| `harness:coder` | （不存在） | **新建** |
| `harness:reviewer` | （不存在） | **新建** |
| `harness:review-rubric` | `working-harness-team:code-review-rubric` | 重命名 |
| `harness:evaluator` | （不存在） | **新建** |
| `harness:tester` | （不存在） | **新建** |
| `chunk:reviewer` | `chunk-quality-reviewer` | 重命名（加前缀） |

**v2 删除**：`harness:context-manager`（handoff 替代，不需要共享 context 文件）。

### 3.2 目录结构

```
.claude/skills/
├── chunk/
│   └── reviewer/
│       └── SKILL.md            ← 重命名
└── harness/
    ├── facilitator/
    │   └── SKILL.md            ← 重写调度逻辑
    ├── spec/
    │   └── SKILL.md            ← 重命名
    ├── plan/
    │   └── SKILL.md            ← 重命名
    ├── decomposer/
    │   └── SKILL.md            ← 新建
    ├── coder/
    │   └── SKILL.md            ← 新建
    ├── reviewer/
    │   └── SKILL.md            ← 新建
    ├── review-rubric/
    │   └── SKILL.md            ← 改名
    ├── evaluator/
    │   └── SKILL.md            ← 新建
    └── tester/
        └── SKILL.md            ← 新建
```

---

## 4. 各 Skill 详细设计

### 4.1 `harness:facilitator`

#### frontmatter

```yaml
---
name: facilitator
description: agent team 执行阶段的主理编排逻辑。读取 spec + plan，协调 sub-agents 按 Sprint 合约流程完成开发任务。
user-invocable: false
argument-hint: "<RUN_DIR>"
---
```

#### 章节结构

```
## 角色定位
协调者，不写代码。只管流程：谁在什么时间做什么，遇到阻塞时升级。

## 前置条件检查清单
在 facilitator 被调用前，main session 必须完成：
- [ ] team 已创建（TeamCreate）
- [ ] 所有 sub-agents（coder/reviewer/evaluator/tester）已在 team 中且 background=true
- [ ] RUN_DIR 已建立，spec.md 和 plan.md 已写入
- [ ] TaskList 中所有任务已创建，blockedBy 依赖已设置

## 子任务循环

对于每个子任务（按 blockedBy 依赖顺序）：

1. 查 TaskList，TaskUpdate 认领第一个无依赖的 pending 任务
2. SendMessage(to="evaluator", message="起草 sprint-contract\nTaskID: ...\nRUN_DIR: ...\nspec: ...\nplan: ...")
3. **evaluator 起草 sprint-contract 完成后**：
   - 检查 contract-dispute.md（coder 如有异议会写）
   - 存在 dispute → 仲裁（接受或拒绝）→ 更新 sprint-contract → 通知 coder
4. SendMessage(to="coder", message="实现 Task ...\nRUN_DIR: ...\nsprint-contract: ...\n验收命令见 sprint-contract.md")
5. **coder 完成后**（handoff.md 已写入）：
   - 小任务（无 reviewer）：SendMessage(to="tester") → 功能验证
   - 中/大任务：SendMessage(to="reviewer") → 静态评分
6. **reviewer 完成后**：
   - `needs-revision` → SendMessage(to="coder") 重做（传新版本号）
   - `pass` / `pass-with-notes` → SendMessage(to="tester") → 功能验证
7. **tester 完成后**：SendMessage(to="evaluator") → verdict
8. **verdict = fail** → coder 修复，最多 2 次；超过升级
9. **review_rounds > 3** → 升级
10. 所有子任务完成 → 收尾 → summary.md → 结束

## 简化流程分支
小任务（bug fix，单文件）可跳过 reviewer，直接：
evaluator → coder → tester → evaluator verdict

## 任务认领规则
每次 start 新子任务前，查 TaskList：
- 选 `status=pending` 且 `blockedBy` 均为空的最小 ID 任务
- TaskUpdate(status=in_progress, owner=facilitator)
- 如果所有 pending 任务都有未完成的 blockedBy，等待

## SendMessage 格式规范
每次发给 sub-agent 的消息必须包含：
- Task ID
- RUN_DIR
- 指向对应 .md 文件的路径（sprint-contract / handoff / review 等）

## 升级模板
（Markdown 格式，含背景 + 待确认清单）
```

### 4.2 `harness:coder`

#### frontmatter

```yaml
---
name: coder
description: 接收 facilitator 的 Task 指令，读 sprint-contract 实现代码，自检后写 handoff.md（含验证命令）。
user-invocable: false
argument-hint: "<TaskID> <RUN_DIR>"
---
```

#### 章节结构

```
## 唤醒触发
收到 facilitator 的 SendMessage 后开始执行。

## 执行步骤
1. 读取 sprint-contract.md，逐条理解验收标准
2. 实现代码（Read / Grep / Edit / Write / Bash）
3. **自检**：对照 sprint-contract 每一条，检查是否满足
   - 如有不确定的条目，在 handoff.md 里注明
4. 写 handoff.md（见格式）
5. SendMessage(to="facilitator", message="Task {ID} 完成，handoff.md 已写入\n版本：{handoff_version}")

## handoff.md 格式
```markdown
# Handoff: Task {ID}

## 实现摘要
{简要说明做了什么}

## 文件变更
- 新建：...
- 修改：...
- 删除：...

## 关键决策
{为什么这样实现}

## 已知问题
{如果有，标注"需确认"或"已知限制"}

## sprint-contract 核对（自检结果）
- [x] 标准1：{自检说明}
- [?] 标准2：{不确定，需 reviewer 确认}

## 验证方式（evaluator/tester 使用的命令）
- pytest: `uv run pytest tests/.../test_xxx.py -v`
- API: `curl -X GET "http://localhost:9999/api/..."`
- 或其他：{手动验证步骤}
```
```

### 4.3 `harness:reviewer`

#### frontmatter

```yaml
---
name: reviewer
description: 接收 facilitator 的 review 指令，读 handoff + sprint-contract，按 4 维评分输出 review.md。
user-invocable: false
argument-hint: "<TaskID> <RUN_DIR> <handoff_version>"
---
```

#### 章节结构

```
## 唤醒触发
收到 facilitator 的 SendMessage 后开始执行。

## 执行步骤
1. 读取 sprint-contract.md（验收标准）
2. 读取 handoff.md（实现摘要 + 文件变更）
3. 阅读实际代码（Read / Grep）
4. 按 4 维评分（调用 harness:review-rubric）
5. 写 review.md（格式见 rubric）
6. SendMessage(to="facilitator", message="review 完成\n结论: {pass/needs-revision/pass-with-notes}\n轮次: {N}")

## review.md 格式（调用 review-rubric 定义的格式）
```

### 4.4 `harness:review-rubric`

**原 `working-harness-team:code-review-rubric`，重命名迁移。**

内容基本不变，frontmatter 的 name 改为 `harness:review-rubric`。

### 4.5 `harness:evaluator`

#### frontmatter

```yaml
---
name: evaluator
description: 起草 sprint-contract（可与 coder 协商），执行 verdict 验收（跑验证命令）。
user-invocable: false
argument-hint: "<TaskID> <RUN_DIR>"
---
```

#### 章节结构

```
## 两个阶段

### 阶段 1：起草 sprint-contract

1. 读 spec.md + plan.md
2. 从 plan.md 中提取该子任务的验收标准，转化为可测试条款
3. 每条标准必须包含**验证命令**（或说明验证方式）
4. 写 {RUN_DIR}/tasks/{task-id}/sprint-contract.md
5. SendMessage(to="facilitator", message="sprint-contract 起草完成")

**sprint-contract 格式**：
```markdown
# Sprint Contract: Task {ID}

## 验收标准

| # | 标准描述 | 验证方式 | 命令 |
|---|---------|---------|------|
| 1 | API 返回分页数据 | curl | `curl ...` |
| 2 | pytest 全部通过 | pytest | `uv run pytest ...` |

## 注意事项
{如有需要注意的边界条件}
```
```

### 阶段 2：验收 verdict

1. 读取 sprint-contract.md
2. 读取 test-result.md（tester 的功能验证结果）
3. **evaluator 必须执行验证命令**（不只是读文件）：
   - 逐条执行 sprint-contract 里的验证命令
   - 记录每条的执行结果
4. 对照 sprint-contract，输出 verdict
5. 写 {RUN_DIR}/tasks/{task-id}/verdict.md
6. SendMessage(to="facilitator", message="verdict: {pass/fail}")

**verdict.md 格式**：
```markdown
# Verdict: Task {ID}

## 验收结果

| # | 标准 | 验证命令 | 执行结果 | verdict |
|---|------|---------|---------|---------|
| 1 | ... | curl ... | 返回 200 | PASS |
| 2 | ... | pytest ... | 3 failed | FAIL |

## 结论
{pass / fail}

## 失败原因（如果 fail）
{哪一条没过，为什么}
```

### Sprint Contract Dispute（协商流程）

如果 coder 在实现过程中发现某条标准无法实现：

1. coder 写 {RUN_DIR}/tasks/{task-id}/contract-dispute.md，说明哪条标准有问题及原因
2. SendMessage(to="facilitator")
3. facilitator 读 dispute，仲裁：
   - **接受**：更新 sprint-contract，通知 coder 和 evaluator
   - **拒绝**：通知 coder 必须执行，coder 继续
4. 协商完成后，coder 继续实现
```

### 4.6 `harness:tester`

#### frontmatter

```yaml
---
name: tester
description: 接收 facilitator 的测试指令，读 sprint-contract，逐条执行功能验证，写 test-result.md。
user-invocable: false
argument-hint: "<TaskID> <RUN_DIR>"
---
```

#### 章节结构

```
## 唤醒触发
收到 facilitator 的 SendMessage 后开始执行。

## 执行步骤
1. 读取 sprint-contract.md（验证标准 + 命令）
2. **执行** sprint-contract 中的每条验证命令（evaluator 跑命令，tester 记录结果）
   - pytest → 跑测试
   - curl → 调 API
   - 其他 → 执行对应命令
3. 记录每条的执行结果（stdout/stderr/exit code）
4. 写 test-result.md
5. SendMessage(to="facilitator", message="test 完成")

## test-result.md 格式
```markdown
# Test Result: Task {ID}

## 执行记录

| # | 验证命令 | 执行结果 | 说明 |
|---|---------|---------|------|
| 1 | `uv run pytest ...` | exit 0，3 passed | 通过 |
| 2 | `curl ...` | HTTP 200，body: {...} | 通过 |
| 3 | `curl ...` | HTTP 500 | 失败 |

## 问题列表（如有）
{描述失败项}

## 结论
{pass（全部通过）/ fail（有失败）}
```

**注意**：tester 不写测试代码，只执行已有的验证命令并记录结果。测试代码由 coder 在实现时写入。
```

### 4.7 `harness:decomposer`

#### frontmatter

```yaml
---
name: decomposer
description: 将 plan.md 拆解为 TaskList 任务项，设好 blockedBy 依赖。
user-invocable: false
argument-hint: "<RUN_DIR>"
---
```

#### 章节结构

```
## 职责
plan.md 经用户确认后使用，产出 subtasks.md，main session 据此创建 TaskList。

## 执行步骤
1. 读取 plan.md
2. 遍历 plan 中的子任务
3. 对每个子任务，TaskCreate（description 含验收标准概要）
4. 有依赖的子任务，TaskUpdate(addBlockedBy=[...])
5. 写 {RUN_DIR}/subtasks.md（供人确认）
6. SendMessage(to="facilitator", message="decompose 完成，N 个任务已创建")
```

---

## 5. main session 的启动流程（用户操作手册）

```
1. TeamCreate("harness-team", description="...", agent_type="facilitator")

2. 预创建所有 sub-agents（同一 message 内并行，background=true）：
   Agent(name="facilitator", team_name="harness-team", subagent_type="general-purpose", run_in_background=true)
   Agent(name="coder",      team_name="harness-team", subagent_type="general-purpose", run_in_background=true)
   Agent(name="reviewer",   team_name="harness-team", subagent_type="general-purpose", run_in_background=true)
   Agent(name="evaluator",  team_name="harness-team", subagent_type="general-purpose", run_in_background=true)
   Agent(name="tester",     team_name="harness-team", subagent_type="general-purpose", run_in_background=true)

3. 创建 RUN_DIR：
   mkdir -p .agent-workspace/runs/YYYY-MM-DD-<topic>
   写入 spec.md 和 plan.md

4. TaskCreate × N（设 blockedBy）

5. 发送 kickoff 给 facilitator：
   SendMessage(to="facilitator", message="开始执行\nRUN_DIR: .agent-workspace/runs/YYYY-MM-DD-<topic>")
```

---

## 6. 迁移计划

### Phase 1：建立目录结构 + 迁移
- `mkdir -p harness/{facilitator,spec,plan,decomposer,coder,reviewer,review-rubric,evaluator,tester}`
- `mkdir -p chunk/reviewer`
- 逐一写入所有 SKILL.md

### Phase 2：删除旧目录
- `rm -rf .claude/skills/working-harness-team/`
- `rm -f .claude/skills/chunk-quality-reviewer/SKILL.md`
- 确认无残留引用

### Phase 3：验证
- `/harness:spec` 可正常调用
- `/harness:facilitator` skill 内容正确加载
- 启动流程实测

---

## 7. 待确认问题

1. **worktree 隔离**：harness team 在哪个 worktree/分支上工作？main session 启动 team 前是否需要先 EnterWorktree？
2. **main session 的 kickoff 消息格式**：如何让 facilitator 正确解析 RUN_DIR 和 task 列表？
3. **小任务的简化流程**：如何判断"小/中/大"从而决定是否跳过 reviewer？
4. **handoff 版本管理**：coder 重做时，handoff 版本号如何命名（如 `handoff-v2.md`）？
