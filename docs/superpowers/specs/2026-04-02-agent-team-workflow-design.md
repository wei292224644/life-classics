# Agent Team 开发流程设计

**日期：** 2026-04-02  
**状态：** 已确认  
**参考：** [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)

---

## 背景与目标

当前 LLM 辅助开发存在以下痛点：

- 代码质量不稳定，风格不一致
- 流程失控，LLM 一次性生成大量代码难以追踪
- 测试缺失或测试无法真正验证正确性
- 职责不清，同一 LLM 既写代码又 review 自己
- 代码方向偏离意图，缺乏架构约束
- 任务拆分粒度不一致
- Agent 之间信息丢失

**目标：** 构建一套基于 Claude Code Team 的多 Agent 开发 Harness，通过角色分离、Sprint 合约机制、文件/消息混合通信，规范 LLM 开发流程，提升代码质量和可追溯性。

---

## 核心设计原则

1. **生成与评估永远分离** — 自我评估有盲区，evaluator 必须独立于 coder
2. **Sprint 合约先行** — 每个子任务开始前定义可测试的完成标准
3. **文件跨层，消息同层** — 关键交接通过文件持久化，同层 agent 直接对话
4. **边界即约束** — 每个 agent 有严格工具权限，越界视为 harness 设计问题
5. **随模型能力演进** — harness 复杂度应动态调整，不是一成不变的

---

## 整体架构

### 三个层级

| 层级 | 角色 | 边界 |
|------|------|------|
| 主任务层 | facilitator | 全局协调，不写代码，不做技术判断 |
| 规划层 | architect、decomposer | 只产出文档，不触碰代码 |
| 子任务层 | coder、reviewer、tester、evaluator | 独立运行，通过文件跨层交接 |
| 贯穿层 | context-manager | 维护共享上下文，不做决策 |

### 主流程

```
用户需求
    ↓
facilitator（最外层 Harness）
    ├── 调用 architect → spec.md + api-contract.md
    ├── 调用 decomposer → subtasks.md
    │
    └── 按依赖顺序执行每个子任务：
          ┌─────────────────────────────────────┐
          │           子任务 Harness             │
          │                                     │
          │  context-manager 同步上下文          │
          │  evaluator → sprint-contract.md     │
          │  coder 确认合约 → 实现 → handoff.md  │
          │  reviewer → review.md（最多 3 轮）   │
          │  tester → test-result.md            │
          │  evaluator → verdict.md             │
          │    ├── pass → 子任务完成             │
          │    └── fail（最多 2 次）→ 升级用户   │
          └─────────────────────────────────────┘
    ↓
facilitator 汇总 → summary.md
```

### 任务粒度

- **主任务**：对应一个完整需求（可跨多个 workspace），作为追踪容器
- **子任务**：对应单个 workspace 的实现单元，是 8 角色流程的最小执行单位
- **依赖关系**：如 server 子任务完成（API contract 确认）后，web 子任务才可并行开始

---

## Agent 角色定义

### facilitator（主任务层）

- **职责：** 编排全流程，判断跳过哪些角色，处理升级场景
- **工具权限：** All（但不写业务代码）
- **边界：** 不写代码，不做技术判断，只做流程决策
- **升级条件：** reviewer-coder 循环超过 3 轮；evaluator 验收失败超过 2 次

### architect（规划层）

- **职责：** 将用户需求扩展为功能规范和接口契约
- **输出：** `spec.md`、`api-contract.md`
- **工具权限：** Read、Glob、Grep、Write
- **边界：** 只产出文档，禁止写业务代码
- **可跳过：** 小任务（bug fix）可由 facilitator 判断跳过

### decomposer（规划层）

- **职责：** 将 spec 拆分为子任务列表，标注依赖关系和所属 workspace
- **输出：** `subtasks.md`
- **工具权限：** Read、Write
- **边界：** 只拆任务，不判断实现细节

### evaluator（子任务层）

- **职责 1（开始前）：** 读 spec → 起草 `sprint-contract.md`
- **职责 2（结束后）：** 读 `test-result.md` → 按合约验收，输出 `verdict.md`
- **工具权限：** Read、Write、Bash（只读测试结果）
- **边界：** 不写业务代码，不修改测试
- **核心原则：** 谁验收谁定标准，完成标准必须可用命令验证

### coder（子任务层）

- **职责：** 读 `sprint-contract.md` → 实现代码 → 写 `handoff.md`
- **输出：** 代码实现 + `handoff.md`（做了什么、未做什么、已知问题）
- **工具权限：** All
- **边界：** 不写测试，不做验收判断
- **合约冲突：** 发现合约不可行时，直接反馈 evaluator 修订，不自行决定

### reviewer（子任务层）

- **职责：** 读 `handoff.md` + 代码 → 写 `review.md`
- **输出：** 问题列表（按严重程度分级：blocking / major / minor）
- **工具权限：** Read、Glob、Grep、Write
- **边界：** 只评论，不改代码
- **复用：** `superpowers:requesting-code-review` skill

### tester（子任务层）

- **职责：** 读 `sprint-contract.md` + 代码 → 写测试 + 执行 → 写 `test-result.md`
- **工具权限：** Read、Write、Bash
- **边界：** 只写测试，不改业务代码
- **复用：** `superpowers:test-driven-development` skill

### context-manager（贯穿层）

- **职责：** 维护 `context.md` 共享上下文快照
- **触发时机：** 每个子任务开始前、结束后各一次
- **工具权限：** Read、Write、Memory
- **边界：** 只同步状态，不做任何决策

---

## 通信协议

### 原则

- **同层 agent 之间：** 直接对话（SendMessage），更自然流畅
- **跨层交接：** 文件持久化（`.agent-workspace/`），保证可追溯

### 文件结构

```
.agent-workspace/
├── spec.md                    # architect 写，所有人只读
├── api-contract.md            # architect 写，所有人只读
├── subtasks.md                # decomposer 写
├── context.md                 # context-manager 维护
├── summary.md                 # facilitator 写（完成后）
│
└── tasks/
    └── {task-id}/
        ├── sprint-contract.md  # evaluator 写（开始前）
        ├── handoff.md          # coder 写（可追加）
        ├── review.md           # reviewer 写（可追加）
        ├── test-result.md      # tester 写
        └── verdict.md          # evaluator 写（验收结论）
```

### 文件所有权

| 文件 | 写入者 | 读取者 | 可追加 |
|------|--------|--------|--------|
| `spec.md` | architect | 所有 agent | 否 |
| `api-contract.md` | architect | 所有 agent | 否 |
| `subtasks.md` | decomposer | facilitator | 否 |
| `context.md` | context-manager | 所有 agent | 是 |
| `sprint-contract.md` | evaluator | coder、tester | 否 |
| `handoff.md` | coder | reviewer、tester | 是（每轮追加）|
| `review.md` | reviewer | coder | 是（每轮追加）|
| `test-result.md` | tester | evaluator | 否 |
| `verdict.md` | evaluator | facilitator | 否 |

---

## Sprint 合约格式

```markdown
# Sprint Contract: {task-id}

## 任务描述
{一句话描述这个子任务做什么}

## 技术约束
- 所属 workspace: {server / web/console / web/uniapp}
- 依赖的 API contract: {引用 api-contract.md 相关部分}
- 不允许修改的文件: {列表}

## 完成标准（可测试）
- [ ] {具体的、可用命令验证的标准，如：GET /api/xxx 返回 200}
- [ ] {具体的、可用命令验证的标准}
- [ ] ...

## 验收方式
- 测试类型: 单元测试 / 集成测试 / E2E 测试
- 测试命令: {如 uv run pytest tests/xxx -v}

## 超出范围
{明确列出不在这个子任务里做的事，防止 coder 过度实现}
```

**关键约定：**
- 完成标准必须可用命令验证，禁止模糊表述（如"功能正常"）
- "超出范围"章节强制填写
- coder 在开始实现前必须确认合约，发现冲突直接反馈 evaluator

---

## 循环控制与升级机制

| 场景 | 最大次数 | 超出后 |
|------|---------|--------|
| reviewer → coder 修改循环 | 3 轮 | facilitator 升级给用户 |
| evaluator 验收失败 | 2 次 | facilitator 升级给用户 |
| coder 与 evaluator 合约冲突 | 1 次协商 | facilitator 介入仲裁 |

---

## 复用已有 Skills

| 已有 Skill | 映射角色 |
|-----------|---------|
| `superpowers:brainstorming` | architect |
| `superpowers:writing-plans` | decomposer |
| `superpowers:test-driven-development` | tester |
| `superpowers:requesting-code-review` | reviewer |
| `superpowers:verification-before-completion` | evaluator（验收） |
| `superpowers:using-git-worktrees` | 子任务隔离 |
| `superpowers:dispatching-parallel-agents` | facilitator（并行子任务）|

**新建 Skill（仅 1 个）：** `agent-workflow:facilitator` — 主理流程编排逻辑

---

## Agent 配置文件结构

```
.claude/
└── agents/
    ├── facilitator.md
    ├── architect.md
    ├── decomposer.md
    ├── context-manager.md
    ├── coder.md
    ├── reviewer.md
    ├── tester.md
    └── evaluator.md
```

每个 `.md` 文件定义该 agent 的 system prompt、工具权限、行为规范。

---

## Harness 演进策略

### 阶段一：启动版（当前）

所有 8 个 agent 全部启用，积累数据，观察哪些角色产生真实价值。

### 阶段二：精简版（3 个月后评估）

观察以下信号：
- reviewer 的意见 90% 被接受 → reviewer 可合并进 coder 自检
- decomposer 拆分结果 facilitator 每次都要修改 → 合并进 facilitator
- context-manager 同步内容很少被用 → 简化或移除

### 阶段三：按规模选流程

| 任务规模 | 流程 |
|---------|------|
| 小（bug fix）| facilitator → coder → tester |
| 中（新接口）| facilitator → architect → coder → reviewer → tester → evaluator |
| 大（跨 workspace）| 全流程 |

### 核心原则

> 每个 harness 组件都编码了一个关于模型不能做什么的假设，这些假设值得持续压力测试。

- 每个 agent 的存在必须有可量化的理由
- 模型升级后，重新评估哪些 agent 可以退休
- 宁可删除冗余 agent，不要为了"完整"保留无用组件

---

## 实现路径

1. 定义 8 个 agent 的 `.claude/agents/*.md` 配置文件
2. 新建 `agent-workflow:facilitator` skill
3. 建立 `.agent-workspace/` 目录结构模板
4. 用一个真实子任务跑通完整流程（验证阶段）
5. 根据运行结果调整 agent prompt 和 harness 结构
