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
