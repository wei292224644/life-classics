---
name: code-review-rubric
description: reviewer agent 使用的 4 维评分流程。包含评分标准、blocking 阈值和 few-shot 校准示例。
---

# Code Review Rubric

每个 issue 必须有**文件:行号**。没有定位的反馈是无效反馈。

> "发现问题，不修问题。"

**CRITICAL：facilitator 在 prompt 中传入当前轮次号和 handoff 版本名，直接使用，不自行推断。**

## 评分表

分数含义：5 = 无问题 / 4 = minor / 3 = major / 2 = 严重缺陷 / 1 = 根本性错误 / N/A = 不涉及

| 维度 | 含义 | 结论规则 |
|------|------|---------|
| **正确性** | 是否实现了 sprint-contract 的每条完成标准 | ≤ 2 → `needs-revision` |
| **安全性** | OWASP top 10、注入、权限漏洞 | **< 5 分即 `needs-revision`**；无安全敏感代码打 N/A |
| **代码质量** | 风格一致性、命名清晰、不过度复杂 | ≤ 2 → `needs-revision`；3 → `pass-with-notes` |
| **可维护性** | 边界清晰、无隐式耦合、无未来负债 | ≤ 2 → `needs-revision`；3 → `pass-with-notes` |

整体结论优先级：任意维度 `needs-revision` → 整体 `needs-revision`；否则有 `pass-with-notes` → 整体 `pass-with-notes`；否则 `pass`。

## Few-Shot 校准

**正确性 2 分 → needs-revision：**
合约要求 `GET /api/items` 返回分页，实现返回全量数据，缺少 `total`/`page`/`page_size`。

**安全性 → needs-revision（任何问题）：**
用户输入直接拼接进 SQL 字符串，存在注入风险。打 2 分，needs-revision。

**代码质量 4 分 → pass：**
命名使用缩写（`tmp`、`d`），建议拆分超 50 行的函数。属于 minor，4 分，pass。

**全部通过：**
所有标准已实现，无安全漏洞，命名清晰，边界合理。各维度 4-5 分，pass。

## 执行步骤

1. 读取 `{RUN_DIR}/tasks/{task-id}/sprint-contract.md`
2. 读取 facilitator 传入版本的 handoff（初次 `handoff.md`，后续 `handoff-v{n}.md`）
3. 阅读实际代码（Read / Glob / Grep）
4. 按 4 维度打分
5. 写入 `{RUN_DIR}/tasks/{task-id}/review.md`

## review.md 格式

```markdown
# Code Review: {task-id}

## 评分
| 维度 | 分数 | 说明 |
|------|------|------|
| 正确性 | {1-5/N/A} | {具体说明} |
| 安全性 | {1-5/N/A} | {具体说明} |
| 代码质量 | {1-5/N/A} | {具体说明} |
| 可维护性 | {1-5/N/A} | {具体说明} |

## 问题列表

### Blocking
- {文件:行号} {描述}

### Major
- {文件:行号} {描述}

### Minor
- {文件:行号} {描述}

## 结论
{pass / needs-revision / pass-with-notes}
轮次：{facilitator 传入}
```
