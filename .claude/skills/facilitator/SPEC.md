# Facilitator Harness v3 设计规范

> 最后更新：2026-04-03

---

## 背景与目标

现有的 `facilitator`（harness v3）在执行大 spec 时效率低下——所有任务串行分发，忽略了任务间的依赖关系和并行可能性。

**目标**：重新设计 facilitator，支持按依赖图并行分发 coder，显著提升大 spec 的执行效率。

---

## 核心设计决策

### 1. Facilitator 职责定位

- **不做**：写代码，做技术判断、决定实现细节
- **做**：建团、分析任务依赖、分发任务、协调 agent 间通信、汇总结果、决定升级

### 2. Agent 架构（1:1:1 三元组）

每个任务由一个专属三元组负责，**不共享 Observer/Evaluator**：

| Agent | 数量 | 职责 | 做什么 | 结果发给谁 |
|-------|------|------|--------|----------|
| **Coder-N** | 每任务 1 个 | 实现 | 写代码 + 自检（handoff.md 写清楚自检结果） | → Facilitator（仅报完成/升级） |
| **Observer-N** | 每任务 1 个 | 审阅 | 审阅 Coder 的自检质量，补充遗漏，给修复建议 | → Coder-N |
| **Evaluator-N** | 每任务 1 个 | 测试 | 功能测试（pytest），报告 pass/fail | → Coder-N |

**核心通信原则**：
- Coder 直接通知自己的 Observer 和 Evaluator，**不经过 Facilitator 中转**
- Observer 和 Evaluator 互不通信，都只返回给配对的 Coder
- Coder 收到两方反馈后自行决定下一步（修复 or 完成）
- Facilitator 只在任务**整体完成或升级**时收到 Coder 通知

**Observer 不做**：
- 不写代码
- 不做功能测试
- 不和 Evaluator 通信

**Observer 做**：
- 审阅 Coder 的自检是否完整
- 审阅代码是否符合架构规范、code-standards
- 指出 Coder 遗漏或判断错误的地方
- 给出具体修复建议

### 3. Agent 数量

总 agent 数 = **3N**（N 为并行任务数）。Facilitator 在 TeamCreate 时按任务数预建三元组。

### 4. 任务关系类型

| 类型 | 描述 | 处理方式 |
|------|------|----------|
| **独立任务** | 不依赖任何其他任务的产出 | 立即分发，并行执行 |
| **等待任务** | 依赖其他 coder 的产出（文件路径、数据结构） | 等被依赖方完成后，主理人转发输入再分发 |
| **协作任务** | 两个 coder 需要实时协调（如接口契约） | **合并为一个任务**，避免跨 coder 通信 |

**合并判断标准（必须满足至少一条）**：
- 两个 task 读写同一个文件/数据结构
- 一个 task 的输出是另一个 task 的直接输入（含 API provider + consumer 的情况）

**可以不合并的情况**：
- 只是都读某个共享配置（但不改它）
- 时序上有关联但逻辑独立（依赖关系通过 handoff.md 传递产出物即可）

### 5. Coder 间通信

**方式**：**不依赖 peer DM**，主理人充当中介转发产出物

```
Task A 完成 → 主理人读取 handoff.md 中的产出路径 → 转发给 Task B → Task B 继续
```

**决策**：不需要 coder 间直接 peer DM。

原因：
- 如果两个 coder 需要实时协调，说明它们应该**合并为一个任务**
- 依赖关系用"产出物传递"（handoff.md 路径）就足够，无需双向通信
- peer DM 会让 Facilitator 失去对任务状态的可见性

### 6. Agent 数量与规模判断

- **初始数量**：基于 task-graph.md 分析结果，在 TeamCreate 时**预先创建所有三元组**（每任务 1 个 coder + 1 个 observer + 1 个 evaluator）
- **后续按需**：Layer N 开始前，如需新增任务，同步创建对应三元组
- **规模判断**：由 Facilitator 读 plan.md 独立判断；总 agent 数 = 3 × 并行任务峰值数

### 7. Observer 审阅职责

Observer 审阅 Coder 的 handoff.md，聚焦于：

| 审阅维度 | 具体内容 |
|---------|---------|
| **自检完整性** | Coder 的自检是否覆盖了所有完成标准？有没有遗漏？ |
| **架构规范** | 是否遵循 L1/L2/L3 分层？是否有越权 import？ |
| **代码规范** | 命名、文件布局是否符合 code-standards？ |
| **实现质量** | 自检结果是否可信？有没有明显遗漏的 edge case？ |

Observer **必须读取以下文件**：
- `handoff.md`（含本次实现的文件清单）
- `handoff.md` 中列出的所有实现文件
- `code-standards/` 下对应语言/框架的规范文件
- 项目 `CLAUDE.md`（如有）
- `docs/architecture/` 下的架构规范（如有）

Observer **不**做：
- 不执行功能测试（Evaluator 负责）
- 不和 Evaluator 通信

Observer **给**：
- 具体的修复建议（不是"有问题"，而是"X 应该改成 Y"）

**Observer 输出格式**（写入 `{RUN_DIR}/tasks/{task-id}/observer-review.md`）：

```markdown
## 审阅结论

**结论**：通过 / 需要修复

## 逐项检查

| 审阅维度 | 结论 | 具体说明 |
|---------|------|---------|
| 自检完整性 | 通过 | - |
| 架构规范 | 需修复 | X 应该改成 Y（{文件}:{行号}） |
| 代码规范 | 通过 | - |
| 实现质量 | 通过 | - |

## 修复建议（如有）
- `{文件路径}:{行号}` — {具体建议}
```

**消息格式**（Coder 直接发给配对的 Observer）：
```
SendMessage(to="observer-{N}", 请审阅 {RUN_DIR}/tasks/{task-id}/handoff.md)
```

每个 Observer 只服务一个 Coder，无需队列管理。


### 8. Evaluator 职责

**Evaluator 数量**：每任务 **1 个专属实例**，只服务配对的 Coder，无队列管理。

**消息格式**（Coder 直接发给配对的 Evaluator）：
```
SendMessage(to="evaluator-{N}", 请读取 {RUN_DIR}/tasks/{task-id}/handoff.md，执行验收测试)
```

**round 号维护**：由 Coder 在 `state.json` 中记录（初始为 1，每次修复后 +1），写新 handoff.md 前先备份旧版本。Evaluator 无需感知 round 号——每次收到请求时直接读最新的 `handoff.md` 执行测试即可。

**测试数据由 Coder 准备，不是 Evaluator。**

| 任务类型 | 测试方式 | Evaluator 职责 |
|---------|---------|---------------|
<!-- | **API endpoint** | Evaluator 启动服务 + 发真实 HTTP 请求 | 执行并报告 | -->
| **模块/编排逻辑** | Evaluator 执行 pytest（Coder 已写好测试） | 执行并报告 |

**原则**：
- 测试数据由 Coder 准备（Coder 知道模块期望什么格式，会构造模拟数据）
- Evaluator 不 mock 模块函数本身（调的是真实函数）
- Coder 在 sprint-contract 里写清楚测试命令和测试数据位置
- Evaluator 给具体反馈（不只是 pass/fail，还有实际输出和修复建议）


```
参考 V1 Evaluator：
- "FAIL — Tool only places tiles at drag start/end points instead of filling the region."
- "FAIL — PUT /frames/reorder route defined after /{frame_id} routes."
```

**Evaluator 反馈格式**（写入 `{RUN_DIR}/tasks/{task-id}/verdict.md`，由 **Evaluator** 负责撰写）：
```markdown
## 逐条验证
| 完成标准 | 验证命令 | 实际输出 | 结果 |
|---------|---------|---------|------|
| API 返回正确 JSON | pytest tests/api/test_analysis.py | 1 passed | pass |

## 失败原因（如有）
- {标准X}：{具体 bug 描述}
  - 实际输出：{...}
  - 修复建议：{...}
```

### 9. 多轮修复（并行重审 + 重测）

**流程**：
1. Coder 修复 → 将旧 `handoff.md` 移至 `handoff.v{N}.bak`（N 为新版本号）→ 写新 `handoff.md` → **重新并行提交** Observer 审阅 + Evaluator 重测
2. 直到两者都 pass

**版本隔离规则**：
- Coder 修复时**不覆盖**，而是用版本后缀备份：`handoff.v1.bak`, `handoff.v2.bak` ...
- Evaluator 和 Observer 始终读最新的 `handoff.md`（而非自己记住的版本号）
- Facilitator 发给 Observer/Evaluator 的消息中**不包含版本号**，只说"请读取 task-X 的 handoff.md"
- Evaluator 和 Observer **读完再测/审**，测/审期间 Coder 不得覆盖 handoff.md（这是隐式协议——Coder 在收到两方反馈前不应覆盖）

**完成标准**：**Observer 和 Evaluator 都 pass** 才算任务完成。两者是独立维度，必须同时满足。

**Evaluator 反馈要求**：
- 具体到文件、行号、预期值
- 修复建议要可直接执行

**Observer 先到、Evaluator 未到时**：Coder 等待 Evaluator 结果后再决定下一步（不因单方反馈提前行动）。

**多轮修复终止条件**：Evaluator 连续 fail **3 轮**，或 Observer 连续要求修复 **3 轮**（两者各自独立计数，任一达到阈值即升级），Facilitator 升级给用户，任务标记 `ESCALATED`。

---

## 工作流程

### 第一步：前置检查

1. 获取 `RUN_DIR` 参数
2. 确认 `{RUN_DIR}/spec.md` 和 `{RUN_DIR}/plan.md` 存在
3. 读取两文件，用 2-3 句话复述理解，等用户确认

### 第二步：任务结构分析（Facilitator 独立完成）

**输入**：plan.md

**输出**：`{RUN_DIR}/task-graph.md`

**分析内容**：
1. 提取任务列表（编号 + 描述）
2. 分析每个任务的输入/输出
3. 标注依赖关系（Task B 依赖 Task A 的哪些产出）
4. 识别协作点
5. 划分执行层（Layer）
6. **任务分组方案**（关键决策）：
   - 哪些任务可**合并**为一个 coder 处理（协作任务）
   - 哪些任务需要**独立** coder（复杂任务）
   - 估算 **coder 数量需求**

**task-graph.md 格式**：

```markdown
# 任务依赖图

## 任务列表
- Task 1: 描述
- Task 2: 描述
- ...

## 依赖关系
- Task 1 → [无依赖]
- Task 2 → [依赖 Task 1 的产出: {具体输入}]
- Task 3 → [依赖 Task 1, Task 2 的产出: {具体输入}]

## 执行层
- Layer 0: Task 1, Task 3（无依赖，并行）
- Layer 1: Task 2（等待 Task 1 完成）
- Layer 2: Task 4（等待 Task 2, Task 3 完成）

## 协作点
（无——本例中所有任务均可独立或通过产出物传递实现依赖，无需跨 coder 实时协调）

## 任务分组方案

### 分组逻辑
| 组 | 包含任务 | 分配 coder | 理由 |
|---|---------|-----------|------|
| 组 1 | Task 1 | coder-1 | 独立任务，并行 |
| 组 2 | Task 3 | coder-2 | 独立任务，并行 |
| 组 3 | Task 2 | coder-3 | 独立任务，并行 |
| 组 4 | Task 4 + Task 5 | coder-4 | 协作任务，接口契约强耦合，合并处理 |

### Coder 数量估算
- Layer 0 峰值并行数：2（Task 1, Task 3）
- 协作合并占用：1（Task 4+5）
- **所需 coder 总数：4**
```

### 第三步：建立 Agent Team（基于任务分组方案）

**前置条件**：已完成 task-graph.md，包含"任务分组方案"章节。

**决策规则**：
- coder 数量 = task-graph.md 中"所需 coder 总数"
- observer：1 个
- evaluator：1 个

```
TeamCreate("harness-team")

# 每任务一个三元组：coder-N + observer-N + evaluator-N
Agent(name="coder-1",    subagent_type="coder",     team_name="harness-team", run_in_background=true)
Agent(name="observer-1", subagent_type="observer",  team_name="harness-team", run_in_background=true)
Agent(name="evaluator-1",subagent_type="evaluator", team_name="harness-team", run_in_background=true)

Agent(name="coder-2",    subagent_type="coder",     team_name="harness-team", run_in_background=true)
Agent(name="observer-2", subagent_type="observer",  team_name="harness-team", run_in_background=true)
Agent(name="evaluator-2",subagent_type="evaluator", team_name="harness-team", run_in_background=true)
# ... 以此类推，按任务总数创建
```

**后续 Layer 的三元组按需创建**：Layer N 开始前，根据新增任务数同步创建对应三元组。

### 第四步：按层执行

#### Layer 0：首次分发

所有 Layer 0 任务**同时并行**分发，每任务对应一个专属 coder。

> **`{task-id}` 命名规范**：`task-{N}`，如 `task-1`、`task-2`。若多个原始任务合并为一个 coder 处理，使用主任务编号，如 `task-4`（含 Task 4 + Task 5）。

```
mkdir -p {RUN_DIR}/tasks/{task-id}
SendMessage(to="coder-1", Task 1: sprint-contract 描述)
SendMessage(to="coder-2", Task 2: sprint-contract 描述)
...
SendMessage(to="coder-N", Task N: sprint-contract 描述)
```

#### Sprint Contract 格式

Coder 收到任务后，在 `{RUN_DIR}/tasks/{task-id}/sprint-contract.md` 中写入合约。

> **小任务豁免**：预计修改文件 ≤ 2 个且无跨模块依赖的任务，Coder 可跳过合约直接实现，并在 handoff.md 中补充完成标准和测试命令。

**sprint-contract.md 格式**：

```
## 任务描述
{一句话描述任务目标}

## 实现方案
{技术方案概述，包含关键设计决策}

## 完成标准
- [ ] {具体、可验证的标准 1}
- [ ] {具体、可验证的标准 2}

## 测试命令
{执行测试的完整 shell 命令，如: cd server && uv run pytest tests/xxx.py -v}

## 测试数据位置
{测试数据文件路径或构造方式}

## 涉及文件
- 新建：{路径列表}
- 修改：{路径列表}
```

> Coder 完成合约后通知 Facilitator，由 Facilitator 审核后决定是否进入实现阶段。

#### Sprint Contract 审核（Facilitator）

所有 Layer 0 coder 合约完成后，**Facilitator 读取并审核**所有合约：
- 检查完成标准是否清晰、无歧义
- 检查实现方案是否合理
- 检查测试命令和测试数据是否完备

Facilitator 审核结果处理：
- 全部 approved → 进入实现
- 有 rejected → 发给对应 coder 修订 → 重新提交审核
- 仍 rejected → 升级给用户

> **注意**：此阶段 Evaluator 不参与合约审核，Evaluator 只在实现完成后的功能验收阶段工作。

#### 实现

所有合约确认后，并行分发实现：
```
SendMessage(to="coder-N", sprint-contract 已确认，开始实现)
```

#### Observer 审阅 + Evaluator 功能测试（并行）

Coder 实现完成，写 handoff.md（含自检结果），**直接并行通知配对的 Observer 和 Evaluator**：

```
Coder-N 并行发出：
SendMessage(to="observer-N",   请审阅 {RUN_DIR}/tasks/{task-id}/handoff.md)
SendMessage(to="evaluator-N",  请读取 {RUN_DIR}/tasks/{task-id}/handoff.md，执行验收测试)
```

**Observer 和 Evaluator 并行工作，互不通信**，结果分别返回给 Coder-N：
- Observer-N → 返回：通过 / 需要修复（附具体建议）
- Evaluator-N → 返回：pass / fail（附验证输出）

**Coder 收到两方反馈后决定下一步**：
- **两者都 pass** → 通知 Facilitator 任务完成，更新 state.json status=COMPLETED
- 任一方需修复 → Coder 修复 → 备份旧 handoff.md → 写新 handoff.md → 重新并行发给 Observer-N + Evaluator-N
- 连续 3 轮未通过 → 通知 Facilitator 升级，更新 state.json status=ESCALATED

#### Layer N：依赖就绪驱动分发

前置条件：**不要求前置 Layer 全部完成**，根据每个任务的依赖是否就绪来决定分发时机。

**Facilitator 主循环**（每个 Layer 开始前执行一次，或在每次任务完成时触发）：

```
for each pending task in current Layer:
  if all dependencies have verdict.md with status=COMPLETED:
    read dependency handoff.md, extract inputs
    dispatch task (并行分发)
  else if any dependency has status=ESCALATED:
    mark task as BLOCKED
    escalate dependency failure
  else:
    # 依赖还在运行中，暂时跳过，下轮再检查
    continue
```

**依赖就绪的定义**：所有依赖任务的 `verdict.md` 存在且 `status=COMPLETED`。Coder 完成实现后主动 SendMessage 给 Facilitator，Facilitator 收到通知后触发主循环检查，决定是否分发后续任务。

**状态说明**：
- `status` 字段在 `state.json` 中定义（见下方状态机）
- 任意状态为 `ESCALATED` 的依赖都会级联阻塞下游任务

**按需创建 coder**：每次主循环中，如当前 pending 任务数超过可用 coder 余量，新增 coder（不替换已存在的）。


### 第五步：收尾

所有任务完成后，写 `{RUN_DIR}/summary.md`：

```markdown
# Summary

## 完成情况
| 任务 | Layer | 状态 | 验收轮次 | 备注 |
|------|-------|------|----------|------|
| Task 1 | 0 | 完成 | 1 | - |
| Task 2 | 1 | 完成 | 2 | 修复 1 次 |
| Task 3 | 0 | 升级 | - | 多轮修复无果，暂时不处理 |

## 产出物
- `{RUN_DIR}/tasks/{task-id}/verdict.md`（**Evaluator 撰写**，记录逐条验证结果）

## 已知问题
{none / 具体问题}
```

---

## 代码规范体系

### 规范来源分工

| 内容 | 放哪 | 谁维护 |
|------|------|--------|
| 通用代码规范（命名、文件布局、错误处理）| `harness-team/code-standards/` | harness 模板 |
| 语言/框架专用规范（FastAPI、React 等）| `harness-team/code-standards/` | harness 模板 |
| 项目架构（L1/L2/L3、禁止规则）| `CLAUDE.md` + `docs/architecture/` | 项目本身 |
| 模块局部模式 | Coder 自己读现有代码 | - |

### `harness-team/code-standards/` 结构

```
harness-team/code-standards/
├── README.md                # 索引：遇到 X 读 Y
├── common/
│   ├── file-layout.md       # 文件放哪、叫什么
│   ├── naming.md           # 命名规范
│   └── error-handling.md   # 错误处理通用模式
├── python/
│   └── fastapi.md          # FastAPI 专用（通用模式，非项目架构）
└── typescript/
    └── react.md
```

### Coder 获取规范的方式

在 `coder.md` agent 描述里明确指定：

```markdown
## 开始前必须做

1. 读取 `code-standards/README.md` 了解整体规范索引
2. 根据任务类型，读对应的规范文件
3. 读取项目的 `CLAUDE.md`（如有）

## 当你进入一个新目录时

1. 读该目录下的 `__init__.py` 了解模块结构
2. 读 1-2 个现有文件理解代码模式
3. 再开始写新代码
```

---

## 任务状态机

每个任务的状态记录在 `state.json` 中，Facilitator 读写此文件判断任务所处阶段。`verdict.md` 只记录 Evaluator 的测试结果，不承载任务生命周期状态。

**文件职责分工**：
- `state.json`：任务生命周期状态 + round 号（Facilitator 维护）
- `verdict.md`：Evaluator 测试结果表（Evaluator 写入）
- `observer-review.md`：Observer 审阅结论（Observer 写入）

```
PENDING                    # 任务在队列中，尚未分发
  ↓
IN_CONTRACT                # Facilitator 已分发 sprint-contract 给 coder
  ↓
IN_IMPLEMENTATION          # 合约 approved，Coder 正在实现
  ↓
IN_REVIEW                  # Coder 已写 handoff.md，并行提交 Observer + Evaluator
  ↓ (两者都 pass)           ↓ (任一方打回)
COMPLETED                  IN_IMPLEMENTATION   # 修复后重新进入 IN_REVIEW
                             ↓ (连续3轮均未通过)
                           ESCALATED           # 升级给用户（终结失败状态）
                             ↓ (影响下游任务)
                           BLOCKED             # 依赖任务升级，级联阻塞（终结失败状态）
```

**Facilitator 只关注 `COMPLETED` / `ESCALATED` / `BLOCKED` 三种终结状态**，依此驱动下游任务调度。中间状态由各 Agent 完成阶段后写入 `state.json`。

> **注意**：`FAILED` 不是任务状态，是 `verdict.md` 测试结果表中的单行结果（`pass` / `fail`）。任务本身只有 `ESCALATED` 和 `BLOCKED` 两种终结失败状态。

---

## Contract Dispute 处理流程

当 Facilitator 收到两个或以上 coder 对同一接口/文件给出不兼容的实现方案时：

1. **Facilitator 读取**所有相关方的合约，找出分歧点
2. **Facilitator 提出调解方案**，发给相关 coder 确认
3. 如 coder 接受 → 更新合约，继续执行
4. 如 coder 拒绝 → Facilitator 将分歧 + 两方立场打包，**升级给用户**
5. 升级期间：**其他无依赖的任务继续执行**；涉事任务标记 `BLOCKED`

---

## 升级机制

### 升级条件

- Observer 审阅发现无法修复的问题
- 依赖任务失败导致后续任务无法分发
- Coder 报告 BLOCKED / NEEDS_CONTEXT
- Contract Dispute 发生且无法解决

### 升级格式

```markdown
## ⚠️ 需要人工介入

**任务：** {task-id}
**Layer：** {N}
**原因：** {具体原因}
**当前状态：** {验收失败 / Observer 审阅失败 / 依赖任务失败}
**相关文件：** {路径}

### 待确认
- [ ] 请告知如何处理
```

---

## 已确认设计决策

| 问题 | 结论 | 日期 |
|------|------|------|
| Agent 数量 | 3 个：Coder、Observer、Evaluator | 2026-04-03 |
| Coder peer DM | 不需要，协作任务合并为一个；依赖用产出物传递 | 2026-04-03 |
| Evaluator 并行 | 串行足够，验收无副作用不会成瓶颈 | 2026-04-03 |
| Coder 数量 | 初始基于 task-graph 分析，后续按需创建 | 2026-04-03 |
| Observer/Evaluator 模型 | 1:1:1 三元组，每任务专属，无共享队列 | 2026-04-03 |
| Observer 职责 | 审阅 Coder 自检质量，不做功能测试；写 observer-review.md | 2026-04-03 |
| Observer/Evaluator 通信 | Coder 直接发给配对的 Observer-N / Evaluator-N，不经 Facilitator | 2026-04-03 |
| 测试数据来源 | Coder 准备模拟数据，Evaluator 执行测试 | 2026-04-03 |
| Layer 调度模型 | Layer 是概念分组；实际调度依赖就绪驱动，非 Layer 批次驱动 | 2026-04-03 |
| Sprint Contract | Coder 写入 sprint-contract.md；Facilitator 审核后进入实现 | 2026-04-03 |
| task-id 命名 | `task-{N}`，合并任务用主任务编号 | 2026-04-03 |
| FAILED vs 任务状态 | FAILED 是 verdict.md 测试行结果，非任务状态；任务终结失败状态为 ESCALATED | 2026-04-03 |
| Facilitator 唤醒机制 | Coder 完成/升级后主动 SendMessage 给 Facilitator，触发主循环 | 2026-04-03 |
| round 号维护 | Coder 记录于 state.json，每次修复 +1；Evaluator 直接读最新 handoff.md | 2026-04-03 |
| 多轮修复竞态 | handoff.vN.bak 版本隔离；Coder 在收到两方反馈前不覆盖 handoff.md | 2026-04-03 |
| Contract Dispute | Facilitator 调解 → 升级用户，期间其他任务继续 | 2026-04-03 |

---

## 文件清单

```
.claude/skills/facilitator/
├── SKILL.md                 # Facilitator 执行流程
└── SPEC.md                  # 本文档（设计决策记录）

{RUN_DIR}/tasks/{task-id}/
├── sprint-contract.md       # Coder 写入，Facilitator 审核
├── handoff.md               # Coder 实现完成后写入（含自检结果）
├── handoff.v{N}.bak         # 多轮修复时的历史备份
├── observer-review.md       # Observer 写入审阅结果
├── verdict.md               # Evaluator 写入验收结果（含 status frontmatter）
└── state.json               # Facilitator 维护，记录 round 号等运行时状态

harness-team/
├── coder.md                 # Coder agent 描述（含规范获取指引）
├── observer.md              # Observer agent 描述
└── code-standards/          # 通用代码规范（与项目无关）
    ├── README.md
    ├── common/
    │   ├── file-layout.md
    │   ├── naming.md
    │   └── error-handling.md
    ├── python/
    │   └── fastapi.md
    └── typescript/
        └── react.md
```
