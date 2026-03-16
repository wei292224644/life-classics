# Cross-Reference Enrich Node Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 parser_workflow 的 escalate_node 和 transform_node 之间插入 enrich_node，自动识别"见表X"等交叉引用，将被引用表格内容注入 TypedSegment，使 transform_node 生成语义完整的向量化文本。

**Architecture:** 新增 `enrich_node.py`，构建双重匹配（正则标签索引 + section_path 模糊匹配）来解析表格引用。修改 `TypedSegment` 数据模型增加 `cross_refs` 和 `ref_context` 字段。更新 graph.py 将 enrich_node 插入两条收敛路径（有/无 escalate）中，再流向 transform_node。

**Tech Stack:** Python 3.10+, LangGraph, re（标准库）

**Spec:** `agent-server/docs/superpowers/specs/2026-03-16-cross-reference-enrich-design.md`

---

## File Map

| 文件 | 操作 | 职责 |
|---|---|---|
| `app/core/parser_workflow/models.py` | 修改 | TypedSegment 增加 cross_refs、ref_context、failed_table_refs 字段 |
| `app/core/parser_workflow/nodes/classify_node.py` | 修改 | 构造 TypedSegment 时补充 cross_refs=[]、ref_context="" |
| `app/core/parser_workflow/nodes/escalate_node.py` | 修改 | 构造 TypedSegment 时补充 cross_refs=[]、ref_context="" |
| `app/core/parser_workflow/nodes/enrich_node.py` | 新建 | 全部 enrich 逻辑：正则索引、引用提取、双重匹配、节点入口 |
| `app/core/parser_workflow/nodes/transform_node.py` | 修改 | _call_llm_transform 加 ref_context 参数；apply_strategy 传 ref_context 并写 meta |
| `app/core/parser_workflow/graph.py` | 修改 | 插入 enrich_node，更新边和 _should_escalate 返回值 |
| `app/core/parser_workflow/nodes/__init__.py` | 修改 | 导出 enrich_node |
| `tests/core/parser_workflow/test_enrich_node.py` | 新建 | enrich_node 全部单元测试 |
| `tests/core/parser_workflow/test_transform_node.py` | 修改 | 更新 TypedSegment 构造，补充新字段；覆盖 ref_context 注入场景 |

---

## Chunk 1: 数据模型与构造点更新

### Task 1: 更新 TypedSegment 数据模型

**Files:**
- Modify: `agent-server/app/core/parser_workflow/models.py`

- [ ] **Step 1: 在 models.py 中为 TypedSegment 增加两个字段**

打开 `agent-server/app/core/parser_workflow/models.py`，在 `TypedSegment` 类中 `escalated: bool` 之后追加：

```python
class TypedSegment(TypedDict):
    content: str
    content_type: str
    transform_params: dict
    confidence: float
    escalated: bool
    cross_refs: List[str]         # 识别到的所有引用标识符，如 ["表1", "附录A", "图A.1"]
    ref_context: str              # 已解析的被引用表格内容（拼接文本），未解析时为 ""
    failed_table_refs: List[str]  # 尝试内联但未能解析的表格引用标识符
```

- [ ] **Step 2: 运行现有 transform_node 测试，确保无破坏**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_transform_node.py -v
```

预期：全部 PASS（TypedDict 在运行时不强制校验，旧字典仍可正常工作）

---

### Task 2: 更新 classify_node 中的 TypedSegment 构造

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/classify_node.py`

`classify_node.py` 中有两处构造 TypedSegment，分别在低置信度（unknown）和正常分类两条分支。

- [ ] **Step 1: 更新低置信度分支**

找到 `classify_raw_chunk` 函数中的第一处 `TypedSegment(...)` 构造（unknown 分支），追加两个字段：

```python
seg = TypedSegment(
    content=item.content,
    content_type="unknown",
    transform_params={
        "strategy": "plain_embed",
        "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
    },
    confidence=confidence,
    escalated=False,
    cross_refs=[],
    ref_context="",
    failed_table_refs=[],
)
```

- [ ] **Step 2: 更新正常分类分支**

找到同函数中第二处 `TypedSegment(...)` 构造（else 分支），追加两个字段：

```python
seg = TypedSegment(
    content=item.content,
    content_type=ct_id,
    transform_params=transform_params,
    confidence=confidence,
    escalated=False,
    cross_refs=[],
    ref_context="",
    failed_table_refs=[],
)
```

- [ ] **Step 3: 运行现有测试**

```bash
cd agent-server && pytest tests/core/parser_workflow/ -v -k "not real_llm"
```

预期：全部 PASS

---

### Task 3: 更新 escalate_node 中的 TypedSegment 构造

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/escalate_node.py`

- [ ] **Step 1: 更新 escalate_node 中的 TypedSegment 构造**

找到 `escalate_node` 函数中的 `TypedSegment(...)` 构造（约第82行），追加两个字段：

```python
new_segments[j] = TypedSegment(
    content=seg["content"],
    content_type=new_ct_id,
    transform_params=transform_params,
    confidence=1.0,
    escalated=True,
    cross_refs=[],
    ref_context="",
    failed_table_refs=[],
)
```

- [ ] **Step 2: 运行现有测试**

```bash
cd agent-server && pytest tests/core/parser_workflow/ -v -k "not real_llm"
```

预期：全部 PASS

- [ ] **Step 3: Commit**

```bash
cd agent-server && git add app/core/parser_workflow/models.py \
  app/core/parser_workflow/nodes/classify_node.py \
  app/core/parser_workflow/nodes/escalate_node.py
git commit -m "feat: add cross_refs and ref_context fields to TypedSegment"
```

---

## Chunk 2: enrich_node 核心逻辑

### Task 4: 实现正则工具函数（表格标签索引 + 引用提取）

**Files:**
- Create: `agent-server/app/core/parser_workflow/nodes/enrich_node.py`
- Create: `agent-server/tests/core/parser_workflow/test_enrich_node.py`

- [ ] **Step 1: 为标签索引构建写失败测试**

创建 `agent-server/tests/core/parser_workflow/test_enrich_node.py`：

```python
from __future__ import annotations

import pytest
from typing import Dict, List
from app.core.parser_workflow.nodes.enrich_node import (
    build_table_label_index,
    extract_table_refs,
    extract_other_refs,
)
from app.core.parser_workflow.models import RawChunk


# ── build_table_label_index ──────────────────────────────────────────


def test_build_index_finds_table_at_start_of_chunk():
    """raw_chunk 以表格标题行开头时应被索引"""
    rc: RawChunk = {
        "content": "表1 样品浓缩条件\n\n| 参数 | 值 |\n|---|---|\n| 温度 | 25℃ |",
        "section_path": ["5", "5.1"],
        "char_count": 50,
    }
    index = build_table_label_index([rc])
    assert "表1" in index
    assert "温度" in index["表1"]


def test_build_index_finds_table_in_middle_of_chunk():
    """表格标题行不在 chunk 开头时也应被索引"""
    rc: RawChunk = {
        "content": "以下为测试参数：\n\n表1 样品浓缩条件\n\n| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        "section_path": ["5"],
        "char_count": 80,
    }
    index = build_table_label_index([rc])
    assert "表1" in index


def test_build_index_handles_table_with_space_in_label():
    """'表 1'（含空格）也应规范化为'表1'后被索引"""
    rc: RawChunk = {
        "content": "表 1 卡拉胶质量指标\n\n| 项目 | 指标 |",
        "section_path": ["3"],
        "char_count": 40,
    }
    index = build_table_label_index([rc])
    assert "表1" in index


def test_build_index_handles_lettered_table():
    """'表A.1'格式的表格标签应被正确索引"""
    rc: RawChunk = {
        "content": "表A.1 添加回收率\n\n| 浓度 | 回收率 |",
        "section_path": ["附录A"],
        "char_count": 40,
    }
    index = build_table_label_index([rc])
    assert "表A.1" in index


def test_build_index_empty_when_no_table_title():
    """无表格标题行的 chunk 不应进入索引"""
    rc: RawChunk = {
        "content": "这是普通正文，没有表格。",
        "section_path": ["1"],
        "char_count": 12,
    }
    index = build_table_label_index([rc])
    assert len(index) == 0


# ── extract_table_refs ───────────────────────────────────────────────


def test_extract_table_refs_basic():
    """'见表1'应提取出标准化标签'表1'"""
    refs = extract_table_refs("样品浓缩条件见表1。")
    assert "表1" in refs


def test_extract_table_refs_with_context_prefix():
    """'条件见表1'类带前缀的引用也应提取"""
    refs = extract_table_refs("a）样品浓缩条件见表1；")
    assert "表1" in refs


def test_extract_table_refs_canjian():
    """'参见表A.1'应提取'表A.1'"""
    refs = extract_table_refs("规格参见表A.1。")
    assert "表A.1" in refs


def test_extract_table_refs_canzhao():
    """'参照表B.1'应提取'表B.1'"""
    refs = extract_table_refs("参照表B.1进行操作。")
    assert "表B.1" in refs


def test_extract_table_refs_returns_empty_for_no_ref():
    """无表格引用时返回空列表"""
    refs = extract_table_refs("本节描述检测方法。")
    assert refs == []


# ── extract_other_refs ───────────────────────────────────────────────


def test_extract_other_refs_figure():
    """'见图A.1'应提取'图A.1'"""
    refs = extract_other_refs("色谱图见图A.1。")
    assert any("图A.1" in r for r in refs)


def test_extract_other_refs_appendix():
    """'见附录A'应提取附录引用"""
    refs = extract_other_refs("具体见附录A。")
    assert any("附录A" in r for r in refs)


def test_extract_other_refs_canzhao():
    """'参照图A.2'应提取图引用"""
    refs = extract_other_refs("参照图A.2所示操作。")
    assert any("图A.2" in r for r in refs)


def test_extract_other_refs_no_table():
    """纯表格引用不应出现在 other_refs 中"""
    refs = extract_other_refs("条件见表1。")
    assert refs == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_enrich_node.py -v
```

预期：全部 FAIL（ImportError，模块不存在）

- [ ] **Step 3: 实现 build_table_label_index、extract_table_refs、extract_other_refs**

创建 `agent-server/app/core/parser_workflow/nodes/enrich_node.py`：

```python
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)

# 匹配表格标题行，如 "表1 xxx"、"表A.1 xxx"、"表 1 xxx"
# 规范化后 key 去除 "表" 后的空格：表 1 → 表1
_TABLE_TITLE_PATTERN = re.compile(
    r'(?:^|\n)表\s*([\dA-Z]+(?:\.\d+)*)\s+\S',
    re.UNICODE,
)

# 匹配表格引用，如 "见表1"、"参见表A.1"、"条件见表 B.1"
_TABLE_REF_PATTERN = re.compile(
    r'(?:见|参见|参照)[^\n，。；]*?表\s*([\dA-Z]+(?:\.\d+)*)',
    re.UNICODE,
)

# 匹配其他引用（图/附录/章节），只记录不内联
_OTHER_REF_PATTERN = re.compile(
    r'(?:见|参见|参照|按照?)\s*((?:图|附录)[^\s，。；]{0,15}'
    r'|第?\s*\d+[\.\d]*\s*[节章条]'
    r'|\d+\.\d+[\.\d]*)',
    re.UNICODE,
)


def _normalize_label(raw: str) -> str:
    """将标签规范化：去除'表'后的空格，如'表 1' → '表1'，'A.1' → 'A.1'"""
    return raw.replace(" ", "").replace("\u3000", "")


def build_table_label_index(raw_chunks: List[RawChunk]) -> Dict[str, str]:
    """
    扫描所有 raw_chunks 的完整内容，查找表格标题行，建立 {标准化标签: chunk内容} 索引。
    如 "表1 样品浓缩条件" → {"表1": <chunk content>}
    """
    index: Dict[str, str] = {}
    for rc in raw_chunks:
        for m in _TABLE_TITLE_PATTERN.finditer(rc["content"]):
            label = "表" + _normalize_label(m.group(1))
            index[label] = rc["content"]
    return index


def extract_table_refs(text: str) -> List[str]:
    """
    从文本中提取表格引用标识符列表（已规范化），如 ["表1", "表A.1"]。
    匹配 "见表X"、"参见表X"、"参照表X" 及含前缀的形式。
    """
    return ["表" + _normalize_label(m.group(1)) for m in _TABLE_REF_PATTERN.finditer(text)]


def extract_other_refs(text: str) -> List[str]:
    """
    从文本中提取非表格引用（图/附录/章节），只记录不内联。
    返回原始匹配字符串列表。
    """
    results = []
    for m in _OTHER_REF_PATTERN.finditer(text):
        ref = m.group(1).strip()
        # 排除纯表格引用（TABLE_REF_PATTERN 已覆盖）
        if not ref.startswith("表"):
            results.append(ref)
    return results
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_enrich_node.py -v -k "index or refs"
```

预期：全部 PASS

---

### Task 5: 实现双重匹配逻辑

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/enrich_node.py`
- Modify: `agent-server/tests/core/parser_workflow/test_enrich_node.py`

- [ ] **Step 1: 追加双重匹配测试**

在 `test_enrich_node.py` 末尾追加：

```python
from app.core.parser_workflow.nodes.enrich_node import resolve_table_ref
from app.core.parser_workflow.models import ClassifiedChunk, TypedSegment


# ── resolve_table_ref ────────────────────────────────────────────────


def _make_classified_chunk(section_path, content_type="table") -> ClassifiedChunk:
    raw: RawChunk = {
        "content": "| 项目 | 指标 |\n|---|---|\n| 水分 | ≤12% |",
        "section_path": section_path,
        "char_count": 40,
    }
    seg: TypedSegment = {
        "content": "| 项目 | 指标 |",
        "content_type": content_type,
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
    }
    return ClassifiedChunk(raw_chunk=raw, segments=[seg], has_unknown=False)


def test_resolve_hits_label_index():
    """正则索引命中时直接返回 chunk 内容"""
    index = {"表1": "| 参数 | 值 |\n|---|---|\n| 温度 | 25℃ |"}
    result = resolve_table_ref("表1", index, [])
    assert result is not None
    assert "温度" in result


def test_resolve_falls_back_to_section_path():
    """正则索引未命中时，通过 section_path 模糊匹配找到 table chunk"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表1 卡拉胶质量指标"])
    result = resolve_table_ref("表1", index, [cc])
    assert result is not None
    assert "水分" in result


def test_resolve_section_path_normalizes_spaces():
    """section_path 含空格的标签也能匹配（规范化后比较）"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表 1 卡拉胶质量指标"])
    result = resolve_table_ref("表1", index, [cc])
    assert result is not None


def test_resolve_returns_none_when_not_found():
    """两步都未命中时返回 None"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表2 其他指标"])
    result = resolve_table_ref("表1", index, [cc])
    assert result is None


def test_resolve_ignores_non_table_chunks():
    """content_type 非 table 的 chunk 不参与 section_path 匹配"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表1 卡拉胶质量指标"], content_type="plain_text")
    result = resolve_table_ref("表1", index, [cc])
    assert result is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_enrich_node.py -v -k "resolve"
```

预期：FAIL（ImportError: cannot import resolve_table_ref）

- [ ] **Step 3: 在 enrich_node.py 实现 resolve_table_ref**

在 `enrich_node.py` 中追加：

```python
def resolve_table_ref(
    label: str,
    label_index: Dict[str, str],
    classified_chunks: List[ClassifiedChunk],
) -> str | None:
    """
    双重匹配：先查正则标签索引，再查 classified_chunks 中 table 段的 section_path。
    找到返回该 raw_chunk 的内容字符串，未找到返回 None。
    """
    # Step 1: 正则标签索引
    if label in label_index:
        return label_index[label]

    # Step 2: section_path 模糊匹配
    label_norm = _normalize_label(label)
    for cc in classified_chunks:
        # 只检查含 table 类型段的 chunk
        if not any(seg["content_type"] == "table" for seg in cc["segments"]):
            continue
        raw = cc["raw_chunk"]
        for path_seg in raw["section_path"]:
            if label_norm in _normalize_label(path_seg):
                return raw["content"]

    return None
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_enrich_node.py -v -k "resolve"
```

预期：全部 PASS

---

### Task 6: 实现 enrich_node 主函数

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/enrich_node.py`
- Modify: `agent-server/tests/core/parser_workflow/test_enrich_node.py`

- [ ] **Step 1: 追加 enrich_node 主函数测试**

在 `test_enrich_node.py` 末尾追加：

```python
from app.core.parser_workflow.nodes.enrich_node import enrich_node


# ── enrich_node ──────────────────────────────────────────────────────


def _make_state(seg_content: str, raw_chunks=None, extra_classified=None) -> dict:
    """构造最小化的 WorkflowState 用于 enrich_node 测试"""
    table_raw: RawChunk = {
        "content": "表1 样品浓缩条件\n\n| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        "section_path": ["5", "5.1"],
        "char_count": 60,
    }
    ref_raw: RawChunk = {
        "content": seg_content,
        "section_path": ["5", "5.2"],
        "char_count": len(seg_content),
    }
    ref_seg: TypedSegment = {
        "content": seg_content,
        "content_type": "plain_text",
        "transform_params": {"strategy": "semantic_standardization", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
    }
    table_seg: TypedSegment = {
        "content": "| 参数 | 值 |",
        "content_type": "table",
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 0.95,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
    }
    ref_cc = ClassifiedChunk(raw_chunk=ref_raw, segments=[ref_seg], has_unknown=False)
    table_cc = ClassifiedChunk(raw_chunk=table_raw, segments=[table_seg], has_unknown=False)
    chunks = [ref_cc, table_cc] + (extra_classified or [])
    return {
        "md_content": "",
        "doc_metadata": {"standard_no": "GB-001"},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": (raw_chunks if raw_chunks is not None else [table_raw, ref_raw]),
        "classified_chunks": chunks,
        "final_chunks": [],
        "errors": [],
    }


def test_enrich_node_inlines_table_via_label_index():
    """见表1 引用能通过正则标签索引内联表格内容"""
    state = _make_state("a）样品浓缩条件见表1；")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert segs[0]["ref_context"] != ""
    assert "流速" in segs[0]["ref_context"]


def test_enrich_node_inlines_table_via_section_path():
    """正则索引未命中时通过 section_path 回退匹配"""
    # 表格 raw_chunk 内容无标题行 → label_index 为空 → 强制走 section_path 路径
    table_raw_no_title: RawChunk = {
        "content": "| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        "section_path": ["5", "表1 样品浓缩条件"],
        "char_count": 40,
    }
    table_seg: TypedSegment = {
        "content": "| 参数 | 值 |",
        "content_type": "table",
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 0.95,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    ref_raw: RawChunk = {
        "content": "样品浓缩条件见表1",
        "section_path": ["5", "5.2"],
        "char_count": 9,
    }
    ref_seg: TypedSegment = {
        "content": "样品浓缩条件见表1",
        "content_type": "plain_text",
        "transform_params": {"strategy": "semantic_standardization", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    table_cc = ClassifiedChunk(raw_chunk=table_raw_no_title, segments=[table_seg], has_unknown=False)
    ref_cc = ClassifiedChunk(raw_chunk=ref_raw, segments=[ref_seg], has_unknown=False)
    state = {
        "md_content": "",
        "doc_metadata": {"standard_no": "GB-001"},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": [table_raw_no_title, ref_raw],
        "classified_chunks": [ref_cc, table_cc],
        "final_chunks": [],
        "errors": [],
    }
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "流速" in segs[0]["ref_context"]


def test_enrich_node_records_cross_refs():
    """识别到的引用（包括图/附录）均应写入 cross_refs"""
    state = _make_state("条件见表1，色谱图见图A.1。")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "表1" in segs[0]["cross_refs"]
    assert any("图A.1" in r for r in segs[0]["cross_refs"])


def test_enrich_node_other_refs_not_inlined():
    """图/附录引用只记录 cross_refs，ref_context 仍为空"""
    state = _make_state("具体见附录A，色谱图见图A.1。")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert segs[0]["ref_context"] == ""
    assert len(segs[0]["cross_refs"]) > 0


def test_enrich_node_unresolved_table_writes_error():
    """表格引用未命中时写入 errors 警告，不抛异常"""
    state = _make_state("条件见表99。")  # 表99 不存在
    result = enrich_node(state)
    assert any("表99" in e for e in result["errors"])


def test_enrich_node_appends_to_existing_errors():
    """enrich_node 追加 errors，不覆盖上游已有的错误"""
    state = _make_state("条件见表99。")
    state["errors"] = ["ERROR: 上游已有错误"]
    result = enrich_node(state)
    assert "ERROR: 上游已有错误" in result["errors"]
    assert any("表99" in e for e in result["errors"])


def test_enrich_node_meta_records_failed_table_refs():
    """未能解析的表格引用写入 TypedSegment.failed_table_refs"""
    state = _make_state("条件见表99。")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "表99" in segs[0]["failed_table_refs"]
    assert segs[0]["ref_context"] == ""


def test_enrich_node_partial_resolution_tracks_failed():
    """部分表格引用解析成功、部分失败时，failed_table_refs 只含失败的"""
    state = _make_state("条件见表1，规格见表99。")  # 表1 能解析，表99 不能
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "表99" in segs[0]["failed_table_refs"]
    assert "表1" not in segs[0]["failed_table_refs"]
    assert segs[0]["ref_context"] != ""  # 表1 的内容已内联
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_enrich_node.py -v -k "enrich_node"
```

预期：FAIL（ImportError: cannot import enrich_node）

- [ ] **Step 3: 实现 enrich_node 主函数**

在 `enrich_node.py` 末尾追加：

```python
def enrich_node(state: WorkflowState) -> dict:
    """
    扫描所有 classified_chunks 中的 TypedSegment，识别交叉引用：
    - 表格引用（见表X）：双重匹配后将内容写入 ref_context
    - 其他引用（图/附录/章节）：只记录到 cross_refs
    未解析的表格引用追加到 errors（不中断流程）。
    """
    raw_chunks: List[RawChunk] = state["raw_chunks"]
    classified_chunks: List[ClassifiedChunk] = [dict(cc) for cc in state["classified_chunks"]]
    existing_errors: List[str] = list(state.get("errors", []))
    new_errors: List[str] = []

    # Step 1: 建表格标签索引
    label_index = build_table_label_index(raw_chunks)

    # Step 2: 逐段处理
    updated_chunks: List[ClassifiedChunk] = []
    for cc in classified_chunks:
        new_segments: List[TypedSegment] = []
        for seg in cc["segments"]:
            text = seg["content"]

            # 提取引用
            table_refs = extract_table_refs(text)
            other_refs = extract_other_refs(text)
            all_refs = list(dict.fromkeys(table_refs + other_refs))  # 去重保序

            # 解析表格引用
            resolved_parts: List[str] = []
            failed_labels: List[str] = []
            for label in table_refs:
                content = resolve_table_ref(label, label_index, classified_chunks)
                if content is not None:
                    resolved_parts.append(content)
                else:
                    failed_labels.append(label)
                    new_errors.append(
                        f"WARN: unresolved cross_ref \"{label}\" "
                        f"in section_path {cc['raw_chunk']['section_path']} "
                        f"— no matching raw_chunk found"
                    )

            new_segments.append(TypedSegment(
                content=seg["content"],
                content_type=seg["content_type"],
                transform_params=seg["transform_params"],
                confidence=seg["confidence"],
                escalated=seg["escalated"],
                cross_refs=all_refs,
                ref_context="\n\n".join(resolved_parts),
                failed_table_refs=failed_labels,
            ))

        updated_chunks.append(ClassifiedChunk(
            raw_chunk=cc["raw_chunk"],
            segments=new_segments,
            has_unknown=cc["has_unknown"],
        ))

    return {
        "classified_chunks": updated_chunks,
        "errors": existing_errors + new_errors,
    }
```

- [ ] **Step 4: 运行全部 enrich_node 测试**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_enrich_node.py -v
```

预期：全部 PASS

- [ ] **Step 5: Commit**

```bash
cd agent-server && git add \
  app/core/parser_workflow/nodes/enrich_node.py \
  tests/core/parser_workflow/test_enrich_node.py
git commit -m "feat: add enrich_node with dual-match cross-reference resolution"
```

---

## Chunk 3: transform_node 更新与 graph 接入

### Task 7: 更新 transform_node 使用 ref_context

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/transform_node.py`
- Modify: `agent-server/tests/core/parser_workflow/test_transform_node.py`

- [ ] **Step 1: 追加 ref_context 注入测试**

在 `test_transform_node.py` 末尾追加：

```python
def test_call_llm_transform_appends_ref_context_to_prompt():
    """ref_context 非空时，prompt 应包含表格内容"""
    mock_resp = MagicMock()
    mock_resp.content = "转化后的文本"
    captured_prompt = {}

    def capture_invoke(prompt):
        captured_prompt["value"] = prompt
        return mock_resp

    with patch(
        "app.core.parser_workflow.nodes.transform_node.create_chat_model"
    ) as mock_factory, patch(
        "app.core.parser_workflow.nodes.transform_node.resolve_provider",
        return_value="openai",
    ):
        mock_chat = MagicMock()
        mock_chat.invoke.side_effect = capture_invoke
        mock_factory.return_value = mock_chat

        _call_llm_transform(
            "样品浓缩条件见表1",
            {"strategy": "semantic_standardization", "prompt_template": "请转化："},
            ref_context="| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        )

    assert "流速" in captured_prompt["value"]
    assert "表格" in captured_prompt["value"]


def test_call_llm_transform_no_ref_context_unchanged():
    """ref_context 为空时，prompt 不包含额外表格内容"""
    mock_resp = MagicMock()
    mock_resp.content = "转化后的文本"
    captured_prompt = {}

    def capture_invoke(prompt):
        captured_prompt["value"] = prompt
        return mock_resp

    with patch(
        "app.core.parser_workflow.nodes.transform_node.create_chat_model"
    ) as mock_factory, patch(
        "app.core.parser_workflow.nodes.transform_node.resolve_provider",
        return_value="openai",
    ):
        mock_chat = MagicMock()
        mock_chat.invoke.side_effect = capture_invoke
        mock_factory.return_value = mock_chat

        _call_llm_transform(
            "普通内容",
            {"strategy": "plain_embed", "prompt_template": "请转化："},
        )

    assert "表格" not in captured_prompt["value"]


def test_apply_strategy_writes_cross_refs_to_meta():
    """apply_strategy 应将 seg 的 cross_refs 写入 DocumentChunk.meta"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["1", "1.1"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "片段内容",
        "content_type": "plain_text",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "请转化："},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": ["表1", "图A.1"],
        "ref_context": "| 参数 | 值 |",
    }
    doc_metadata = {"standard_no": "GB/T-001", "title": "测试标准"}

    with patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="转化结果",
    ):
        result = apply_strategy([seg], raw_chunk, doc_metadata)

    assert result[0]["meta"]["cross_refs"] == ["表1", "图A.1"]
    assert "failed_table_refs" in result[0]["meta"]
```

- [ ] **Step 2: 运行新测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_transform_node.py -v \
  -k "ref_context or cross_refs"
```

预期：FAIL

- [ ] **Step 3: 更新 _call_llm_transform 签名**

在 `transform_node.py` 中修改 `_call_llm_transform`：

```python
def _call_llm_transform(
    content: str,
    transform_params: dict,
    ref_context: str = "",
) -> str:
    provider = resolve_provider(settings.TRANSFORM_LLM_PROVIDER)
    chat = create_chat_model(settings.TRANSFORM_MODEL, provider, output_schema=TransformOutput)
    format_example = """
    {
        "content": "转化后的内容"
    }
    """

    prompt = f"""
    请根据以下提示词，将待处理内容转化为 JSON 结构。
    {transform_params["prompt_template"]}
    \n\n待处理内容：
    {content}
    \n\n返回格式（json）：
    {format_example}
    """

    if ref_context:
        prompt += f"\n\n以下是文中引用的表格内容，请结合该表格理解上下文：\n{ref_context}"

    resp: TransformOutput = chat.invoke(prompt)
    return resp.content
```

- [ ] **Step 4: 更新 apply_strategy 传入 ref_context 并写 meta**

修改 `apply_strategy` 函数：

```python
def apply_strategy(
    segments: List[TypedSegment],
    raw_chunk,
    doc_metadata: dict,
) -> List[DocumentChunk]:
    results: List[DocumentChunk] = []

    for seg in segments:
        raw_content = raw_chunk["content"]
        ref_context = seg.get("ref_context", "")
        cross_refs = seg.get("cross_refs", [])

        llm_text = _call_llm_transform(seg["content"], seg["transform_params"], ref_context)

        # 直接使用 enrich_node 精确追踪的失败列表（正确处理部分解析的情况）
        failed_table_refs = seg.get("failed_table_refs", [])

        results.append(
            DocumentChunk(
                chunk_id=make_chunk_id(
                    doc_metadata.get("standard_no", ""),
                    raw_chunk["section_path"],
                    llm_text,
                ),
                doc_metadata=doc_metadata,
                section_path=raw_chunk["section_path"],
                content_type=seg["content_type"],
                content=llm_text,
                raw_content=raw_content,
                meta={
                    "transform_strategy": seg["transform_params"]["strategy"],
                    "segment_raw_content": seg["content"],
                    "cross_refs": cross_refs,
                    "non_table_refs": [r for r in cross_refs if not r.startswith("表")],
                    "failed_table_refs": failed_table_refs,
                },
            )
        )

    return results
```

- [ ] **Step 5: 运行全部 transform_node 测试**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_transform_node.py -v
```

预期：全部 PASS

- [ ] **Step 6: Commit**

```bash
cd agent-server && git add \
  app/core/parser_workflow/nodes/transform_node.py \
  tests/core/parser_workflow/test_transform_node.py
git commit -m "feat: update transform_node to accept and use ref_context in LLM prompt"
```

---

### Task 8: 更新 graph.py 插入 enrich_node

**Files:**
- Modify: `agent-server/app/core/parser_workflow/graph.py`
- Modify: `agent-server/app/core/parser_workflow/nodes/__init__.py`

- [ ] **Step 1: 修改 graph.py**

将 `graph.py` 中的 `_build_graph` 和 `_should_escalate` 更新如下：

```python
from app.core.parser_workflow.nodes.enrich_node import enrich_node

def _should_escalate(state: WorkflowState) -> str:
    if any(c["has_unknown"] for c in state["classified_chunks"]):
        return "escalate_node"
    return "enrich_node"   # 原来返回 "transform_node"


def _build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("parse_node", parse_node)
    builder.add_node("structure_node", structure_node)
    builder.add_node("slice_node", slice_node)
    builder.add_node("classify_node", classify_node)
    builder.add_node("escalate_node", escalate_node)
    builder.add_node("enrich_node", enrich_node)   # 新增
    builder.add_node("transform_node", transform_node)

    builder.set_entry_point("parse_node")
    builder.add_edge("parse_node", "structure_node")
    builder.add_edge("structure_node", "slice_node")
    builder.add_edge("slice_node", "classify_node")
    builder.add_conditional_edges("classify_node", _should_escalate)
    builder.add_edge("escalate_node", "enrich_node")   # 原来是 escalate_node → transform_node
    builder.add_edge("enrich_node", "transform_node")  # 新增
    builder.add_edge("transform_node", END)             # 保留原有终止边
    return builder.compile()
```

- [ ] **Step 2: 更新 nodes/__init__.py**

文件当前为空，追加以下内容（勿覆盖）：

```python
from app.core.parser_workflow.nodes.enrich_node import enrich_node  # noqa: F401

__all__ = ["enrich_node"]
```

- [ ] **Step 3: 写 graph 集成测试**

在 `test_enrich_node.py` 末尾追加：

```python
import pytest
from unittest.mock import patch, MagicMock
from app.core.parser_workflow.graph import _build_graph, _should_escalate
from app.core.parser_workflow.models import WorkflowState


# ── graph integration ────────────────────────────────────────────────


def test_should_escalate_returns_enrich_node_when_no_unknown():
    """无 unknown 段时 _should_escalate 应返回 'enrich_node'（原返回 'transform_node'）"""
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": [],
        "classified_chunks": [
            ClassifiedChunk(
                raw_chunk={"content": "x", "section_path": [], "char_count": 1},
                segments=[{
                    "content": "x",
                    "content_type": "plain_text",
                    "transform_params": {},
                    "confidence": 0.9,
                    "escalated": False,
                    "cross_refs": [],
                    "ref_context": "",
                }],
                has_unknown=False,
            )
        ],
        "final_chunks": [],
        "errors": [],
    }
    assert _should_escalate(state) == "enrich_node"


def test_should_escalate_returns_escalate_node_when_has_unknown():
    """有 unknown 段时 _should_escalate 应返回 'escalate_node'"""
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": [],
        "classified_chunks": [
            ClassifiedChunk(
                raw_chunk={"content": "x", "section_path": [], "char_count": 1},
                segments=[],
                has_unknown=True,
            )
        ],
        "final_chunks": [],
        "errors": [],
    }
    assert _should_escalate(state) == "escalate_node"


def test_graph_contains_enrich_node():
    """编译后的 graph 应包含 enrich_node 节点"""
    graph = _build_graph()
    node_names = list(graph.nodes.keys())
    assert "enrich_node" in node_names


def test_enrich_node_sees_table_corrected_by_escalate():
    """escalate_node 将 unknown 段修正为 table 后，enrich_node 应能通过 section_path 匹配该表格"""
    # 模拟 escalate_node 输出：原 unknown 段已被修正为 table
    table_raw: RawChunk = {
        "content": "| 项目 | 指标 |\n|---|---|\n| 水分 | ≤12% |",
        "section_path": ["3", "表1 卡拉胶质量要求"],
        "char_count": 40,
    }
    escalated_seg: TypedSegment = {
        "content": "| 项目 | 指标 |",
        "content_type": "table",      # escalate_node 修正后的类型
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 1.0,
        "escalated": True,            # 标记为已 escalate
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    ref_raw: RawChunk = {
        "content": "感官要求见表1。",
        "section_path": ["3", "3.1"],
        "char_count": 8,
    }
    ref_seg: TypedSegment = {
        "content": "感官要求见表1。",
        "content_type": "plain_text",
        "transform_params": {"strategy": "semantic_standardization", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    table_cc = ClassifiedChunk(raw_chunk=table_raw, segments=[escalated_seg], has_unknown=False)
    ref_cc = ClassifiedChunk(raw_chunk=ref_raw, segments=[ref_seg], has_unknown=False)
    state = {
        "md_content": "",
        "doc_metadata": {"standard_no": "GB-001"},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": [table_raw, ref_raw],
        "classified_chunks": [ref_cc, table_cc],
        "final_chunks": [],
        "errors": [],
    }
    result = enrich_node(state)
    ref_segs = result["classified_chunks"][0]["segments"]
    # section_path 包含 "表1"，应能通过回退匹配找到表格内容
    assert "水分" in ref_segs[0]["ref_context"]
```

- [ ] **Step 4: 运行测试**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_enrich_node.py -v \
  -k "should_escalate or graph_contains"
```

预期：全部 PASS

- [ ] **Step 5: 运行完整测试套件**

```bash
cd agent-server && pytest tests/core/parser_workflow/ -v -k "not real_llm"
```

预期：全部 PASS

- [ ] **Step 6: Commit**

```bash
cd agent-server && git add \
  app/core/parser_workflow/graph.py \
  app/core/parser_workflow/nodes/__init__.py \
  tests/core/parser_workflow/test_enrich_node.py
git commit -m "feat: wire enrich_node into parser_workflow graph between escalate and transform"
```

---

## 验收检查

所有实现完成后，运行完整测试确认无回归：

```bash
cd agent-server && pytest tests/core/parser_workflow/ -v -k "not real_llm"
```

预期：全部 PASS，无跳过，无错误。
