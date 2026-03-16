# 设计文档：classify_node 前言切分优化

**日期**：2026-03-16
**状态**：已批准

## 背景与问题

`classify_node` 在处理 GB 食品安全标准的"前言"章节时，将其切分得过于细碎。以 GB1886.47-2016 为例，前言本应作为整体（版本代替声明 + 所有修订条目），却被拆分为 7 个 segment（标题、代替声明、引导句、4 条独立变更条目），每条变更条目脱离上下文后语义不完整，严重影响 RAG 检索质量。

**根本原因：**
1. classify 的 prompt 要求"拆分为语义独立的片段"，激励 LLM 尽可能细粒度切分。
2. `content_type_rules.json` 缺少 `preface` 类型，导致 LLM 用 `standard_header` 和 `numbered_list` 混合处理前言内容。

## 目标

前言章节整体作为一个 segment，类型为 `preface`，内部变更条目列表不拆分。

## 方案（C = A + B）

### A. 新增 `preface` content type

在 `app/core/parser_workflow/rules/content_type_rules.json` 的 `content_types` 数组中追加：

```json
{
  "id": "preface",
  "description": "标准前言，包含版本代替关系及主要修订说明，整体作为一个语义单元，内部列表项不拆分",
  "transform": {
    "strategy": "plain_embed",
    "prompt_template": "请将以下标准前言内容转化为规范化的版本元数据陈述，保留所有版本号、代替关系及修订说明条目：\n"
  }
}
```

### B. 修改 classify prompt（`classify_node.py`）

在现有 prompt 末尾（返回格式之前）追加保守切分原则：

```
保守切分原则（不满足以下条件时，不拆分）：
1. 只在相邻内容属于明显不同的 content_type 时才切分；同一逻辑章节的内容应保持整体。
2. 标准前言（以"前言"为标题的章节）整体归为 preface 类型，内部变更条目列表不单独拆分。
```

## 预期效果

前言 chunk classify 输出：

| 字段 | 值 |
|------|-----|
| `content_type` | `preface` |
| `confidence` | ~0.95 |
| `content` | 完整前言文本 |
| segments 数量 | 1 |

## 测试策略

更新 `tests/core/parser_workflow/test_classify_node_real_llm.py`：

- 针对前言 chunk（`section_path` 包含"前言"）断言 segments 数量 == 1
- 断言 `content_type` == `"preface"`

## 影响范围

| 文件 | 变更类型 |
|------|---------|
| `app/core/parser_workflow/rules/content_type_rules.json` | 追加 `preface` 类型 |
| `app/core/parser_workflow/nodes/classify_node.py` | 修改 prompt 增加保守切分原则 |
| `tests/core/parser_workflow/test_classify_node_real_llm.py` | 更新断言逻辑 |

## 不在范围内

- 其他 content_type 的切分行为不变
- slice_node 和 transform_node 不受影响
- `standard_header` 类型保留，用于真正的文档头部（标题、发布日期等）
