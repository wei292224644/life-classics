# enrich_node 表格引用正则扩展 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展 `_TABLE_REF_PATTERN` 覆盖 GB 标准所有常见表格引用前缀，并预留后验过滤扩展口。

**Architecture:** TDD 方式：先写失败测试，再修改实现让测试通过。仅改两个文件：`enrich_node.py`（正则 + 新函数）和 `test_enrich_node.py`（7 个新测试）。

**Tech Stack:** Python 3.12, `re` 标准库, pytest, uv

---

## 文件变更清单

| 操作 | 文件 | 变更内容 |
|------|------|---------|
| 修改 | `agent-server/app/core/parser_workflow/nodes/enrich_node.py` | 扩展 `_TABLE_REF_PATTERN`，新增 `_filter_table_refs`，更新 `extract_table_refs` |
| 修改 | `agent-server/tests/core/parser_workflow/test_enrich_node.py` | 新增 6 个单元测试 + 1 个集成测试 |

---

### Task 1：写 6 个失败单元测试（新前缀覆盖）

**Files:**
- Modify: `agent-server/tests/core/parser_workflow/test_enrich_node.py`

在文件末尾 `# ── extract_table_refs ───` 区块之后追加以下 6 个测试函数：

- [ ] **Step 1: 追加 6 个新单元测试到测试文件**

在 `test_enrich_node.py` 末尾（`# ── extract_amendment_refs` 区块之前）追加：

```python
def test_extract_table_refs_yingfuhe():
    """'应符合表1的规定' 应提取 '表1'"""
    refs = extract_table_refs("感官要求应符合表1的规定。")
    assert "表1" in refs


def test_extract_table_refs_fuhe():
    """'符合表2的规定' 应提取 '表2'"""
    refs = extract_table_refs("理化指标符合表2的规定。")
    assert "表2" in refs


def test_extract_table_refs_an():
    """'按表3进行检验' 应提取 '表3'"""
    refs = extract_table_refs("按表3进行检验。")
    assert "表3" in refs


def test_extract_table_refs_anzhao():
    """'按照表A.1操作' 应提取 '表A.1'"""
    refs = extract_table_refs("按照表A.1操作。")
    assert "表A.1" in refs


def test_extract_table_refs_bu_chao():
    """'不得超过表4的规定' 应提取 '表4'"""
    refs = extract_table_refs("污染物限量不得超过表4的规定。")
    assert "表4" in refs


def test_extract_table_refs_bu_di():
    """'不应低于表B.1的要求' 应提取 '表B.1'"""
    refs = extract_table_refs("检出限不应低于表B.1的要求。")
    assert "表B.1" in refs
```

- [ ] **Step 2: 运行测试，确认全部 FAIL**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_yingfuhe tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_fuhe tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_an tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_anzhao tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_bu_chao tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_bu_di -v
```

期望：6 个测试全部 **FAIL**（AssertionError，refs 为空列表）。

---

### Task 2：写 1 个失败集成测试（GB 风格多表内联）

**Files:**
- Modify: `agent-server/tests/core/parser_workflow/test_enrich_node.py`

- [ ] **Step 1: 追加集成测试**

在 `test_enrich_node.py` 末尾追加：

```python
def test_enrich_node_gb_style_multiple_refs():
    """GB 风格段落含多种新前缀时，三个表格均应被内联到 ref_context"""
    from app.core.parser_workflow.models import ClassifiedChunk, RawChunk, TypedSegment

    ref_text = "感官要求应符合表1的规定。理化指标符合表2的规定。微生物指标按照表3执行。"

    ref_raw: RawChunk = {
        "content": ref_text,
        "section_path": ["2"],
        "char_count": len(ref_text),
    }
    table1_raw: RawChunk = {
        "content": "表1 感官要求\n\n| 色泽 | 正常 |\n|---|---|\n| 白色 | 均匀 |",
        "section_path": ["3"],
        "char_count": 40,
    }
    table2_raw: RawChunk = {
        "content": "表2 理化指标\n\n| 灰分 | ≤1% |\n|---|---|\n| 水分 | ≤12% |",
        "section_path": ["4"],
        "char_count": 40,
    }
    table3_raw: RawChunk = {
        "content": "表3 微生物指标\n\n| 菌落总数 | ≤100 |\n|---|---|\n| 大肠菌群 | 阴性 |",
        "section_path": ["5"],
        "char_count": 45,
    }

    def _make_seg(content, structure_type, semantic_type):
        return TypedSegment(
            content=content,
            structure_type=structure_type,
            semantic_type=semantic_type,
            transform_params={"strategy": "semantic_standardization", "prompt_template": ""},
            confidence=0.9,
            escalated=False,
            cross_refs=[],
            ref_context="",
            failed_table_refs=[],
        )

    ref_cc = ClassifiedChunk(
        raw_chunk=ref_raw,
        segments=[_make_seg(ref_text, "paragraph", "requirement")],
        has_unknown=False,
    )
    table1_cc = ClassifiedChunk(
        raw_chunk=table1_raw,
        segments=[_make_seg("| 色泽 | 正常 |", "table", "specification_table")],
        has_unknown=False,
    )
    table2_cc = ClassifiedChunk(
        raw_chunk=table2_raw,
        segments=[_make_seg("| 灰分 | ≤1% |", "table", "specification_table")],
        has_unknown=False,
    )
    table3_cc = ClassifiedChunk(
        raw_chunk=table3_raw,
        segments=[_make_seg("| 菌落总数 | ≤100 |", "table", "specification_table")],
        has_unknown=False,
    )

    state = {
        "md_content": "",
        "doc_metadata": {"standard_no": "GB1886.47"},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": [ref_raw, table1_raw, table2_raw, table3_raw],
        "classified_chunks": [ref_cc, table1_cc, table2_cc, table3_cc],
        "final_chunks": [],
        "errors": [],
    }

    result = enrich_node(state)
    seg = result["classified_chunks"][0]["segments"][0]
    ref_context = seg["ref_context"]
    cross_refs = seg["cross_refs"]

    assert "色泽" in ref_context, "表1 未被内联"
    assert "灰分" in ref_context, "表2 未被内联"
    assert "菌落总数" in ref_context, "表3 未被内联"
    assert set(["表1", "表2", "表3"]).issubset(set(cross_refs)), f"cross_refs 缺失标签: {cross_refs}"
    assert seg["failed_table_refs"] == [], f"存在未解析引用: {seg['failed_table_refs']}"
```

- [ ] **Step 2: 运行集成测试，确认 FAIL**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_enrich_node.py::test_enrich_node_gb_style_multiple_refs -v
```

期望：**FAIL**（三个断言全部失败，ref_context 为空，cross_refs 为空列表）。

---

### Task 3：修改实现（正则扩展 + 过滤层）

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/enrich_node.py:21-64`

- [ ] **Step 1: 替换 `_TABLE_REF_PATTERN`**

将文件中第 21-24 行：

```python
_TABLE_REF_PATTERN = re.compile(
    r'(?:见|参见|参照)[^\n，。；]*?表\s*([\dA-Z]+(?:\.\d+)*)',
    re.UNICODE,
)
```

替换为：

```python
_TABLE_REF_PATTERN = re.compile(
    r'(?:见|参见|参照|应符合|符合|按照?|不[应得]超过|不[应得]低于)'
    r'[^\n，。；]*?表\s*([\dA-Z]+(?:\.\d+)*)',
    re.UNICODE,
)
```

- [ ] **Step 2: 在 `_normalize_label` 函数定义之前插入 `_filter_table_refs`**

在第 41 行 `def _normalize_label` 之前插入：

```python
def _filter_table_refs(refs: List[str]) -> List[str]:
    """
    后验过滤：对召回的表格引用标签做二次验证。
    当前直接透传；后期如需排除误报可在此添加规则。

    TODO: 如召回率提高后误报增多，在此添加过滤逻辑，
          例如排除标题行自身（如"表1 感官要求"行首）、
          排除特定 section_path 下的引用等。
          主要误报源：含"表"字的非引用词，如"征求意见表"。
    """
    return refs
```

- [ ] **Step 3: 更新 `extract_table_refs` 接入过滤层**

将第 59-64 行：

```python
def extract_table_refs(text: str) -> List[str]:
    """
    从文本中提取表格引用标识符列表（已规范化），如 ["表1", "表A.1"]。
    匹配 "见表X"、"参见表X"、"参照表X" 及含前缀的形式。
    """
    return ["表" + _normalize_label(m.group(1)) for m in _TABLE_REF_PATTERN.finditer(text)]
```

替换为：

```python
def extract_table_refs(text: str) -> List[str]:
    """
    从文本中提取表格引用标识符列表（已规范化），如 ["表1", "表A.1"]。
    匹配 "见表X"、"参见表X"、"参照表X"、"应符合表X"、"符合表X"、
    "按表X"、"按照表X"、"不[应得]超过表X"、"不[应得]低于表X" 等形式。
    结果经 _filter_table_refs 后验过滤后返回。
    """
    raw = ["表" + _normalize_label(m.group(1)) for m in _TABLE_REF_PATTERN.finditer(text)]
    return _filter_table_refs(raw)
```

---

### Task 4：验证所有新测试通过

- [ ] **Step 1: 运行全部 7 个新测试**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_yingfuhe tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_fuhe tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_an tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_anzhao tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_bu_chao tests/core/parser_workflow/test_enrich_node.py::test_extract_table_refs_bu_di tests/core/parser_workflow/test_enrich_node.py::test_enrich_node_gb_style_multiple_refs -v
```

期望：7 个测试全部 **PASS**。

- [ ] **Step 2: 运行整个 test_enrich_node.py，确认无回归**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_enrich_node.py -v
```

期望：全部测试 **PASS**，无新增失败。

---

### Task 5：提交

- [ ] **Step 1: 提交**

```bash
git add agent-server/app/core/parser_workflow/nodes/enrich_node.py \
        agent-server/tests/core/parser_workflow/test_enrich_node.py
git commit -m "fix(enrich_node): expand _TABLE_REF_PATTERN to cover GB standard table ref prefixes

- Add 应符合/符合/按照?/不[应得]超过/不[应得]低于 to _TABLE_REF_PATTERN
- Add _filter_table_refs passthrough with TODO for future false-positive filtering
- Wire _filter_table_refs into extract_table_refs
- Add 6 unit tests + 1 integration test for new prefixes"
```
