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
