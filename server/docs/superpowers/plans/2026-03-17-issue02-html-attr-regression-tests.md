# ISSUE-02 HTML 属性回归测试 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 classify_node 的 HTML 属性转义修复补充回归测试，覆盖单元层（mock LLM）和真实 LLM 层。

**Architecture:** 在现有两个测试文件中追加测试函数；单元测试直接导入并测试 `_escape_for_json_prompt`，同时 mock `invoke_structured` 验证 prompt 内容和 segment content；真实 LLM 测试构造含 HTML 属性的 chunk 并调用完整 `classify_node`。

**Tech Stack:** Python, pytest, unittest.mock；`uv run pytest` 执行测试。

---

## File Map

| 操作 | 文件 |
|------|------|
| Modify | `tests/core/parser_workflow/test_classify_node_unit.py` |
| Modify | `tests/core/parser_workflow/test_classify_node_real_llm.py` |

---

### Task 1：单元测试 — `_escape_for_json_prompt` 函数

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node_unit.py`

- [ ] **Step 1: 写两个失败测试**

在 `test_classify_node_unit.py` 末尾追加：

```python
from app.core.parser_workflow.nodes.classify_node import _escape_for_json_prompt


def test_escape_for_json_prompt_escapes_double_quotes():
    """_escape_for_json_prompt 应将所有 ASCII 双引号替换为 \\"."""
    raw = '<td rowspan="2">取适量试样</td>'
    escaped = _escape_for_json_prompt(raw)
    assert '\\"' in escaped
    assert 'rowspan=\\"2\\"' in escaped
    assert '"' not in escaped.replace('\\"', '')


def test_escape_for_json_prompt_preserves_other_characters():
    """_escape_for_json_prompt 不应修改无双引号的字符串。"""
    raw = "<td>无属性的单元格</td>"
    assert _escape_for_json_prompt(raw) == raw
```

- [ ] **Step 2: 运行测试，确认 FAIL（函数未导入）**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py::test_escape_for_json_prompt_escapes_double_quotes tests/core/parser_workflow/test_classify_node_unit.py::test_escape_for_json_prompt_preserves_other_characters -v
```

期望：**ImportError 或 FAILED**（`_escape_for_json_prompt` 尚未在测试文件中导入）

- [ ] **Step 3: 确认实现已存在，测试应直接 PASS**

`_escape_for_json_prompt` 已在 `app/core/parser_workflow/nodes/classify_node.py:57-59` 实现。无需修改实现代码。

- [ ] **Step 4: 再次运行，确认 PASS**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py::test_escape_for_json_prompt_escapes_double_quotes tests/core/parser_workflow/test_classify_node_unit.py::test_escape_for_json_prompt_preserves_other_characters -v
```

期望：2 passed

- [ ] **Step 5: Commit**

```bash
git add agent-server/tests/core/parser_workflow/test_classify_node_unit.py
git commit -m "test: add unit tests for _escape_for_json_prompt HTML attribute escaping"
```

---

### Task 2：单元测试 — classify_node prompt 转义 + segment content 保留

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node_unit.py`

- [ ] **Step 1: 写两个失败测试**

在 `test_classify_node_unit.py` 末尾继续追加：

```python
def test_classify_node_html_chunk_prompt_escapes_attribute_quotes(tmp_path):
    """classify_node 传给 LLM 的 prompt 中，HTML 属性双引号应被转义为 \\"."""
    html_content = '<td rowspan="2">取适量试样置于清洁、干燥的白瓷盘中</td>'
    mock_output = ClassifyOutput(segments=[
        SegmentItem(
            content=html_content,
            structure_type="table",
            semantic_type="procedure",
            confidence=0.9,
        ),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch(
        "app.core.parser_workflow.nodes.classify_node.invoke_structured",
        side_effect=capture_invoke,
    ):
        state = _make_state(html_content, tmp_path)
        classify_node(state)

    assert captured_prompts
    prompt = captured_prompts[0]
    assert 'rowspan=\\"2\\"' in prompt, "prompt 中 HTML 属性双引号应已被转义"
    assert 'rowspan="2"' not in prompt, "prompt 中不应含未转义的 HTML 属性双引号"


def test_classify_node_html_chunk_content_unchanged_in_segment(tmp_path):
    """mock LLM 返回含 HTML 属性的 content 时，segment.content 应与原始 chunk content 完全相同。"""
    html_content = '<td rowspan="2">取适量试样置于清洁、干燥的白瓷盘中</td>'
    mock_output = ClassifyOutput(segments=[
        SegmentItem(
            content=html_content,
            structure_type="table",
            semantic_type="procedure",
            confidence=0.9,
        ),
    ])

    with patch(
        "app.core.parser_workflow.nodes.classify_node.invoke_structured",
        return_value=mock_output,
    ):
        state = _make_state(html_content, tmp_path)
        result = classify_node(state)

    seg = result["classified_chunks"][0]["segments"][0]
    assert seg["content"] == html_content, (
        f"segment.content 应与原始 HTML 完全相同，实际得到：{seg['content']!r}"
    )
```

- [ ] **Step 2: 运行测试，确认初始状态**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py::test_classify_node_html_chunk_prompt_escapes_attribute_quotes tests/core/parser_workflow/test_classify_node_unit.py::test_classify_node_html_chunk_content_unchanged_in_segment -v
```

期望：2 passed（实现已就绪）

- [ ] **Step 3: 运行所有单元测试，确认无回归**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py -v
```

期望：全部 PASS

- [ ] **Step 4: Commit**

```bash
git add agent-server/tests/core/parser_workflow/test_classify_node_unit.py
git commit -m "test: add classify_node HTML attr prompt escaping and content preservation tests"
```

---

### Task 3：真实 LLM 测试 — HTML 属性端到端保留验证

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node_real_llm.py`

- [ ] **Step 1: 写失败测试**

在 `test_classify_node_real_llm.py` 末尾追加：

```python
def test_classify_node_html_table_attribute_content_preserved_with_real_llm():
    """
    回归测试（ISSUE-02）：含 rowspan 属性的 HTML 表格 chunk 经 classify 后，
    所有 segment content 拼合仍应包含 rowspan="2"，属性不得被 LLM 篡改。
    """
    rules_dir = get_rules_dir()
    html_content = (
        "<table>\n"
        '<tr><td rowspan="2">取适量试样置于清洁、干燥的白瓷盘中，'
        "在自然光线下观察其色泽和状态</td><td>符合要求</td></tr>\n"
        "<tr><td>无异味</td></tr>\n"
        "</table>"
    )

    state = WorkflowState(
        md_content=html_content,
        doc_metadata={"standard_no": "TEST-HTML-ATTR"},
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[
            RawChunk(
                content=html_content,
                section_path=["感官要求"],
                char_count=len(html_content),
            )
        ],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )

    result = classify_node(state)
    classified_chunks = result["classified_chunks"]

    assert classified_chunks, "classify_node 应返回至少一个 ClassifiedChunk"

    all_content = "".join(
        seg.get("content", "")
        for cc in classified_chunks
        for seg in cc.get("segments", [])
    )

    logger.info("all_content from segments: %r", all_content)

    assert 'rowspan="2"' in all_content, (
        f'HTML 属性 rowspan="2" 在 segment content 中丢失或被篡改。\n'
        f"拼合内容：{all_content!r}"
    )

    valid_structure_types = {"paragraph", "list", "table", "formula", "header", "unknown"}
    valid_semantic_types = {
        "metadata", "scope", "limit", "procedure",
        "material", "calculation", "definition", "amendment", "unknown",
    }
    for cc in classified_chunks:
        for seg in cc.get("segments", []):
            assert seg.get("structure_type") in valid_structure_types, (
                f"非法 structure_type：{seg.get('structure_type')!r}"
            )
            assert seg.get("semantic_type") in valid_semantic_types, (
                f"非法 semantic_type：{seg.get('semantic_type')!r}"
            )
```

- [ ] **Step 2: 运行测试（需要 LLM_API_KEY）**

```bash
cd agent-server
LLM_API_KEY=<your_key> uv run pytest tests/core/parser_workflow/test_classify_node_real_llm.py::test_classify_node_html_table_attribute_content_preserved_with_real_llm -v -s -m real_llm
```

期望：PASS，日志中可见 `all_content` 包含 `rowspan="2"`

- [ ] **Step 3: Commit**

```bash
git add agent-server/tests/core/parser_workflow/test_classify_node_real_llm.py
git commit -m "test(real_llm): add HTML table attribute preservation regression test for ISSUE-02"
```
