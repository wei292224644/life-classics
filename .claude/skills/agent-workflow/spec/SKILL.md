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
