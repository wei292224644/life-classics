# classify_node LaTeX 占位符 & raw_content 修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用占位符方案彻底解决 classify_node 将 LaTeX 输出到 JSON 时的转义失败问题，并修正 DocumentChunk.raw_content 与 content 不对应的语义问题。

**Architecture:** 在 classify_node 调用 LLM 前，将所有 LaTeX 公式替换为 `[__MATH_N__]` 占位符，LLM 返回后将占位符还原为原始 LaTeX，写入 seg["content"]。transform_node 将 raw_content 来源从 raw_chunk["content"] 改为 seg["content"]，实现 content 与 raw_content 一一对应。

**Tech Stack:** Python 3.11, pytest, unittest.mock.patch, re（标准库）

---

## 文件结构

| 文件 | 变更类型 | 职责 |
|------|---------|------|
| `server/parser/nodes/classify_node.py` | 修改 | 新增 `_replace_latex_with_placeholders` / `_restore_placeholders`；删除临时 LaTeX prompt 指令；在 `_call_classify_llm` 中调用两函数 |
| `server/parser/nodes/transform_node.py` | 修改 | `apply_strategy` 中 `raw_content` 来源改为 `seg["content"]` |
| `server/tests/core/parser_workflow/test_classify_node_unit.py` | 修改 | 新增占位符函数单元测试 + 集成测试 |
| `server/tests/core/parser_workflow/test_transform_node_unit.py` | 修改 | 新增 raw_content 与 seg["content"] 一致性测试 |

---

## Task 1：为占位符函数编写失败测试

**Files:**
- Modify: `server/tests/core/parser_workflow/test_classify_node_unit.py`

- [ ] **Step 1：在 test_classify_node_unit.py 顶部补充导入**

在现有 import 块末尾追加（`_replace_latex_with_placeholders` 和 `_restore_placeholders` 此时尚未实现，导入会失败）：

```python
from parser.nodes.classify_node import (
    _replace_latex_with_placeholders,
    _restore_placeholders,
)
```

- [ ] **Step 2：在文件末尾追加以下测试**

注意：测试中使用的 `_make_state` 已定义在该文件顶部，`ClassifyOutput`、`SegmentItem` 已在文件顶部导入，无需重复添加。

```python
# ── 占位符预处理 ──────────────────────────────────────────────

def test_replace_inline_latex_single():
    """单个内联公式应被替换为 [__MATH_0__]，mapping 记录原始 LaTeX。"""
    text = "称取 $4\\mathrm{g}$ 试样"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert "[__MATH_0__]" in clean
    assert "$" not in clean
    assert mapping["[__MATH_0__]"] == "$4\\mathrm{g}$"


def test_replace_inline_latex_multiple():
    """多个内联公式按出现顺序分配序号。"""
    text = "加 $200~\\mathrm{mL}$ 水，加热至 $80^{\\circ}C$"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert "[__MATH_0__]" in clean
    assert "[__MATH_1__]" in clean
    assert "$" not in clean
    assert len(mapping) == 2


def test_replace_block_latex():
    """block 公式 $$...$$ 应被替换，且优先于 inline 匹配。"""
    text = "按下式计算：\n$$\nw = m_1 / m\n$$\n式中 w 为质量分数。"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert "[__MATH_0__]" in clean
    assert "$$" not in clean
    assert mapping["[__MATH_0__]"].startswith("$$")


def test_replace_mixed_block_and_inline():
    """block 先替换，inline 后替换，序号连续。"""
    text = "公式：\n$$\nX = a + b\n$$\n其中 $a$ 为常数。"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert len(mapping) == 2
    # block 应为 MATH_0
    assert mapping["[__MATH_0__]"].startswith("$$")
    # inline 应为 MATH_1
    assert mapping["[__MATH_1__]"] == "$a$"


def test_replace_no_latex_unchanged():
    """不含 LaTeX 的文本应原样返回，mapping 为空。"""
    text = "本标准适用于食品添加剂卡拉胶。"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert clean == text
    assert mapping == {}


# ── 占位符后处理 ──────────────────────────────────────────────

def test_restore_placeholders_normal():
    """正常情况下占位符应被精确还原为原始 LaTeX。"""
    mapping = {"[__MATH_0__]": "$4\\mathrm{g}$"}
    text = "称取 [__MATH_0__] 试样"
    result = _restore_placeholders(text, mapping)
    assert result == "称取 $4\\mathrm{g}$ 试样"


def test_restore_placeholders_tolerates_extra_spaces():
    """占位符前后多余空格应被容忍，还原后得到完整原始 LaTeX。"""
    mapping = {"[__MATH_0__]": "$4\\mathrm{g}$"}
    text = "称取 [ __MATH_0__ ] 试样"
    result = _restore_placeholders(text, mapping)
    assert result == "称取 $4\\mathrm{g}$ 试样"


def test_restore_placeholders_missing_not_raises():
    """若 LLM 删除了占位符，不抛异常，返回原文本。"""
    mapping = {"[__MATH_0__]": "$4\\mathrm{g}$"}
    text = "称取试样"  # 占位符已被 LLM 丢弃
    result = _restore_placeholders(text, mapping)
    assert result == "称取试样"  # 原样返回，不报错


def test_restore_placeholders_multiple():
    """多个占位符全部还原。"""
    mapping = {
        "[__MATH_0__]": "$200~\\mathrm{mL}$",
        "[__MATH_1__]": "$80^{\\circ}C$",
    }
    text = "加 [__MATH_0__] 水，加热至 [__MATH_1__]"
    result = _restore_placeholders(text, mapping)
    assert result == "加 $200~\\mathrm{mL}$ 水，加热至 $80^{\\circ}C$"
```

- [ ] **Step 3：运行测试，确认因函数未实现而失败**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py::test_replace_inline_latex_single -v
```

期望：`ImportError` 或 `FAILED`（函数不存在）

---

## Task 2：实现 `_replace_latex_with_placeholders` 和 `_restore_placeholders`

**Files:**
- Modify: `server/parser/nodes/classify_node.py`

- [ ] **Step 1：在 classify_node.py 的 import 区末尾确认 `re` 已导入**

检查文件顶部，若无 `import re` 则添加：

```python
import re
```

- [ ] **Step 2：在 `_escape_for_json_prompt` 函数之后插入两个新函数**

```python
def _replace_latex_with_placeholders(text: str) -> tuple[str, dict[str, str]]:
    """
    将文本中的 LaTeX 公式替换为占位符 [__MATH_N__]。
    先匹配 block 公式（$$...$$），再匹配 inline 公式（$...$），顺序不可颠倒。
    返回 (clean_text, mapping)，mapping 为 {占位符: 原始LaTeX}。
    """
    mapping: dict[str, str] = {}
    counter = 0

    def make_placeholder() -> str:
        nonlocal counter
        ph = f"[__MATH_{counter}__]"
        counter += 1
        return ph

    # 1. block 公式：$$...$$（跨行，DOTALL）
    def replace_block(m: re.Match) -> str:
        ph = make_placeholder()
        mapping[ph] = m.group(0)
        return ph

    text = re.sub(r'\$\$.*?\$\$', replace_block, text, flags=re.DOTALL)

    # 2. inline 公式：$...$（单行）
    def replace_inline(m: re.Match) -> str:
        ph = make_placeholder()
        mapping[ph] = m.group(0)
        return ph

    text = re.sub(r'\$[^$\n]+?\$', replace_inline, text)

    return text, mapping


def _restore_placeholders(text: str, mapping: dict[str, str]) -> str:
    """
    将文本中的占位符还原为原始 LaTeX。
    容错：处理占位符前后多余空格（如 [ __MATH_0__ ]）。
    若某占位符未找到（LLM 删除），忽略该条目，不抛异常。
    """
    for placeholder, original in mapping.items():
        # 精确匹配
        if placeholder in text:
            text = text.replace(placeholder, original)
            continue
        # 容错：去除方括号内部空格后再匹配
        inner = placeholder[1:-1].strip()  # 去掉 [ 和 ]，保留 __MATH_N__
        lenient = r'\[\s*' + re.escape(inner) + r'\s*\]'
        text = re.sub(lenient, original, text)
    return text
```

- [ ] **Step 3：运行占位符单元测试，确认全部通过**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py -k "replace or restore" -v
```

期望：所有新增测试 PASS

- [ ] **Step 4：提交**

```bash
git add server/parser/nodes/classify_node.py server/tests/core/parser_workflow/test_classify_node_unit.py
git commit -m "feat(classify): add latex placeholder pre/post-processing functions"
```

---

## Task 3：将占位符函数接入 `_call_classify_llm`，清理临时 prompt 指令

**Files:**
- Modify: `server/parser/nodes/classify_node.py`
- Modify: `server/tests/core/parser_workflow/test_classify_node_unit.py`

- [ ] **Step 1：在 test_classify_node_unit.py 末尾追加集成测试**

注意：`_make_state`、`ClassifyOutput`、`SegmentItem` 已在文件中定义/导入，无需重复。

```python
def test_classify_llm_sends_placeholder_not_latex(tmp_path):
    """_call_classify_llm 发给 LLM 的 prompt 中不应含原始 $...$，应含 [__MATH_N__]。"""
    content = "称取 $4\\mathrm{g}$ 试样，加 $200~\\mathrm{mL}$ 水。"
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="称取 [__MATH_0__] 试样，加 [__MATH_1__] 水。",
                    structure_type="list", semantic_type="procedure", confidence=0.9),
    ])
    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch("parser.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        state = _make_state(content, tmp_path)
        classify_node(state)

    prompt = captured_prompts[0]
    assert "[__MATH_0__]" in prompt, "prompt 应含占位符"
    assert "$4\\mathrm{g}$" not in prompt, "prompt 不应含原始 LaTeX"


def test_classify_node_restores_latex_in_seg_content(tmp_path):
    """classify_node 产出的 seg["content"] 应含还原后的原始 LaTeX，不含占位符。"""
    content = "称取 $4\\mathrm{g}$ 试样"
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="称取 [__MATH_0__] 试样",
                    structure_type="list", semantic_type="material", confidence=0.9),
    ])

    with patch("parser.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state(content, tmp_path)
        result = classify_node(state)

    seg = result["classified_chunks"][0]["segments"][0]
    assert "$4\\mathrm{g}$" in seg["content"], "seg.content 应含还原后的 LaTeX"
    assert "[__MATH_0__]" not in seg["content"], "seg.content 不应含占位符"
```

- [ ] **Step 2：运行集成测试，确认当前失败**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py::test_classify_llm_sends_placeholder_not_latex -v
```

期望：FAILED（尚未接入占位符）

- [ ] **Step 3：修改 `_call_classify_llm` 接入占位符流程**

`_call_classify_llm` 当前签名（`server/parser/nodes/classify_node.py` 约第 28 行）：

```python
def _call_classify_llm(
    chunk_content: str,
    structure_types: List[Dict],
    semantic_types: List[Dict],
) -> List[SegmentItem]:
```

修改后的完整函数体骨架（保留现有 prompt 文本，只做以下三处改动）：

```python
def _call_classify_llm(
    chunk_content: str,
    structure_types: List[Dict],
    semantic_types: List[Dict],
) -> List[SegmentItem]:
    # [改动 1] 函数开头：预处理 LaTeX → 占位符
    clean_content, latex_mapping = _replace_latex_with_placeholders(chunk_content)

    structure_desc = "\n".join(...)   # 不变
    semantic_desc = _build_type_desc(...)  # 不变

    prompt = f"""...(保留原有 prompt 全文)...

文本内容：
{_escape_for_json_prompt(clean_content)}  # [改动 2] chunk_content → clean_content
"""
    # [改动 3] 同时删除 prompt 末尾的【输出 content 字段的 LaTeX 处理规则】整段
    # （该段从"【输出 content 字段的 LaTeX 处理规则】"开始到 f""" 结束前，约 12 行）

    result = invoke_structured(
        node_name="classify_node",
        prompt=prompt,
        response_model=ClassifyOutput,
        extra_body={"enable_thinking": False, "reasoning_split": True},
        max_tokens=15000,
    )

    # [改动 4] 后处理：还原占位符到每个 segment 的 content
    restored_segments: List[SegmentItem] = []
    for item in result.segments:
        restored_content = _restore_placeholders(item.content, latex_mapping)
        restored_segments.append(SegmentItem(
            content=restored_content,
            structure_type=item.structure_type,
            semantic_type=item.semantic_type,
            confidence=item.confidence,
        ))
    return restored_segments
```

- [ ] **Step 4：运行所有 classify_node 单元测试**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py -v
```

期望：全部 PASS（包括旧测试和新增测试）

- [ ] **Step 5：提交**

```bash
git add server/parser/nodes/classify_node.py server/tests/core/parser_workflow/test_classify_node_unit.py
git commit -m "feat(classify): wire latex placeholder into _call_classify_llm, remove temp prompt instruction"
```

---

## Task 4：修正 transform_node 的 `raw_content` 来源

**Files:**
- Modify: `server/parser/nodes/transform_node.py`
- Modify: `server/tests/core/parser_workflow/test_transform_node_unit.py`

- [ ] **Step 1：在 test_transform_node_unit.py 末尾追加失败测试**

注意：`apply_strategy` 内部所有 strategy（包括 `plain_embed`）均通过 `_call_llm_transform` 处理内容（当 `len(content) >= 50` 时），patch 路径 `parser.nodes.transform_node._call_llm_transform` 对本测试有效。测试中两个 segment 的 content 长度均超过 50 字符，确保走 LLM 分支。

```python
def test_transform_node_raw_content_matches_seg_content():
    """DocumentChunk.raw_content 应等于 seg["content"]，而非整个 raw_chunk["content"]。

    当 classify_node 将一个 chunk 切分为多个 segment 时，每个 DocumentChunk 的
    raw_content 应只对应其自身 segment 的内容，不含相邻 segment 的文本。
    """
    seg1 = TypedSegment(
        content="A.3.2 试剂与材料：氯化钾溶液配制方法如下",   # 超过 50 字符确保走 LLM 分支
        structure_type="list",
        semantic_type="material",
        transform_params={"strategy": "plain_embed", "prompt_template": "请转化：\n"},
        confidence=0.9,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    seg2 = TypedSegment(
        content="A.3.3 分析步骤：称取试样约2g，加入氯化钾溶液200mL",  # 超过 50 字符
        structure_type="list",
        semantic_type="procedure",
        transform_params={"strategy": "plain_embed", "prompt_template": "请转化：\n"},
        confidence=0.9,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    raw_chunk = RawChunk(
        content="A.3.2 试剂与材料：氯化钾溶液配制方法如下\nA.3.3 分析步骤：称取试样约2g，加入氯化钾溶液200mL",
        section_path=["A.3"],
        char_count=100,
    )
    classified = ClassifiedChunk(raw_chunk=raw_chunk, segments=[seg1, seg2], has_unknown=False)
    state = WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "TEST001"},
        config={},
        rules_dir="",
        raw_chunks=[raw_chunk],
        classified_chunks=[classified],
        final_chunks=[],
        errors=[],
    )

    with patch(
        "parser.nodes.transform_node._call_llm_transform",
        side_effect=lambda content, params, ref="": f"转化后：{content}",
    ):
        result = transform_node(state)

    chunks = result["final_chunks"]
    assert len(chunks) == 2
    assert chunks[0]["raw_content"] == seg1["content"], (
        f"raw_content 应为 seg1 内容，实际：{chunks[0]['raw_content']!r}"
    )
    assert chunks[1]["raw_content"] == seg2["content"], (
        f"raw_content 应为 seg2 内容，实际：{chunks[1]['raw_content']!r}"
    )
```

- [ ] **Step 2：运行测试，确认失败**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_transform_node_unit.py::test_transform_node_raw_content_matches_seg_content -v
```

期望：FAILED（`raw_content` 当前仍是整个 `raw_chunk["content"]`）

- [ ] **Step 3：修改 transform_node.py 的 `apply_strategy` 函数**

找到 `server/parser/nodes/transform_node.py` 约第 68 行：

```python
# 修改前
raw_content = raw_chunk["content"]

# 修改后
raw_content = seg["content"]
```

- [ ] **Step 4：运行全部 transform_node 测试**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_transform_node_unit.py tests/core/parser_workflow/test_transform_node.py -v
```

期望：全部 PASS

- [ ] **Step 5：提交**

```bash
git add server/parser/nodes/transform_node.py server/tests/core/parser_workflow/test_transform_node_unit.py
git commit -m "fix(transform): raw_content now sourced from seg[content] for precise segment correspondence"
```

---

## Task 5：全套回归测试

- [ ] **Step 1：运行 parser_workflow 全部单元测试（排除需要真实 LLM 的测试）**

```bash
cd server
uv run pytest tests/core/parser_workflow/ -v \
  --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_parse_node_real.py \
  --ignore=tests/core/parser_workflow/test_slice_node_real.py
```

期望：全部 PASS，无回归

- [ ] **Step 2：若有失败，修复后重新运行至全部通过**

- [ ] **Step 3：最终提交（如有额外修复）**

```bash
git add server/parser/nodes/classify_node.py server/parser/nodes/transform_node.py \
        server/tests/core/parser_workflow/test_classify_node_unit.py \
        server/tests/core/parser_workflow/test_transform_node_unit.py
git commit -m "fix(parser): resolve regression from latex placeholder & raw_content changes"
```
