# P1-01 公式分类不稳定修复实现方案

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 classify_node prompt 中加入公式识别确定性规则，使含 `$$...$$` LaTeX 公式的 segment 无论所在 chunk 大小，都被正确分类为 `structure_type=formula`。

**Architecture:** 在 `_call_classify_llm()` 的 prompt 字符串中追加第 4 条分类规则。规则为确定性约束，不依赖 LLM 语义推断。测试通过 `invoke_structured` mock 捕获 prompt 内容验证规则存在。

**Tech Stack:** Python, pytest, `unittest.mock.patch`

---

## 受影响文件

| 操作 | 文件 |
|---|---|
| 修改 | `app/core/parser_workflow/nodes/classify_node.py`（prompt 增加规则） |
| 修改 | `tests/core/parser_workflow/test_classify_node_unit.py`（新增 prompt 内容测试） |

---

### Task 1：新增 prompt 公式规则的测试

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node_unit.py`

- [ ] **Step 1：在 `test_classify_node_unit.py` 末尾追加失败测试**

```python
def test_classify_node_prompt_contains_formula_rule(tmp_path):
    """prompt 中应包含公式识别确定性规则，要求含 $$ 的 segment 必须分类为 formula"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="x", structure_type="formula", semantic_type="calculation", confidence=0.9),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        state = _make_state("x", tmp_path)
        classify_node(state)

    prompt = captured_prompts[0]
    assert "$$" in prompt, "prompt 未包含 $$ 公式规则"
    assert "formula" in prompt.split("分类规则：")[1] if "分类规则：" in prompt else "formula" in prompt
    assert "plain_text" not in prompt.split("分类规则：")[1].lower() if "分类规则：" in prompt else True
```

> 注意：上面的断言比较宽松，目的是先有失败测试；Step 5 会收紧。

- [ ] **Step 2：运行测试，确认失败**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node_unit.py::test_classify_node_prompt_contains_formula_rule -v
```

期望：FAILED（`assert "$$" in prompt` 失败，因为当前 prompt 不含 `$$`）

---

### Task 2：在 prompt 中加入公式识别规则

**Files:**
- Modify: `app/core/parser_workflow/nodes/classify_node.py:31-46`

- [ ] **Step 3：修改 `_call_classify_llm()` 的 prompt，将分类规则第 3 条后追加第 4 条**

在 `classify_node.py` 第 39-43 行，将：

```python
分类规则：
1. 保守切分：只在相邻内容属于明显不同语义单元时才切分；同一逻辑章节保持整体。
2. 对每个片段独立推断两个维度，互不干扰：先判断呈现形式（structure_type），再判断用途（semantic_type）。
3. confidence 反映你对两个判断综合的把握程度（0-1）。
```

改为：

```python
分类规则：
1. 保守切分：只在相邻内容属于明显不同语义单元时才切分；同一逻辑章节保持整体。
2. 对每个片段独立推断两个维度，互不干扰：先判断呈现形式（structure_type），再判断用途（semantic_type）。
3. confidence 反映你对两个判断综合的把握程度（0-1）。
4. 公式识别（强制规则）：文本中出现 $$...$$ 块级公式时，该部分及其紧邻的变量说明（"式中：m1——..."格式）必须作为独立 segment，structure_type=formula，semantic_type=calculation。不得因上下文中存在大量列表或段落而将含公式的内容归为 plain_text。
```

- [ ] **Step 4：运行 Task 1 的测试，确认通过**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node_unit.py::test_classify_node_prompt_contains_formula_rule -v
```

期望：PASSED

- [ ] **Step 5：收紧测试断言，确保规则内容完整**

将 `test_classify_node_prompt_contains_formula_rule` 中的断言替换为更精确的版本：

```python
    prompt = captured_prompts[0]
    assert "$$" in prompt, "prompt 未包含 $$ 公式规则"
    assert "structure_type=formula" in prompt, "prompt 未要求含 $$ 的 segment 用 structure_type=formula"
    assert "semantic_type=calculation" in prompt, "prompt 未要求含 $$ 的 segment 用 semantic_type=calculation"
    assert "plain_text" in prompt, "prompt 中应提到不得将公式归为 plain_text"
```

- [ ] **Step 6：再次运行全部 classify_node 单元测试，确认全部通过**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node_unit.py tests/core/parser_workflow/test_classify_node.py -v
```

期望：所有测试 PASSED

- [ ] **Step 7：运行更大范围的测试，确认没有回归**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/ -v --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py --ignore=tests/core/parser_workflow/test_parse_node_real.py --ignore=tests/core/parser_workflow/test_slice_node_real.py
```

期望：所有非 real_llm 测试 PASSED

- [ ] **Step 8：提交**

```bash
git add agent-server/app/core/parser_workflow/nodes/classify_node.py \
        agent-server/tests/core/parser_workflow/test_classify_node_unit.py
git commit -m "fix(P1-01): add deterministic formula rule to classify_node prompt

Segments containing \$\$...\$\$ LaTeX block formulas must be classified as
structure_type=formula regardless of surrounding context. Prevents LLM from
misclassifying formula segments as plain_text when they appear alongside
large volumes of list/paragraph content in a single chunk."
```
