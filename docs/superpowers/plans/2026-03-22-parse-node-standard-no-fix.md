# parse_node standard_no 提取优先级修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `parse_node` 的 `standard_no` 提取逻辑，改为 title 优先、content 兜底，去除无意义的 UUID fallback。

**Architecture:** 仅修改 `parse_node.py` 中的一段提取逻辑（约 10 行），同步替换已全部注释的测试文件为有效测试用例。改动极小，无跨模块影响。

**Tech Stack:** Python 3.x, pytest, uv（所有命令在 `server/` 目录下通过 `uv run` 执行）

---

## 文件清单

| 文件 | 操作 |
|------|------|
| `server/parser/nodes/parse_node.py` | 修改（第 44-54 行提取逻辑） |
| `server/tests/core/parser_workflow/test_parse_node_real.py` | 替换（清除注释代码，写入新测试） |

---

### Task 1: 替换测试文件，写入失败测试

**Files:**
- Modify: `server/tests/core/parser_workflow/test_parse_node_real.py`

- [ ] **Step 1: 用新测试完整替换 test_parse_node_real.py**

用以下内容完整覆盖该文件（原内容均为注释，全部丢弃）：

```python
"""parse_node standard_no 提取优先级测试。

所有测试使用内联 fixture，不依赖 test_utils。
"""
from parser.models import WorkflowState
from parser.nodes.parse_node import parse_node


def _make_state(md_content: str, doc_metadata: dict) -> WorkflowState:
    return WorkflowState(
        md_content=md_content,
        doc_metadata=doc_metadata,
        config={},
        rules_dir="",
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


def test_standard_no_from_title_wins_over_content():
    """title 含 GB 编号时，应取 title 的，即使 content 里有别的 GB 编号。"""
    state = _make_state(
        md_content="正文中引用了 GB 1234-2020 作为参考标准。",
        doc_metadata={"title": "GB 29701-2013 鸡可食性组织中地克珠利残留量的测定"},
    )
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB 29701-2013"


def test_standard_no_falls_back_to_content_when_title_has_none():
    """title 无 GB 编号时，从 md_content 提取。"""
    state = _make_state(
        md_content="本标准为 GB 29701-2013，规定了检测方法。",
        doc_metadata={"title": "食品安全国家标准 鸡可食性组织中地克珠利残留量的测定"},
    )
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB 29701-2013"


def test_standard_no_from_content_when_title_filled_by_parse_node():
    """title 由 parse_node 从 # 标题行填充（不含 GB 编号），应降级到 content 提取。"""
    md = "# 食品安全国家标准 鸡可食性组织中地克珠利残留量的测定\n\n本标准编号 GB 29701-2013。"
    state = _make_state(md_content=md, doc_metadata={})
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB 29701-2013"


def test_standard_no_warning_when_neither_title_nor_content_match():
    """title 和 content 均无 GB 编号时，standard_no 不写入，errors 含 WARNING。"""
    state = _make_state(
        md_content="本文档无标准编号。",
        doc_metadata={"title": "食品安全国家标准"},
    )
    result = parse_node(state)
    assert "standard_no" not in result["doc_metadata"]
    assert any("WARNING: doc_metadata missing 'standard_no'" in e for e in result["errors"])


def test_standard_no_not_overwritten_when_already_set():
    """meta 已有非空 standard_no 时，不覆盖。"""
    state = _make_state(
        md_content="正文引用了 GB 1234-2020。",
        doc_metadata={"title": "GB 9999-2000 某标准", "standard_no": "GB 29701-2013"},
    )
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB 29701-2013"


def test_standard_no_extracted_when_empty_string():
    """standard_no 为空字符串时，视为无值，继续从 title 提取。"""
    state = _make_state(
        md_content="正文。",
        doc_metadata={"title": "GB 29701-2013 某标准", "standard_no": ""},
    )
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB 29701-2013"


def test_standard_no_takes_first_when_title_has_multiple():
    """title 含多个 GB 编号时，取第一个。"""
    state = _make_state(
        md_content="正文。",
        doc_metadata={"title": "GB 29701-2013 关于 GB 1234-2020 的引用"},
    )
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB 29701-2013"
```

- [ ] **Step 2: 运行测试，确认全部失败（因为实现还未改）**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_parse_node_real.py -v
```

预期：部分或全部 FAIL（`test_standard_no_from_title_wins_over_content` 等必须失败，`test_standard_no_not_overwritten_when_already_set` 可能已通过）。

---

### Task 2: 修改 parse_node 实现

**Files:**
- Modify: `server/parser/nodes/parse_node.py:44-54`

- [ ] **Step 1: 替换 standard_no 提取逻辑**

将 `parse_node.py` 中第 44-54 行的现有代码：

```python
        # standard_no 缺失时，尝试从 Markdown 内容中提取
        if not meta.get("standard_no"):
            pattern = r"GB[\s_]?\d+(?:[.\d]*)?(?:\.\d+)?-\d{4}"
            match = re.search(pattern, state["md_content"])
            if match:
                meta["standard_no"] = match.group(0)
            elif meta.get("doc_id"):
                # fallback：使用 doc_id（通常为文件名去扩展名）
                meta["standard_no"] = meta["doc_id"]
            else:
                errors.append("WARNING: doc_metadata missing 'standard_no'")
```

替换为：

```python
        # standard_no 缺失时，先从 title 提取，再从 md_content 全文兜底
        if not meta.get("standard_no"):
            pattern = r"GB[\s_]?\d+(?:[.\d]*)?(?:\.\d+)?-\d{4}"
            match = re.search(pattern, meta.get("title", "")) or re.search(
                pattern, state["md_content"]
            )
            if match:
                meta["standard_no"] = match.group(0)
            else:
                errors.append("WARNING: doc_metadata missing 'standard_no'")
```

- [ ] **Step 2: 运行新测试，确认全部通过**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_parse_node_real.py -v
```

预期：7 个测试全部 PASS。

- [ ] **Step 3: 运行全套 parser_workflow 测试，确认无回归**

```bash
cd server && uv run pytest tests/core/parser_workflow/ -v
```

预期：全部 PASS（或与修改前相同的 skip/xfail 数量，无新增失败）。

- [ ] **Step 4: Commit**

```bash
git add server/parser/nodes/parse_node.py server/tests/core/parser_workflow/test_parse_node_real.py
git commit -m "fix(parser): extract standard_no from title first, remove UUID fallback"
```
