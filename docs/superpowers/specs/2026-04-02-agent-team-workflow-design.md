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

## 两阶段开发模式

整个开发流程分为**人工阶段**和**执行阶段**，agent team 只负责执行阶段。

```
人工阶段（现有 superpowers 流程，保持不变）
  用户 + superpowers:brainstorming  → spec.md（功能规范 + API contract）
  用户 + superpowers:writing-plans  → plan.md（实现计划）
        ↓ 用户确认 spec + plan
执行阶段（agent team 接管）
  facilitator 读 spec.md + plan.md → 开始执行
```

**为什么这样分：**
- spec 质量决定执行质量，人机协作产出的 spec 远优于 agent 自己推断的
- brainstorming/writing-plans 是交互式的，不适合在 agent 内部循环调用
- agent team 专注于"执行正确"，人工阶段专注于"方向正确"

**因此 architect 角色不再需要**，spec 和 plan 由人工阶段产出。

---

## 核心设计原则

1. **生成与评估永远分离** — 自我评估有盲区，evaluator 必须独立于 coder
2. **Sprint 合约先行** — 每个子任务开始前定义可测试的完成标准
3. **文件跨层，消息同层** — 关键交接通过文件持久化，同层 agent 直接对话
4. **边界即约束** — 每个 agent 有严格工具权限，越界视为 harness 设计问题
5. **随模型能力演进** — harness 复杂度应动态调整，不是一成不变的

---

## 整体架构

### 层级结构（7 个 Agent）

| 层级 | 角色 | 边界 |
|------|------|------|
| 主任务层 | facilitator | 全局协调，不写代码，不做技术判断 |
| 规划层 | decomposer | 基于 plan.md 拆子任务，不从零规划 |
| 子任务层 | coder、reviewer、tester、evaluator | 独立运行，通过文件跨层交接 |
| 贯穿层 | context-manager | 维护共享上下文，不做决策 |

### 主流程

```
用户提供 spec.md + plan.md
    ↓
facilitator（最外层 Harness）
    ├── 读取并确认理解 spec.md + plan.md
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

- **职责：** 读取 spec.md + plan.md，确认理解后编排全流程，处理升级场景
- **工具权限：** All（但不写业务代码）
- **边界：** 不写代码，不做技术判断，只做流程决策
- **升级条件：** reviewer-coder 循环超过 3 轮；evaluator 验收失败超过 2 次
- **入口约定：** 必须先读取并确认 spec.md + plan.md，再调用 decomposer

### decomposer（规划层）

- **职责：** 基于 plan.md 拆分子任务列表，标注依赖关系和所属 workspace
- **输出：** `subtasks.md`
- **工具权限：** Read、Write
- **边界：** 只拆任务，不判断实现细节，不重新规划已有 plan

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
- **规范来源：** System prompt（约束性规则）+ 引用 CLAUDE.md

**Coder 硬性规则（写入 system prompt）：**
1. 只实现 sprint-contract 范围内的代码，禁止额外功能
2. 不写测试文件
3. handoff.md 必须如实填写已知问题，不得隐瞒
4. 遵循 CLAUDE.md 中所有约定（YAGNI、不过度抽象、安全规范等）

### reviewer（子任务层）

- **职责：** 读 `handoff.md` + 代码 → 按 4 维评分 → 写 `review.md`
- **输出：** 各维度分数 + 问题列表（按 blocking / major / minor 分级）
- **工具权限：** Read、Glob、Grep、Write
- **边界：** 只评论，不改代码
- **Skill：** `agent-workflow:code-review-rubric`（新建）+ `superpowers:requesting-code-review`（基础）

**4 维评分标准（写入 `agent-workflow:code-review-rubric` skill）：**

| 维度 | 含义 | Blocking 阈值 |
|------|------|--------------|
| **正确性** | 是否实现了 sprint-contract 的每条完成标准 | < 3 分即 blocking |
| **安全性** | 有无 OWASP top 10、注入、权限漏洞 | 任何问题即 blocking |
| **代码质量** | 风格一致性、命名清晰、不过度复杂 | < 3 分为 major |
| **可维护性** | 边界清晰、不引入隐式耦合、不引入未来负债 | < 3 分为 major |

评分 1-5 分，每个维度必须给出分数 + 具体问题说明。Skill 中包含 few-shot 示例用于校准判断标准。

### tester（子任务层）

- **职责：** 读 `sprint-contract.md` + 代码 → 写测试 + 执行 → 写 `test-result.md`
- **工具权限：** Read、Write、Bash
- **边界：** 只写测试，不改业务代码
- **Skill：** `superpowers:test-driven-development`（复用，无需新建）

**Tester 硬性规则（写入 system prompt）：**
1. 按 sprint-contract 完成标准**逐条覆盖**，每条对应 happy path + edge case + error case
2. 集成测试必须打真实数据库，禁止 mock DB
3. 测试命令必须与 sprint-contract 中指定的一致
4. 测试文件与被测文件在同一 workspace

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

## Skills 分配

### 人工阶段（执行阶段前，保持现有流程）

| Skill | 用途 |
|-------|------|
| `superpowers:brainstorming` | 产出 spec.md + api-contract.md |
| `superpowers:writing-plans` | 产出 plan.md |

### 执行阶段（agent team）

**复用已有 Skill：**

| Skill | 映射角色 |
|-------|---------|
| `superpowers:test-driven-development` | tester |
| `superpowers:requesting-code-review` | reviewer（基础） |
| `superpowers:verification-before-completion` | evaluator（验收） |
| `superpowers:using-git-worktrees` | 子任务隔离 |
| `superpowers:dispatching-parallel-agents` | facilitator（并行子任务）|

**新建 Skill（共 2 个）：**

| Skill | 用于 | 说明 |
|-------|------|------|
| `agent-workflow:facilitator` | facilitator | 主理流程编排逻辑 |
| `agent-workflow:code-review-rubric` | reviewer | 4 维打分流程 + few-shot 校准示例 |

---

## 配置文件结构

```
.claude/
├── agents/                      # 各 agent 的 system prompt
│   ├── facilitator.md
│   ├── architect.md
│   ├── decomposer.md
│   ├── context-manager.md
│   ├── coder.md
│   ├── reviewer.md
│   ├── tester.md
│   └── evaluator.md
└── standards/                   # 技术规范文档，agent 按需引用
    ├── python.md                # server/ 规范：uv workspace、目录结构、代码约定
    ├── frontend.md              # web/ 规范：pnpm monorepo、各 app 约定
    └── cross-workspace.md       # 跨 workspace 规范：API 调用约定、接口契约格式
```

### 三层分工

| 层级 | 文件 | 内容 | 修改频率 |
|------|------|------|---------|
| 执行约定 | `CLAUDE.md` | 如何运行命令（uv/pnpm/git 位置） | 低 |
| 技术规范 | `.claude/standards/*.md` | 如何写代码（架构约束、语言规范） | 中 |
| 角色边界 | `.claude/agents/*.md` | 角色职责、工具权限、专属规则 | 低 |

**原则：**
- `CLAUDE.md` 保持现状，不再追加技术规范
- `coder.md` 只写角色边界规则，技术规范通过引用 `standards/` 获取
- `standards/` 各文件独立演进，python 规范更新不影响前端规范
- architect、reviewer 等 agent 同样可以引用 `standards/` 了解技术约束

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

1. 编写 `.claude/standards/python.md`、`frontend.md`、`cross-workspace.md`
2. 定义 7 个 agent 的 `.claude/agents/*.md` 配置文件
3. 新建 `agent-workflow:facilitator` skill
4. 新建 `agent-workflow:code-review-rubric` skill（含 few-shot 示例）
5. 建立 `.agent-workspace/` 目录结构模板
6. 用一个真实子任务跑通完整流程（验证阶段）
7. 根据运行结果调整 agent prompt 和 harness 结构
