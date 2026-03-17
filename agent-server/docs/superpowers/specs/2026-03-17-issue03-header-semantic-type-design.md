# ISSUE-03 修复设计：header segment 的 semantic_type 一致性

**日期：** 2026-03-17
**严重性：** 低
**文件范围：**
- `app/core/parser_workflow/rules/content_type_rules.json`
- `app/core/parser_workflow/nodes/classify_node.py`
- `tests/core/parser_workflow/test_workflow.py`（补充回归测试）

---

## 问题描述

`classify_node` 对 `structure_type=header` 的 segment（纯章节标题行，如 `## A.5 总灰分的测定`）的 `semantic_type` 判断不稳定：大多数 header 被正确标记为 `metadata`，但部分方法节标题（A.5、A.6）被标记为 `definition`，导致同一文档内分类不一致。

### 根因

1. `metadata` 的 description 过窄（仅覆盖"文档身份信息"），LLM 无法将章节标题与 `metadata` 关联。
2. `definition` 的 description（"术语、概念或常数的定义"）对"测定方法节标题"有一定语义吸引力。
3. `examples` 字段虽存在于 JSON 中，但从未被注入 prompt，对 LLM 完全不可见。

---

## 设计决策

### 决策一：扩展 `metadata` 的语义定义

将 `metadata` 的 description 从"文档身份信息"扩展为"文档的组织性信息"，明确将章节标题行纳入其中。

**修改前：**
```json
{
  "id": "metadata",
  "description": "文档身份信息：标准号、发布机构、发布/实施日期"
}
```

**修改后：**
```json
{
  "id": "metadata",
  "description": "文档的组织性信息，包括标准号、发布机构、日期等文件身份信息，以及各级章节标题行"
}
```

**关于语义重叠的说明：** 修改后的 `metadata` description 与 `structure_types` 中 `header`（"纯章节标题，无实质内容"）存在有意为之的语义约束关系：`structure_type=header` 的 segment 必然满足 `semantic_type=metadata`。这一约束通过 description 层面的一致性表达，而非 prompt 规则强制（见"不在范围内"说明）。

**关于与 `scope` examples 的潜在冲突：** `scope` 的 examples 中包含 `"1 范围"` 这一字符串，形式上也是标题。但 `structure_type` 是在拆分阶段对 chunk 整体形式的判断：当 chunk 仅包含标题行（无正文）时为 `header`；当 chunk 包含"1 范围\n本标准适用于..."等正文时，为 `paragraph` 或 `list`，semantic_type 才会命中 `scope`。因此两者不存在实际冲突——`structure_type=header` 的 chunk 不会同时满足 `scope` 的语义条件。

### 决策二：为所有有 `examples` 字段的类型注入示例

在 `classify_node.py` 的 prompt 构建逻辑中，当类型含有 `examples` 字段时，在 description 下方换行缩进追加示例行。由于 `content_type_rules.json` 中 8 个 semantic_type 均已有 examples 字段，此改动会为所有类型注入示例。

针对 `metadata` 和 `definition` 的 examples 内容需特别设计，以从两侧消除歧义：
- `metadata` examples 中增加附录方法节标题（`## A.3 硫酸酯的测定`、`## A.5 总灰分的测定`）
- `definition` examples 中强调"后接术语正文"，与纯标题行区分

**prompt 中的效果（节选）：**
```
- metadata: 文档的组织性信息，包括标准号、发布机构、日期等文件身份信息，以及各级章节标题行
  示例：GB 1886.169—2016 / 2016-08-31 发布 / ## A.3 硫酸酯的测定 / ## A.5 总灰分的测定
- definition: 术语、概念或常数的定义
  示例：卡拉胶是指... / 术语和定义（后接术语正文）
```

---

## 实现方案

### 1. `content_type_rules.json` 改动

- 修改 `metadata` 的 `description`（如上）
- 更新 `metadata` 的 `examples`：
  ```json
  ["GB 1886.169—2016", "2016-08-31 发布", "2017-01-01 实施", "## A.3 硫酸酯的测定", "## A.5 总灰分的测定", "# 附录 A 检验方法"]
  ```
- 更新 `definition` 的 `examples`：
  ```json
  ["卡拉胶是指...", "术语和定义（后接术语正文）", "3.1 本标准中，X 是指..."]
  ```
- 其他类型的 description 和 examples 不变

### 2. `classify_node.py` 改动

新增辅助函数 `_build_type_desc`，替换原有的 `semantic_desc` 构建逻辑：

```python
def _build_type_desc(types: List[Dict]) -> str:
    lines = []
    for t in types:
        lines.append(f"- {t['id']}: {t['description']}")
        if t.get("examples"):
            examples_str = " / ".join(t["examples"])
            lines.append(f"  示例：{examples_str}")
    return "\n".join(lines)
```

`_call_classify_llm` 中将：
```python
semantic_desc = "\n".join(
    f"- {t['id']}: {t['description']}" for t in semantic_types
)
```
替换为：
```python
semantic_desc = _build_type_desc(semantic_types)
```

`_build_type_desc` 只用于替换 `semantic_desc` 的构建，`structure_desc` 的内联推导式保持不变。原因：`structure_types` 当前无 `examples` 字段，对 `structure_desc` 使用 `_build_type_desc` 在功能上等价，但属于无关改动，不在本次变更范围内。

---

## 不在范围内

- **prompt 强制规则**：曾考虑在 prompt 分类规则中增加"structure_type=header 时 semantic_type 强制为 metadata"，但用户选择了 description+examples 方案，保持 prompt 规则层面的最小改动。
- **post-processing 硬校正**：在 `classify_raw_chunk` 中对 header 强制覆写 semantic_type，不在此次范围内。
- **structure_types 的 examples 注入**：本次只修改 semantic_desc 构建逻辑，structure_desc 不变。
- **escalate_node 逻辑**：此修改不影响 escalation 判断。
- **metadata 的 transform strategy**：`plain_embed` 对纯标题行行为合理，不在此次调整范围内。

---

## 测试策略

在 `tests/core/parser_workflow/test_classify_node_real_llm.py` 中补充 `real_llm` 标记的集成测试。测试入口为 `classify_raw_chunk(raw_chunk, store)`，直接构造 `RawChunk` 输入（不需要完整 `WorkflowState`）。`store` 在每个测试函数内内联构造：`store = RulesStore(str(get_rules_dir()))`，参考同文件现有测试惯例，无需 pytest fixture。

`RawChunk` 必填字段：`content`、`section_path`、`char_count`（`char_count` 取 `len(content)`）。

```python
@pytest.mark.real_llm
def test_header_semantic_type_is_metadata_for_method_sections():
    """附录方法节标题 header 的 semantic_type 应一律为 metadata"""
    store = RulesStore(str(get_rules_dir()))
    content = "## A.5 总灰分的测定"
    chunk = RawChunk(content=content, section_path=["A.5"], char_count=len(content))
    result = classify_raw_chunk(chunk, store)
    seg = result.segments[0]
    assert seg.structure_type == "header"
    assert seg.semantic_type == "metadata"

@pytest.mark.real_llm
def test_header_semantic_type_a6():
    store = RulesStore(str(get_rules_dir()))
    content = "## A.6 酸不溶灰分的测定"
    chunk = RawChunk(content=content, section_path=["A.6"], char_count=len(content))
    result = classify_raw_chunk(chunk, store)
    assert result.segments[0].semantic_type == "metadata"

@pytest.mark.real_llm
def test_document_identity_metadata_not_degraded():
    """文档身份信息 semantic_type 不退化"""
    store = RulesStore(str(get_rules_dir()))
    content = "GB 1886.169—2016\n2016-08-31 发布  2017-01-01 实施"
    chunk = RawChunk(content=content, section_path=[], char_count=len(content))
    result = classify_raw_chunk(chunk, store)
    assert any(seg.semantic_type == "metadata" for seg in result.segments)

@pytest.mark.real_llm
def test_definition_body_not_misclassified_as_metadata():
    """含实质术语正文的段落仍分类为 definition，不被误归为 metadata"""
    store = RulesStore(str(get_rules_dir()))
    content = "3 术语和定义\n3.1 卡拉胶\n卡拉胶是指以红藻类植物为原料..."
    chunk = RawChunk(content=content, section_path=["3"], char_count=len(content))
    result = classify_raw_chunk(chunk, store)
    assert any(seg.semantic_type == "definition" for seg in result.segments)
```

覆盖场景：
1. `## A.5 总灰分的测定` → `structure_type=header, semantic_type=metadata`
2. `## A.6 酸不溶灰分的测定` → `semantic_type=metadata`
3. 文档身份信息行 → `semantic_type=metadata`（原有行为不退化）
4. 含术语正文的段落 → `semantic_type=definition`（definition 未被误伤）
