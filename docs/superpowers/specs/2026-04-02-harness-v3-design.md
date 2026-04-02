# Harness V3 设计文档

**日期：** 2026-04-02  
**状态：** 已确认  
**取代：** `2026-04-02-agent-team-workflow-design.md`  
**参考：** [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)

---

## 背景与目标

写完 spec 后，通过 `/facilitator` 命令启动 agent team，多 agent 协作完成实现、相互监督打分，产出符合约束的代码。验证方式为实际执行命令（pytest / curl），不依赖 LLM 读代码判断。

---

## 核心设计原则

1. **生成与评估永远分离** — coder 不评估自己的代码，evaluator 独立验证
2. **Sprint 合约由 coder 提议** — coder 更了解实现边界，提议合约后 evaluator 审核
3. **非 LLM 验证** — evaluator 跑真实命令（pytest/curl），不靠读代码判断
4. **文件是唯一交接载体** — handoff.md 包含所有必要上下文，SendMessage 只传路径
5. **context 越小越好** — 每个 agent 只装当前任务需要的信息

---

## 架构

### 角色

| 角色 | 运行方式 | 职责 |
|------|---------|------|
| **facilitator** | main session skill | 分析任务、建团、编排流程、升级决策 |
| **coder** | team agent，background | 提议合约、实现代码、自检、写 handoff.md |
| **evaluator** | team agent，background | 审核合约、跑命令验证、写 verdict.md |
| **reviewer** | team agent，background | 静态代码质量评分（MVP 后加入） |

### 启动流程

```
你 → /facilitator skill（main session）
         ↓
    读 spec.md + plan.md，理解任务结构
         ↓
    TeamCreate("harness-team")
    Agent(coder,     subagent_type="coder",     background=true, team_name="harness-team")
    Agent(evaluator, subagent_type="evaluator", background=true, team_name="harness-team")
```

### 子任务循环

```
SendMessage(coder, "Task: {id}\nRUN_DIR: {path}\nspec: {path}\nplan: {path}")
    ↓
coder 提议 sprint-contract.md
    ↓
SendMessage(evaluator, "审核合约\nsprint-contract: {path}")
    ↓
evaluator 审核（可协商，最多 1 轮）
    ↓
SendMessage(coder, "合约已确认，开始实现")
    ↓
coder 实现 → 自检 → handoff.md
    ↓
SendMessage(evaluator, "验收\nhandoff: {path}\nsprint-contract: {path}")
    ↓
evaluator 跑命令（pytest / curl）→ verdict.md
    ↓
pass → 下一子任务
fail → SendMessage(coder, "修复：{失败原因}") → 最多 2 轮 → 超出升级
```

---

## Sprint Contract

**由 coder 提议，evaluator 审核。**

coder 更了解实现约束（哪些能做，哪些做不到），由它先提议更合理。

```markdown
# Sprint Contract: {task-id}

## 任务描述
{一句话}

## 技术约束
- workspace: {server / web/console / web/uniapp}
- 不允许修改: {列表}

## 完成标准（可用命令验证）
- [ ] {具体标准，如：GET /api/xxx 返回 200，body 包含 ...}
- [ ] uv run pytest tests/xxx -v 全部通过

## 超出范围
{明确列出不在此次做的事}
```

**关键约定：**
- 完成标准必须可以用命令验证，禁止"功能正常"这类模糊表述
- evaluator 发现合约不合理可协商，协商不超过 1 轮，无法达成则 facilitator 介入

---

## Handoff 文档

coder 完成实现并自检后写入，是 evaluator 验收的主要输入。

```markdown
# Handoff: {task-id}

## 实现摘要
{做了什么}

## 文件变更
- 新建：...
- 修改：...

## 关键决策
{为什么这样实现}

## 自检结果
- [x] 标准1：{说明}
- [?] 标准2：{不确定，需 evaluator 验证}

## 已知问题
{如有，如实填写，不得隐瞒}

## 验证命令
- `uv run pytest tests/xxx -v`
- `curl -X GET "http://localhost:9999/api/..."`
```

---

## 上下文管理

### SendMessage 只传路径

```
Task: {task-id}
RUN_DIR: {path}
sprint-contract: {RUN_DIR}/tasks/{task-id}/sprint-contract.md
handoff: {RUN_DIR}/tasks/{task-id}/handoff.md
verdict: {RUN_DIR}/tasks/{task-id}/verdict.md
```

agent 收到消息后自己读文件，不在消息里塞内容。

### Facilitator 只读摘要

| 文件 | facilitator 只读 |
|------|----------------|
| verdict.md | 最后一行 pass / fail |
| handoff.md | "已知问题"章节 |
| sprint-contract.md | "完成标准"列表 |

### 同任务内复用 agent 实例

同一子任务内，coder 修复时 SendMessage resume 同一实例（保留上下文）。  
**新子任务创建新实例**，保持 context 干净。

---

## 文件结构

```
.agent-workspace/
├── spec.md                      # 只读，人工阶段产出
├── plan.md                      # 只读，人工阶段产出
└── tasks/
    └── {task-id}/
        ├── sprint-contract.md   # coder 写，evaluator 审核
        ├── handoff.md           # coder 写（可追加）
        └── verdict.md           # evaluator 写
```

---

## 权限边界

| 角色 | subagent_type | 限制（system prompt 约束） |
|------|--------------|--------------------------|
| coder | general-purpose | 无 |
| evaluator | general-purpose | 不修改业务代码，只读代码 + 跑命令 + 写 verdict |
| reviewer | Explore / 自定义 | 只读，写 review.md（MVP 后加入） |

---

## 循环控制与升级

| 场景 | 最大次数 | 超出后 |
|------|---------|--------|
| evaluator 验收失败 → coder 修复 | 2 次 | facilitator 升级给用户 |
| sprint contract 协商 | 1 轮 | facilitator 介入仲裁 |

升级时 facilitator 输出：

```markdown
## ⚠️ 需要人工介入

**任务：** {task-id}
**原因：** {具体失败原因}
**相关文件：** {verdict.md / sprint-contract.md 路径}

### 待确认
- [ ] 请告知如何处理，或直接修改相关文件后继续
```

---

## MVP 范围

**第一阶段（当前）：** facilitator + coder + evaluator

**第二阶段（后续）：** 加入 reviewer，静态代码质量评分

---

## 从 sub-agent 迁移到 agent team

如未来需要切换，只需修改 facilitator skill 的调用方式：

```
# 改前（sub-agent）
Agent(subagent_type="coder", prompt="...")

# 改后（agent team）
SendMessage(to="coder", message="...")
```

文件结构、sprint contract 流程、agent 配置（.claude/agents/*.md）全部不变。
