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
- 各子任务所属的 workspace（从项目结构或 CLAUDE.md 中确定）
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
