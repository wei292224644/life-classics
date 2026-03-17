# Dual Content Type Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 parser_workflow 的单字段 `content_type` 替换为双维度 `structure_type`（呈现形式）+ `semantic_type`（内容用途），同步更新数据模型、规则 JSON、LLM prompt 及所有下游节点。

**Architecture:** 自底向上修改——先改数据契约（models.py + output.py），再改规则 JSON 和 RulesStore，最后改两个节点（classify_node + transform_node）。每一步先写失败的测试，再写最小实现，再提交。

**Tech Stack:** Python 3.12+, Pydantic v2, TypedDict, pytest, uv

---

## File Map

| 文件 | 变更类型 |
|---|---|
| `app/core/parser_workflow/nodes/output.py` | `SegmentItem` 字段替换 |
| `app/core/parser_workflow/models.py` | `TypedSegment` + `DocumentChunk` 字段替换 |
| `app/core/parser_workflow/rules/content_type_rules.json` | 重写 |
| `app/core/parser_workflow/rules.py` | 仅改 `get_transform_params` 签名 |
| `app/core/parser_workflow/nodes/classify_node.py` | prompt 重写 + 字段引用更新 |
| `app/core/parser_workflow/nodes/transform_node.py` | `DocumentChunk(content_type=...)` → 双字段 |
| `app/core/parser_workflow/nodes/escalate_node.py` | 若全量测试失败则检查此文件的 `seg["content_type"]` 引用 |
| `app/core/document_chunk.py` | 添加 `# DEPRECATED` 注释 |
| `tests/core/parser_workflow/test_classify_node.py` | 全部重写为新 JSON 结构测试 |
| `tests/core/parser_workflow/test_classify_node_real_llm.py` | 断言更新 |
| `tests/core/parser_workflow/test_workflow.py` | 无需改动（已确认无 content_type 断言） |

---

## Task 1: 更新 `SegmentItem` — output.py 字段替换

**Files:**
- Modify: `app/core/parser_workflow/nodes/output.py`
- Test: `tests/core/parser_workflow/test_output_models.py`（新建）

- [ ] **Step 1: 写失败测试**

```python
# tests/core/parser_workflow/test_output_models.py
from app.core.parser_workflow.nodes.output import SegmentItem, ClassifyOutput


def test_segment_item_has_structure_and_semantic_type():
    item = SegmentItem(
        content="试样处理：称取约2g试样",
        structure_type="list",
        semantic_type="procedure",
        confidence=0.9,
    )
    assert item.structure_type == "list"
    assert item.semantic_type == "procedure"


def test_segment_item_rejects_content_type():
    """SegmentItem 不再有 content_type 字段"""
    import pytest
    from pydantic import ValidationError
    with pytest.raises((ValidationError, TypeError)):
        SegmentItem(content="x", content_type="table", confidence=0.8)


def test_classify_output_segments_use_dual_type():
    output = ClassifyOutput(segments=[
        SegmentItem(content="a", structure_type="paragraph", semantic_type="scope", confidence=0.85),
        SegmentItem(content="b", structure_type="table", semantic_type="limit", confidence=0.92),
    ])
    assert output.segments[0].structure_type == "paragraph"
    assert output.segments[1].semantic_type == "limit"
```

- [ ] **Step 2: 运行以确认失败**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_output_models.py -v
```

期望：`FAILED` — `SegmentItem` 无 `structure_type`/`semantic_type` 字段

- [ ] **Step 3: 修改 `output.py`**

```python
# app/core/parser_workflow/nodes/output.py
from typing import List, Literal
from pydantic import BaseModel, Field


class TransformParams(BaseModel):
    strategy: str
    prompt_template: str


class TransformOutput(BaseModel):
    content: str


class DocTypeOutput(BaseModel):
    id: str
    description: str
    detect_keywords: List[str]
    detect_heading_patterns: List[str]


class EscalateOutput(BaseModel):
    """LLM 结构化输出，需与 prompt 中的 format_example 一致。"""
    action: Literal["use_existing", "create_new"]
    id: str
    description: str
    transform: TransformParams


class SegmentItem(BaseModel):
    content: str
    structure_type: str
    semantic_type: str
    confidence: float = Field(default=0.8, ge=0, le=1)


class ClassifyOutput(BaseModel):
    segments: List[SegmentItem]
```

- [ ] **Step 4: 运行确认通过**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_output_models.py -v
```

期望：`3 passed`

- [ ] **Step 5: 提交**

```bash
cd agent-server && git add app/core/parser_workflow/nodes/output.py tests/core/parser_workflow/test_output_models.py
git commit -m "feat: replace content_type with structure_type+semantic_type in SegmentItem"
```

---

## Task 2: 更新 `models.py` — TypedSegment + DocumentChunk 字段替换

**Files:**
- Modify: `app/core/parser_workflow/models.py`
- Test: `tests/core/parser_workflow/test_models.py`（新建）

- [ ] **Step 1: 写失败测试**

```python
# tests/core/parser_workflow/test_models.py
from app.core.parser_workflow.models import TypedSegment, DocumentChunk


def test_typed_segment_has_dual_type_fields():
    seg = TypedSegment(
        content="试剂：异丙醇溶液 60%",
        structure_type="list",
        semantic_type="material",
        transform_params={"strategy": "plain_embed", "prompt_template": "..."},
        confidence=0.88,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    assert seg["structure_type"] == "list"
    assert seg["semantic_type"] == "material"
    assert "content_type" not in seg


def test_document_chunk_has_dual_type_fields():
    chunk = DocumentChunk(
        chunk_id="abc123",
        doc_metadata={"standard_no": "GB1886.47"},
        section_path=["A.3", "A.3.1"],
        structure_type="list",
        semantic_type="procedure",
        content="转化后文本",
        raw_content="原始文本",
        meta={},
    )
    assert chunk["structure_type"] == "list"
    assert chunk["semantic_type"] == "procedure"
    assert "content_type" not in chunk
```

- [ ] **Step 2: 运行确认失败**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_models.py -v
```

期望：`FAILED` — 无 `structure_type` 字段，且有多余的 `content_type` key

- [ ] **Step 3: 修改 `models.py`**

将 `TypedSegment` 中的 `content_type: str` 替换为两行：

```python
class TypedSegment(TypedDict):
    content: str
    structure_type: str        # 结构维度：paragraph / list / table / formula / header
    semantic_type: str         # 语义维度：metadata / scope / limit / procedure / material / calculation / definition / amendment
    transform_params: dict
    confidence: float
    escalated: bool
    cross_refs: List[str]
    ref_context: str
    failed_table_refs: List[str]
```

将 `DocumentChunk` 中的 `content_type: str` 替换为两行：

```python
class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    structure_type: str
    semantic_type: str
    content: str
    raw_content: str
    meta: dict
```

- [ ] **Step 4: 运行确认通过**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_models.py -v
```

期望：`2 passed`

- [ ] **Step 5: 提交**

```bash
cd agent-server && git add app/core/parser_workflow/models.py tests/core/parser_workflow/test_models.py
git commit -m "feat: replace content_type with structure_type+semantic_type in TypedSegment and DocumentChunk"
```

---

## Task 3: 重写 `content_type_rules.json` + 更新 `rules.py`

**Files:**
- Rewrite: `app/core/parser_workflow/rules/content_type_rules.json`
- Modify: `app/core/parser_workflow/rules.py`
- Modify: `tests/core/parser_workflow/test_classify_node.py`（全部重写）

- [ ] **Step 1: 写失败测试（替换旧测试文件全部内容）**

```python
# tests/core/parser_workflow/test_classify_node.py
import pytest
from app.core.parser_workflow.rules import RulesStore


@pytest.fixture
def store(tmp_path):
    """使用默认规则初始化 RulesStore（复制到 tmp_path 以避免污染）"""
    return RulesStore(str(tmp_path))


# ── structure_types ───────────────────────────────────────────────────

def test_structure_types_contains_five_types(store):
    rules = store.get_content_type_rules()
    ids = [t["id"] for t in rules["structure_types"]]
    assert set(ids) == {"paragraph", "list", "table", "formula", "header"}, f"实际：{ids}"


def test_each_structure_type_has_description_and_examples(store):
    rules = store.get_content_type_rules()
    for t in rules["structure_types"]:
        assert "description" in t, f"{t['id']} 缺 description"
        assert "examples" in t and len(t["examples"]) >= 1, f"{t['id']} 缺 examples"


# ── semantic_types ────────────────────────────────────────────────────

def test_semantic_types_contains_eight_types(store):
    rules = store.get_content_type_rules()
    ids = [t["id"] for t in rules["semantic_types"]]
    assert set(ids) == {
        "metadata", "scope", "limit", "procedure",
        "material", "calculation", "definition", "amendment",
    }, f"实际：{ids}"


def test_each_semantic_type_has_description_and_examples(store):
    rules = store.get_content_type_rules()
    for t in rules["semantic_types"]:
        assert "description" in t, f"{t['id']} 缺 description"
        assert "examples" in t and len(t["examples"]) >= 1, f"{t['id']} 缺 examples"


# ── transform.by_semantic_type ────────────────────────────────────────

def test_transform_exists_for_all_semantic_types(store):
    rules = store.get_content_type_rules()
    transform_map = rules["transform"]["by_semantic_type"]
    for t in rules["semantic_types"]:
        assert t["id"] in transform_map, f"semantic_type '{t['id']}' 缺少 transform 配置"


def test_each_transform_has_strategy_and_non_empty_prompt_template(store):
    rules = store.get_content_type_rules()
    for sem_id, cfg in rules["transform"]["by_semantic_type"].items():
        assert "strategy" in cfg, f"{sem_id} 缺 strategy"
        assert cfg.get("prompt_template", ""), f"{sem_id} prompt_template 为空"


# ── get_transform_params ──────────────────────────────────────────────

def test_get_transform_params_by_semantic_type(store):
    params = store.get_transform_params("procedure")
    assert "strategy" in params
    assert "prompt_template" in params
    assert params["prompt_template"]


def test_get_transform_params_unknown_falls_back_to_plain_embed(store):
    params = store.get_transform_params("nonexistent_type")
    assert params["strategy"] == "plain_embed"


def test_get_transform_params_calculation_uses_formula_embed(store):
    params = store.get_transform_params("calculation")
    assert params["strategy"] == "formula_embed"


def test_get_transform_params_limit_uses_table_to_text(store):
    params = store.get_transform_params("limit")
    assert params["strategy"] == "table_to_text"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node.py -v
```

期望：大量 `FAILED` — JSON 结构仍是旧的 `content_types` 数组，无 `structure_types`

- [ ] **Step 3: 重写 `content_type_rules.json`**

```json
{
  "confidence_threshold": 0.7,
  "structure_types": [
    {
      "id": "paragraph",
      "description": "叙述性段落，连续文字说明",
      "examples": ["本标准适用于...", "本方法按照..."]
    },
    {
      "id": "list",
      "description": "编号或条目列表，包含 GB 标准中的条款项或操作步骤",
      "examples": ["A.3.1.1 异丙醇溶液：60%", "——增加了酸不溶物指标"]
    },
    {
      "id": "table",
      "description": "表格数据，HTML <table> 或 Markdown | 格式",
      "examples": ["表1 感官要求", "表2 理化指标"]
    },
    {
      "id": "formula",
      "description": "数学或化学公式，含 LaTeX 语法",
      "examples": ["$$w_1 = \\frac{m_1 - m_0}{m} \\times 100\\%$$"]
    },
    {
      "id": "header",
      "description": "纯章节标题，无实质内容",
      "examples": ["## 2 技术要求（后无内容）", "# 附录 A 检验方法（后无内容）"]
    }
  ],
  "semantic_types": [
    {
      "id": "metadata",
      "description": "文档身份信息：标准号、发布机构、发布/实施日期",
      "examples": ["GB 1886.169—2016", "2016-08-31 发布", "2017-01-01 实施"]
    },
    {
      "id": "scope",
      "description": "标准的适用范围与对象",
      "examples": ["1 范围", "本标准适用于以红藻类植物为原料..."]
    },
    {
      "id": "limit",
      "description": "技术指标、限量值或感官/微生物要求",
      "examples": ["感官要求", "理化指标", "微生物指标", "铅(Pb)/(mg/kg) ≤ 5.0"]
    },
    {
      "id": "procedure",
      "description": "操作步骤或测定方法的具体过程",
      "examples": ["分析步骤", "A.3.3 分析步骤", "称取试样...置于..."]
    },
    {
      "id": "material",
      "description": "操作前需要准备的试剂或仪器设备",
      "examples": ["试剂和材料", "仪器和设备", "A.9.1 试剂和材料", "A.3.2 仪器和设备"]
    },
    {
      "id": "calculation",
      "description": "计算公式及其变量说明，用于从测量值推导结果",
      "examples": ["结果计算", "A.3.4 结果计算", "式中 m1——坩埚加残渣质量"]
    },
    {
      "id": "definition",
      "description": "术语、概念或常数的定义",
      "examples": ["术语和定义", "卡拉胶是指..."]
    },
    {
      "id": "amendment",
      "description": "对原标准的修改记录",
      "examples": ["第1号修改单", "将'...'修改为'...'"]
    }
  ],
  "transform": {
    "by_semantic_type": {
      "metadata":    { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "scope":       { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "limit":       { "strategy": "table_to_text", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "procedure":   { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "material":    { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "calculation": { "strategy": "formula_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "definition":  { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "amendment":   { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" }
    }
  }
}
```

- [ ] **Step 4: 更新 `rules.py` — 仅改 `get_transform_params` 签名**

**只修改 `get_transform_params` 方法，其余方法（包括 `append_content_type`）一律不动。** `_PLAIN_EMBED_PARAMS` 已在类级别定义，无需移动。

将 `get_transform_params` 改为：

```python
def get_transform_params(self, semantic_type: str) -> dict:
    by_semantic = self._ct.get("transform", {}).get("by_semantic_type", {})
    return by_semantic.get(semantic_type, self._PLAIN_EMBED_PARAMS)
```

注意：`append_content_type` 写入旧格式的问题是已知技术债（见规格文档），本次**不修改**。

- [ ] **Step 5: 运行确认通过**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node.py -v
```

期望：`11 passed`

- [ ] **Step 6: 提交**

```bash
cd agent-server && git add \
  app/core/parser_workflow/rules/content_type_rules.json \
  app/core/parser_workflow/rules.py \
  tests/core/parser_workflow/test_classify_node.py
git commit -m "feat: rewrite content_type_rules.json to dual structure_types+semantic_types schema"
```

---

## Task 4: 更新 `classify_node.py` — prompt + 字段引用

**Files:**
- Modify: `app/core/parser_workflow/nodes/classify_node.py`
- Test: `tests/core/parser_workflow/test_classify_node_unit.py`（新建，mock LLM）

- [ ] **Step 1: 写失败的单元测试（mock LLM）**

```python
# tests/core/parser_workflow/test_classify_node_unit.py
from unittest.mock import patch
import pytest

from app.core.parser_workflow.models import RawChunk, WorkflowState
from app.core.parser_workflow.nodes.classify_node import classify_node
from app.core.parser_workflow.nodes.output import ClassifyOutput, SegmentItem


def _make_state(content: str, tmp_path) -> WorkflowState:
    from app.core.parser_workflow.rules import RulesStore
    store = RulesStore(str(tmp_path))
    return WorkflowState(
        md_content=content,
        doc_metadata={"standard_no": "TEST001"},
        config={},
        rules_dir=str(tmp_path),
        raw_chunks=[RawChunk(content=content, section_path=["A.3"], char_count=len(content))],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


def test_classify_node_produces_dual_type_segments(tmp_path):
    """classify_node 应产生含 structure_type + semantic_type 的 segments"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="称取试样约2g", structure_type="list", semantic_type="procedure", confidence=0.9),
    ])

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state("称取试样约2g", tmp_path)
        result = classify_node(state)

    chunks = result["classified_chunks"]
    assert chunks
    seg = chunks[0]["segments"][0]
    assert seg["structure_type"] == "list"
    assert seg["semantic_type"] == "procedure"
    assert "content_type" not in seg


def test_classify_node_low_confidence_sets_unknown(tmp_path):
    """置信度低于阈值时，两个字段均应为 'unknown'"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="某段内容", structure_type="paragraph", semantic_type="scope", confidence=0.3),
    ])

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state("某段内容", tmp_path)
        result = classify_node(state)

    seg = result["classified_chunks"][0]["segments"][0]
    assert seg["structure_type"] == "unknown"
    assert seg["semantic_type"] == "unknown"
    assert result["classified_chunks"][0]["has_unknown"] is True


def test_classify_node_prompt_includes_both_type_lists(tmp_path):
    """LLM 调用的 prompt 应包含 structure_types 和 semantic_types 两组描述"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="x", structure_type="paragraph", semantic_type="scope", confidence=0.9),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        state = _make_state("x", tmp_path)
        classify_node(state)

    assert captured_prompts
    prompt = captured_prompts[0]
    # prompt 应包含 structure_type 的所有 5 个 id
    for type_id in ["paragraph", "list", "table", "formula", "header"]:
        assert type_id in prompt, f"prompt 未包含 structure_type '{type_id}'"
    # prompt 应包含 semantic_type 的所有 8 个 id
    for type_id in ["metadata", "scope", "limit", "procedure", "material", "calculation", "definition", "amendment"]:
        assert type_id in prompt, f"prompt 未包含 semantic_type '{type_id}'"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node_unit.py -v
```

期望：`FAILED` — `seg` 中无 `structure_type` 字段（旧代码读 `item.content_type`）

- [ ] **Step 3: 重写 `classify_node.py`**

```python
# app/core/parser_workflow/nodes/classify_node.py
from __future__ import annotations

from typing import Dict, List

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.rules import RulesStore
from app.core.config import settings
from app.core.parser_workflow.structured_llm import invoke_structured
from app.core.parser_workflow.nodes.output import ClassifyOutput, SegmentItem


def _call_classify_llm(
    chunk_content: str,
    structure_types: List[Dict],
    semantic_types: List[Dict],
) -> List[SegmentItem]:
    """
    调用小模型对 chunk 做分段 + 双维度分类（单次调用，prompt 内两步推断）。
    """
    structure_desc = "\n".join(
        f"- {t['id']}: {t['description']}" for t in structure_types
    )
    semantic_desc = "\n".join(
        f"- {t['id']}: {t['description']}" for t in semantic_types
    )
    prompt = f"""请将以下文本拆分为语义独立的片段，并对每个片段进行双维度分类。

【结构类型（structure_type）】——描述内容的呈现形式：
{structure_desc}

【语义类型（semantic_type）】——描述内容对读者的用途：
{semantic_desc}

分类规则：
1. 保守切分：只在相邻内容属于明显不同语义单元时才切分；同一逻辑章节保持整体。
2. 对每个片段独立推断两个维度，互不干扰：先判断呈现形式（structure_type），再判断用途（semantic_type）。
3. confidence 反映你对两个判断综合的把握程度（0-1）。

文本内容：
{chunk_content}
"""
    result = invoke_structured(
        node_name="classify_node",
        prompt=prompt,
        response_model=ClassifyOutput,
        extra_body={"enable_thinking": False},
    )
    return result.segments


def classify_raw_chunk(
    raw_chunk: RawChunk,
    store: RulesStore,
) -> ClassifiedChunk:
    threshold = store.get_confidence_threshold(settings.CONFIDENCE_THRESHOLD)
    ct_rules = store.get_content_type_rules()
    structure_types = ct_rules.get("structure_types", [])
    semantic_types = ct_rules.get("semantic_types", [])

    llm_output = _call_classify_llm(raw_chunk["content"], structure_types, semantic_types)

    segments: List[TypedSegment] = []
    has_unknown = False
    for item in llm_output:
        confidence = item.confidence
        if confidence < threshold:
            seg = TypedSegment(
                content=item.content,
                structure_type="unknown",
                semantic_type="unknown",
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
            has_unknown = True
        else:
            transform_params = store.get_transform_params(item.semantic_type)
            seg = TypedSegment(
                content=item.content,
                structure_type=item.structure_type,
                semantic_type=item.semantic_type,
                transform_params=transform_params,
                confidence=confidence,
                escalated=False,
                cross_refs=[],
                ref_context="",
                failed_table_refs=[],
            )
        segments.append(seg)

    return ClassifiedChunk(
        raw_chunk=raw_chunk,
        segments=segments,
        has_unknown=has_unknown,
    )


def classify_node(state: WorkflowState) -> dict:
    store = RulesStore(state["rules_dir"])
    classified: List[ClassifiedChunk] = [
        classify_raw_chunk(chunk, store) for chunk in state["raw_chunks"]
    ]
    return {"classified_chunks": classified}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node_unit.py -v
```

期望：`3 passed`

- [ ] **Step 5: 提交**

```bash
cd agent-server && git add \
  app/core/parser_workflow/nodes/classify_node.py \
  tests/core/parser_workflow/test_classify_node_unit.py
git commit -m "feat: rewrite classify_node with dual structure_type+semantic_type prompt and field references"
```

---

## Task 5: 更新 `transform_node.py` — DocumentChunk 构造

**Files:**
- Modify: `app/core/parser_workflow/nodes/transform_node.py`
- Test: `tests/core/parser_workflow/test_transform_node_unit.py`（新建，mock LLM）

- [ ] **Step 1: 写失败测试**

```python
# tests/core/parser_workflow/test_transform_node_unit.py
from unittest.mock import patch

from app.core.parser_workflow.models import (
    ClassifiedChunk, RawChunk, TypedSegment, WorkflowState,
)
from app.core.parser_workflow.nodes.output import TransformOutput
from app.core.parser_workflow.nodes.transform_node import transform_node


def _make_state(structure_type: str, semantic_type: str) -> WorkflowState:
    seg = TypedSegment(
        content="称取试样",
        structure_type=structure_type,
        semantic_type=semantic_type,
        transform_params={"strategy": "plain_embed", "prompt_template": "请转化：\n"},
        confidence=0.9,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    raw_chunk = RawChunk(content="称取试样", section_path=["A.3"], char_count=5)
    classified = ClassifiedChunk(raw_chunk=raw_chunk, segments=[seg], has_unknown=False)
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "TEST001"},
        config={},
        rules_dir="",
        raw_chunks=[raw_chunk],
        classified_chunks=[classified],
        final_chunks=[],
        errors=[],
    )


def test_transform_node_output_chunk_has_dual_type_fields():
    """transform_node 产出的 DocumentChunk 应包含 structure_type + semantic_type"""
    mock_resp = TransformOutput(content="规范化文本")
    with patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="规范化文本",
    ):
        result = transform_node(_make_state("list", "procedure"))

    chunks = result["final_chunks"]
    assert chunks
    chunk = chunks[0]
    assert chunk["structure_type"] == "list"
    assert chunk["semantic_type"] == "procedure"
    assert "content_type" not in chunk
```

- [ ] **Step 2: 运行确认失败**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_transform_node_unit.py -v
```

期望：`FAILED` — `DocumentChunk` 构造使用了 `content_type=` 关键字（Task 2 已删除该字段）

- [ ] **Step 3: 修改 `transform_node.py`**

将 `apply_strategy` 函数替换为完整实现（只改 `DocumentChunk` 的 `content_type=` 为双字段，其余不变）：

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
        failed_table_refs = seg.get("failed_table_refs", [])

        llm_text = _call_llm_transform(seg["content"], seg["transform_params"], ref_context)

        results.append(
            DocumentChunk(
                chunk_id=make_chunk_id(
                    doc_metadata.get("standard_no", ""),
                    raw_chunk["section_path"],
                    llm_text,
                ),
                doc_metadata=doc_metadata,
                section_path=raw_chunk["section_path"],
                structure_type=seg["structure_type"],
                semantic_type=seg["semantic_type"],
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

- [ ] **Step 4: 运行确认通过**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_transform_node_unit.py -v
```

期望：`1 passed`

- [ ] **Step 5: 提交**

```bash
cd agent-server && git add \
  app/core/parser_workflow/nodes/transform_node.py \
  tests/core/parser_workflow/test_transform_node_unit.py
git commit -m "feat: update transform_node to write structure_type+semantic_type into DocumentChunk"
```

---

## Task 6: 标记 `document_chunk.py` ContentType 枚举为 DEPRECATED

**Files:**
- Modify: `app/core/document_chunk.py`

- [ ] **Step 1: 在 ContentType 枚举上方添加注释**

在 `class ContentType(Enum):` 前插入：

```python
# DEPRECATED: 此枚举属于旧版 kb/strategy 流水线，不再用于 parser_workflow。
# parser_workflow 改用 models.py 中 TypedSegment/DocumentChunk 的
# structure_type + semantic_type 双字段体系。待 kb/strategy 重构时一并清理。
```

- [ ] **Step 2: 验证旧代码仍能运行（枚举未被删除）**

```bash
cd agent-server && uv run python -c "from app.core.document_chunk import ContentType; print('OK:', list(ContentType)[:3])"
```

期望：打印 `OK:` 加前几个枚举值，无报错

- [ ] **Step 3: 提交**

```bash
cd agent-server && git add app/core/document_chunk.py
git commit -m "chore: mark ContentType enum as deprecated in document_chunk.py"
```

---

## Task 7: 更新 `test_classify_node_real_llm.py` 断言

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node_real_llm.py`

- [ ] **Step 1: 更新字段断言**

在 `test_classify_node_returns_structured_segments_with_real_llm_and_rules` 中，将：

```python
logger.info(
    "segment[%d.%d]: type=%s, confidence=%s, content_preview=%r",
    idx, s_idx,
    seg.get("content_type"),
    ...
)
assert "content_type" in seg
```

改为：

```python
logger.info(
    "segment[%d.%d]: structure=%s semantic=%s confidence=%s content_preview=%r",
    idx, s_idx,
    seg.get("structure_type"),
    seg.get("semantic_type"),
    seg.get("confidence"),
    (seg.get("content") or "")[:60],
)
assert "structure_type" in seg, "segment 应包含 structure_type"
assert "semantic_type" in seg, "segment 应包含 semantic_type"
assert seg["structure_type"] in {
    "paragraph", "list", "table", "formula", "header", "unknown"
}, f"非法 structure_type：{seg['structure_type']!r}"
assert seg["semantic_type"] in {
    "metadata", "scope", "limit", "procedure",
    "material", "calculation", "definition", "amendment", "unknown"
}, f"非法 semantic_type：{seg['semantic_type']!r}"
```

在 `test_classify_node_handles_mixed_quotes_revision_chunk` 末尾（第 181 行之后）也加上：

```python
for cc in classified_chunks:
    for seg in cc["segments"]:
        assert "structure_type" in seg
        assert "semantic_type" in seg
```

- [ ] **Step 2: 运行（不调用真实 LLM，仅检查语法正确）**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_classify_node_real_llm.py --collect-only
```

期望：2 个测试被收集，无 import 错误

- [ ] **Step 3: 提交**

```bash
cd agent-server && git add tests/core/parser_workflow/test_classify_node_real_llm.py
git commit -m "test: update real_llm test assertions to check structure_type+semantic_type"
```

---

## Task 8: 运行全量单元测试，确认无回归

- [ ] **Step 1: 运行所有非 real_llm 测试**

```bash
cd agent-server && uv run pytest tests/ -v -m "not real_llm"
```

期望：全部通过，无任何 `content_type` 相关报错

- [ ] **Step 2: 如有失败，定位并修复**

常见原因：
- 其他 test 文件仍引用 `content_type` 字段 → 同步更新断言
- `escalate_node` 引用了 `seg["content_type"]` → 该节点不在本次范围，但若测试失败则需修改断言（不改实现）

- [ ] **Step 3: 提交（如有修复）**

```bash
cd agent-server && git add -p && git commit -m "fix: update remaining content_type references in tests"
```
