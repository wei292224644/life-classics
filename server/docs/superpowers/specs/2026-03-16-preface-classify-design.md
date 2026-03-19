# 设计文档：classify_node 前言切分优化

**日期**：2026-03-16
**状态**：设计已批准，待实现

## 背景与问题

`classify_node` 在处理 GB 食品安全标准的"前言"章节时，将其切分得过于细碎。以 GB1886.47-2016 为例，前言本应作为整体（版本代替声明 + 所有修订条目），却被拆分为 7 个 segment（标题、代替声明、引导句、4 条独立变更条目），每条变更条目脱离上下文后语义不完整，严重影响 RAG 检索质量。

**根本原因：**
1. classify 的 prompt 要求"拆分为语义独立的片段"，激励 LLM 尽可能细粒度切分。
2. `content_type_rules.json` 缺少 `preface` 类型，导致 LLM 用 `standard_header` 和 `numbered_list` 混合处理前言内容。
3. `standard_header` 的 description 包含"前言"字样，与待新增的 `preface` 语义重叠。
4. 现有 `standard_header` 条目存在 JSON 损坏（`prompt_template` 截断、多余的 `action` 字段）。

## 目标

前言章节整体作为一个 segment，类型为 `preface`，内部变更条目列表不拆分。

## 方案（C = A + B）

### A. 修复 `standard_header` 并新增 `preface` content type

在 `app/core/parser_workflow/rules/content_type_rules.json` 中：

**修复 `standard_header`**（当前 JSON 已损坏，需同时修正 description 边界）：
- 移除多余的 `"action": "create_new"` 字段
- 补全被截断的 `prompt_template` 字符串
- 将 description 限定为纯文档头部信息，明确排除前言章节：

```json
{
  "id": "standard_header",
  "description": "标准文档头部元信息（标准号、发布机构、实施日期等），不含前言章节内容",
  "transform": {
    "strategy": "metadata_standardization",
    "prompt_template": "请将以下标准文档头部信息转化为规范化的元数据陈述。要求：\n1. 准确识别并保留标准全称、标准号、发布及实施日期，保持格式统一。\n2. 明确解析版本替代关系（如有）。\n3. 禁止添加不存在于原文的推断内容。\n\n待处理内容：\n"
  }
}
```

**追加 `preface` 类型**：

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

在现有 prompt 的"返回格式"之前追加保守切分原则（含 few-shot 示例）：

```
保守切分原则：
1. 只在相邻内容属于明显不同的 content_type 时才切分；同一逻辑章节的内容应保持整体。
2. 标准前言（以"前言"为标题的章节）整体归为 preface 类型，内部变更条目列表（如"——增加了..."）不单独拆分。

示例（前言章节的正确输出）：
输入：包含前言标题、代替声明和多条变更条目的文本块
正确输出：1 个 segment，content_type=preface，包含完整前言文本
错误输出：多个 segment，将各变更条目拆分为独立的 numbered_list
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

### 单元测试（不依赖真实 LLM）

新增 `tests/core/parser_workflow/test_classify_node.py`（mock 测试）：
- 验证 `RulesStore.get_transform_params("preface")` 返回 `plain_embed` 策略
- 验证 `_call_classify_llm` 的 prompt 字符串中包含"保守切分原则"和"preface"关键词

### 集成测试（真实 LLM）

更新 `tests/core/parser_workflow/test_classify_node_real_llm.py`：
- 改用 `section_path == ["__preamble__"]` 过滤前言 chunk（而非硬编码索引 3）
- 针对前言 chunk 断言：`len(segments) == 1` 且 `segments[0]["content_type"] == "preface"`

## 影响范围

| 文件 | 变更类型 |
|------|---------|
| `app/core/parser_workflow/rules/content_type_rules.json` | 修复 `standard_header`（JSON 损坏 + description）；追加 `preface` 类型 |
| `app/core/parser_workflow/nodes/classify_node.py` | 修改 prompt 增加保守切分原则和 few-shot 示例 |
| `tests/core/parser_workflow/test_classify_node_real_llm.py` | 更新 chunk 过滤逻辑和断言 |
| `tests/core/parser_workflow/test_classify_node.py` | 新增 mock 单元测试 |

## 不在范围内

- 其他 content_type 的切分行为不变
- slice_node 和 transform_node 不受影响
- 生产环境 rules 目录（`app/core/parser_workflow/rules/`）的 JSON 即为默认规则源，`RulesStore` 初始化时会自动复制到运行时 `rules_dir`，无需额外部署步骤

## 注意事项

- `slice_node` 将前言 chunk 的 `section_path` 设为 `["__preamble__"]`，测试中应以此字段值识别前言 chunk，不可用中文标题匹配
