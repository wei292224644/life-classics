# Harness V3 设计文档

**日期：** 2026-04-02  
**状态：** 已确认  
**取代：** `2026-04-02-agent-team-workflow-design.md`（v1）、`harness-team-design.md`（v2 草稿）  
**参考：** [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)

---

## 背景与目标

写完 spec 后，通过 `/facilitator` 命令启动 agent team，多 agent 协作完成实现、相互监督打分，产出符合约束的代码。验证方式为实际执行命令（pytest / curl），不依赖 LLM 读代码判断。

---

## 核心设计原则

1. **生成与评估永远分离** — coder 不评估自己的代码，evaluator 独立验证
2. **Sprint 合约由 coder 提议** — coder 更了解实现边界，提议合约后 evaluator 审核
3. **非 LLM 验证** — evaluator 跑真实命令（pytest/curl），记录实际输出，不靠读代码判断
4. **文件是唯一交接载体** — handoff.md 包含所有必要上下文，SendMessage 只传路径
5. **context 越小越好** — 每个 agent 只装当前任务需要的信息

---

## 架构

### 角色（MVP）

| 角色 | 运行方式 | 职责 |
|------|---------|------|
| **facilitator** | main session skill | 分析任务、建团、编排流程、升级决策 |
| **coder** | team agent，background | 提议合约、实现代码、自检、写 handoff.md |
| **evaluator** | team agent，background | 审核合约、执行验证命令、写 verdict.md |

> reviewer 为第二阶段加入，不在 MVP 范围。

### 启动流程

调用方式：`/facilitator <RUN_DIR>`，其中 `RUN_DIR` 是工作目录路径（如 `.agent-workspace/runs/2026-04-02-user-auth`），用户在调用时指定。

```
你 → /facilitator .agent-workspace/runs/YYYY-MM-DD-<topic>
         ↓
    确认 {RUN_DIR}/spec.md 和 {RUN_DIR}/plan.md 存在
    读取两文件，复述理解，等用户确认
         ↓
    从 plan.md 提取子任务列表，确定依赖顺序
    判断每个子任务的规模（见下方规模表）
         ↓
    TeamCreate("harness-team")
    Agent(name="coder",     subagent_type="coder",     background=true, team_name="harness-team")
    Agent(name="evaluator", subagent_type="evaluator", background=true, team_name="harness-team")
```

### 任务规模判断

| 规模 | 特征 | 处理方式 |
|------|------|---------|
| 小（bug fix）| 单文件改动，无新接口 | 跳过 sprint-contract 阶段，coder 在 handoff.md 里写明修复内容和验证命令，evaluator 直接验收 |
| 中（新功能）| 单 workspace，有新接口 | 完整流程 |
| 大（跨 workspace）| 多 workspace | facilitator 从 plan.md 提取各 workspace 的子任务，按依赖顺序当作多个中任务串行执行 |

### 子任务循环

**完整流程（中/大任务）：**

```
mkdir -p {RUN_DIR}/tasks/{task-id}
         ↓
── 阶段 1：Sprint Contract ──────────────────────────────
SendMessage(coder, "提议合约\nTask:{id}\nspec:{path}\nplan:{path}")
         ↓  收到 coder 完成通知
sprint-contract.md 写入
         ↓
SendMessage(evaluator, "审核合约\nsprint-contract:{path}")
         ↓  收到 evaluator 完成通知
读取 sprint-contract.md 末尾审核结论
         ↓
approved → 继续
rejected → SendMessage(coder, "修改合约:{原因}") → 再审
           仍 rejected → 升级给用户
         ↓
── 阶段 2：实现 ─────────────────────────────────────────
SendMessage(coder, "合约已确认，开始实现\nsprint-contract:{path}")
         ↓  收到 coder 完成通知
检查 contract-dispute.md 是否存在：
  存在 → 读取内容，仲裁
          接受替代方案 → 更新 sprint-contract，SendMessage(coder, "继续实现，合约已更新")
                         → 收到通知 → 检查 dispute（应已消失）→ 继续
          拒绝 → SendMessage(coder, "必须按原合约实现") → 收到通知 → 继续
  不存在 → 继续（handoff.md 已写入）
         ↓
── 阶段 3：验收 ─────────────────────────────────────────
SendMessage(evaluator, "验收\nhandoff:{path}\nsprint-contract:{path}\n验收轮次:{N}")
         ↓  收到 evaluator 完成通知
读取 verdict.md 最后一行
         ↓
pass → 子任务完成，继续下一个
fail → SendMessage(coder, "修复\nverdict:{path}") → verdict_fails++
       verdict_fails >= 2 → 升级给用户
```

**小任务简化流程（bug fix / 单文件改动）：**

```
mkdir -p {RUN_DIR}/tasks/{task-id}
SendMessage(coder, "直接实现\nTask:{id}\n描述:{task描述}\nspec:{path}\n请在 handoff.md 中写明修复内容和验证命令")
         ↓  收到通知
检查 contract-dispute.md（同上）
         ↓
SendMessage(evaluator, "验收（小任务，无 sprint-contract）\nhandoff:{path}\n验收轮次:{N}\n请按 handoff.md 中的验证命令逐条执行")
         ↓
pass / fail（同完整流程）
```

**同一子任务内复用 agent 实例**（SendMessage resume，保留修复上下文）。  
**新子任务不重建 team**，复用同一 team 的 agent（每次任务 agent 仍会重新读规范文档）。

---

## Sprint Contract

**由 coder 提议，evaluator 审核。**

### 格式

```markdown
# Sprint Contract: {task-id}

## 任务描述
{一句话}

## 技术约束
- workspace: {server / web/console / web/uniapp}
- 不允许修改: {列表，无则填 none}

## 完成标准（可用命令验证）
- [ ] {标准1}：验证命令 `{cmd}`
- [ ] {标准2}：验证命令 `{cmd}`

## 超出范围
{此次不做的事，强制填写}
```

### 审核结论（evaluator 追加到文件末尾）

```markdown
## 审核结论
approved

（或）

## 审核结论
rejected: {具体原因}
```

### 关键约定

- 完成标准必须包含验证命令，禁止"功能正常"类模糊表述
- evaluator 协商不超过 1 轮，无法达成则 facilitator 介入仲裁
- coder 提议时若已知某条标准无法实现，直接在合约里注明，不要先接受再 dispute

---

## Handoff 文档

coder 完成实现并自检后写入，是 evaluator 验收的主要输入。

### 格式

```markdown
# Handoff: {task-id}

## 实现摘要
{做了什么}

## 文件变更
- 新建：{路径}
- 修改：{路径}: {改了什么}

## 关键决策
{为什么这样实现}

## 自检结果
- [x] {标准1}：{自检说明}
- [?] {标准2}：{不确定，需 evaluator 验证，原因是...}

## 已知问题
{如实填写，没有则填 none，不得隐瞒}

## 验证命令
- `{cmd1}`
- `{cmd2}`
```

---

## Contract Dispute

coder 在实现过程中发现合约中某条标准存在真正的技术阻碍时：

1. 写 `{RUN_DIR}/tasks/{task-id}/contract-dispute.md`：

```markdown
# Contract Dispute: {task-id}

## 问题标准
{哪一条}

## 技术原因
{为什么无法实现}

## 建议替代方案
{可行的替代验证方式}
```

2. **写完 dispute.md 后直接退出**（完成本轮 SendMessage），不继续实现
3. facilitator 收到完成通知后检测到 dispute.md，仲裁：
   - 接受替代方案 → 更新 sprint-contract，重新 SendMessage(coder, "继续实现")
   - 拒绝 → SendMessage(coder, "必须按原合约实现") → coder 继续

---

## Verdict 文档

evaluator 实际执行验证命令后写入。

### 格式

```markdown
# Verdict: {task-id} — 第 {N} 次验收

## 逐条验证
| 完成标准 | 验证命令 | 实际输出 | 结果 |
|---------|---------|---------|------|
| {标准1} | `{cmd}` | {输出摘要} | pass/fail |
| {标准2} | `{cmd}` | {输出摘要} | pass/fail |

## 失败原因（如有）
{具体描述哪条失败，失败输出是什么}

{pass / fail}
```

> 最后一行只写 `pass` 或 `fail`，facilitator 只读这一行做决策，不读其他内容。

---

## Coder 架构感知

coder 在提议合约和实现前，必须先读取架构规范：

1. 读取 `CLAUDE.md`，找到"架构规范索引"章节
2. 根据当前 workspace 找到对应的架构规范文档（如 `docs/architecture/server-architecture.md`）
3. 读取规范文档，了解禁止事项和设计约束
4. 在合约和实现中遵守规范

---

## 上下文管理

### SendMessage 只传路径

```
Task: {task-id}
RUN_DIR: {path}
spec: {RUN_DIR}/spec.md
sprint-contract: {RUN_DIR}/tasks/{task-id}/sprint-contract.md
handoff: {RUN_DIR}/tasks/{task-id}/handoff.md
verdict: {RUN_DIR}/tasks/{task-id}/verdict.md
```

agent 收到消息后自己读文件，不在消息里塞内容。

### Facilitator 只读摘要

| 文件 | facilitator 只读 |
|------|----------------|
| sprint-contract.md | "审核结论"章节 |
| handoff.md | "已知问题"章节 |
| verdict.md | 最后一行 pass / fail |

### Context 连续性

- **同一子任务内**：SendMessage resume 同一 agent 实例，修复时保留上下文
- **跨子任务**：复用同一 team，不重建。若 agent 上下文异常，可 TeamDelete 后重建

---

## 文件结构

```
.agent-workspace/
├── spec.md                      # 只读，人工阶段产出
├── plan.md                      # 只读，人工阶段产出
├── summary.md                   # facilitator 写（收尾）
└── tasks/
    └── {task-id}/
        ├── sprint-contract.md   # coder 写，evaluator 审核追加结论
        ├── contract-dispute.md  # coder 写（有争议时），facilitator 仲裁后删除
        ├── handoff.md           # coder 写（可追加修复轮次）
        └── verdict.md           # evaluator 写
```

---

## 权限边界

| 角色 | tools | 限制（system prompt 约束） |
|------|-------|--------------------------|
| coder | Task, Read, Write, Edit, Glob, Grep, Bash | 只实现合约范围内的功能 |
| evaluator | Read, Write, Bash | 不修改业务代码，只读代码 + 跑命令 + 写 verdict/审核结论 |

---

## 循环控制与升级

| 场景 | 最大次数 | 超出后 |
|------|---------|--------|
| sprint contract 协商 | 1 轮 | facilitator 介入仲裁 |
| evaluator 验收失败 → coder 修复 | 2 次 | facilitator 升级给用户 |
| contract dispute 仲裁 | 1 次 | 用户决策 |

### 升级模板

```markdown
## ⚠️ 需要人工介入

**任务：** {task-id}
**原因：** {具体原因}
**相关文件：** {verdict.md / sprint-contract.md 路径}

### 待确认
- [ ] 请告知如何处理，或直接修改相关文件后继续
```

---

## MVP 范围

**第一阶段（当前）：** facilitator + coder + evaluator

**第二阶段（后续评估后加入）：** reviewer，静态代码质量评分（4 维：正确性、安全性、代码质量、可维护性）
