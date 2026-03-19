# Preface Classify Optimization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 classify_node 将 GB 标准"前言"章节整体识别为 `preface` 类型的单一 segment，而非拆成多个碎片。

**Architecture:** 三步：① 修复并扩展 `content_type_rules.json`（修复 `standard_header` 损坏 + 新增 `preface`）；② 修改 `classify_node.py` 的 prompt 加入保守切分原则；③ 更新集成测试验证前言 chunk 的实际 LLM 输出。前两步均先写失败的单元测试（mock LLM），再修改实现，再验证通过。

**Tech Stack:** Python 3.12, pytest, unittest.mock, `app.core.parser_workflow.rules.RulesStore`, `app.core.parser_workflow.nodes.classify_node._call_classify_llm`

**Spec:** `docs/superpowers/specs/2026-03-16-preface-classify-design.md`

---

## Chunk 1: 修复 content_type_rules.json 并新增 preface 类型

### Task 1: 为 JSON 规则写失败的单元测试

**Files:**
- Create: `tests/core/parser_workflow/test_classify_node.py`

- [ ] **Step 1: 写失败的测试**

新建文件 `tests/core/parser_workflow/test_classify_node.py`，内容如下：

```python
from __future__ import annotations

import pytest

from app.core.parser_workflow.rules import RulesStore, RULES_DIR


@pytest.fixture
def store(tmp_path):
    """使用默认规则初始化 RulesStore（复制到 tmp_path 以避免污染）"""
    return RulesStore(str(tmp_path))


# ── standard_header 规则 ──────────────────────────────────────────────


def test_standard_header_description_excludes_preface(store):
    """standard_header 的 description 不应包含"前言"字样"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    assert "standard_header" in ct_map
    desc = ct_map["standard_header"]["description"]
    assert "前言" not in desc, f"standard_header description 不应含'前言'，实际：{desc!r}"


def test_standard_header_has_no_action_field(store):
    """standard_header 条目不应有多余的 action 字段"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    assert "action" not in ct_map["standard_header"], "standard_header 不应有 action 字段"


def test_standard_header_prompt_template_is_complete(store):
    """standard_header 的 prompt_template 不应是截断的字符串"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    pt = ct_map["standard_header"]["transform"]["prompt_template"]
    # 合法的 prompt_template 应以换行符结束（约定）
    assert pt.endswith("\n"), f"prompt_template 疑似截断，结尾：{pt[-20:]!r}"


# ── preface 规则 ──────────────────────────────────────────────────────


def test_preface_content_type_exists(store):
    """content_type_rules.json 中应存在 preface 类型"""
    rules = store.get_content_type_rules()
    ids = [ct["id"] for ct in rules["content_types"]]
    assert "preface" in ids, f"未找到 preface 类型，现有：{ids}"


def test_preface_transform_params_use_plain_embed(store):
    """preface 的 transform strategy 应为 plain_embed"""
    params = store.get_transform_params("preface")
    assert params["strategy"] == "plain_embed", f"实际 strategy：{params['strategy']!r}"


def test_preface_description_mentions_no_split(store):
    """preface 的 description 应说明内部列表不拆分"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    desc = ct_map["preface"]["description"]
    assert "不拆分" in desc, f"description 未说明不拆分，实际：{desc!r}"
```

- [ ] **Step 2: 运行测试，确认全部未通过**

```bash
cd /Users/wwj/Desktop/self/life-classics/agent-server
pytest tests/core/parser_workflow/test_classify_node.py -v
```

预期输出：5 个 ERROR 或 FAILED。当前生产 JSON 存在截断（`json.loads` 抛异常），`RulesStore` 初始化会失败，表现为 fixture ERROR——这与 FAILED 同样表示"测试未通过"，是 TDD 的合法失败状态，可继续下一步。

---

### Task 2: 修复 content_type_rules.json

**Files:**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`

- [ ] **Step 3: 修复文件**

将 `app/core/parser_workflow/rules/content_type_rules.json` 完整替换为：

```json
{
  "version": "1.0",
  "confidence_threshold": 0.7,
  "content_types": [
    {
      "id": "table",
      "description": "表格数据（支持 Markdown | 或 HTML <table> 格式）",
      "transform": {
        "strategy": "split_rows",
        "prompt_template": "请将以下表格（Markdown 或 HTML 格式）的每一行内容转化为规范化的陈述句。要求：\n1. 严格保持原始数据一致性，不得修改、添加或删除表格中的任何数值、术语或具体信息。\n2. 将每一行数据（Row）与其对应的表头（Header）一一对应，组合成独立的完整句子。\n3. 去除表格格式符（如 |、--、<tr>、<td> 等），仅输出纯文本陈述。\n4. 禁止进行任何总结、评价或对原文含义的扩充。\n\n待处理表格内容：\n"
      }
    },
    {
      "id": "formula",
      "description": "数学或化学公式，含 LaTeX 语法或化学分子式",
      "transform": {
        "strategy": "augment_description",
        "prompt_template": "请将以下 LaTeX 或化学公式转化为规范化的专业文本描述。要求：\n1. 严禁修改任何数值、符号、下标或变量名称。\n2. 用文字准确解说公式的逻辑含义（例如：'A等于B乘以C' 或 '某化学物质与某物质反应生成...'）。\n3. 保留原始 LaTeX 代码并在其后附加该逻辑说明，确保检索时能匹配到变量名或物理意义。\n4. 禁止进行任何计算或推导。\n\n待处理公式内容：\n"
      }
    },
    {
      "id": "numbered_list",
      "description": "有序编号列表，包含 GB 标准中的章、节、条、款、项或操作步骤",
      "transform": {
        "strategy": "flatten_with_context",
        "prompt_template": "请将以下有序编号列表转化为规范化的完整陈述句。要求：\n1. 严格保持原始编号（如 1., a), 1.1 等）和内容，不得修改或删减任何文字。\n2. 如果列表存在层级，请将上级标题或前置步骤的核心语义整合进每一项中，确保每条信息独立存在时依然语义完整。\n3. 禁止对条款内容进行总结、缩减或改变语序。\n4. 去除多余的换行符，确保每一条规则或步骤输出为一行标准文本。\n\n待处理列表内容：\n"
      }
    },
    {
      "id": "plain_text",
      "description": "普通说明性段落，包括定义、范围说明或通用技术要求",
      "transform": {
        "strategy": "semantic_standardization",
        "prompt_template": "请将以下说明性段落转化为规范化的陈述文本。要求：\n1. 严格保留所有数值、技术参数、术语及核心语义，严禁随意修改或删减原文关键信息。\n2. 消除模糊指代：将文中的"本标准"、"本章"、"上述"、"该"等代词明确替换为其实际指向的主体（如根据上下文补充具体标准号或章节名）。\n3. 保持客观中性，去除无实际意义的修饰词，确保输出为一段完整且自包含的专业陈述。\n4. 禁止对内容进行概括或重组，必须维持原文的逻辑深度。\n\n待处理段落内容：\n"
      }
    },
    {
      "id": "standard_header",
      "description": "标准文档头部元信息（标准号、发布机构、实施日期等），不含前言章节内容",
      "transform": {
        "strategy": "metadata_standardization",
        "prompt_template": "请将以下标准文档头部信息转化为规范化的元数据陈述。要求：\n1. 准确识别并保留标准全称、标准号、发布及实施日期，保持格式统一。\n2. 明确解析版本替代关系（如有）。\n3. 禁止添加不存在于原文的推断内容。\n\n待处理内容：\n"
      }
    },
    {
      "id": "preface",
      "description": "标准前言，包含版本代替关系及主要修订说明，整体作为一个语义单元，内部列表项不拆分",
      "transform": {
        "strategy": "plain_embed",
        "prompt_template": "请将以下标准前言内容转化为规范化的版本元数据陈述，保留所有版本号、代替关系及修订说明条目：\n"
      }
    }
  ]
}
```

- [ ] **Step 4: 运行测试，确认全部通过**

```bash
pytest tests/core/parser_workflow/test_classify_node.py -v
```

预期输出：5 个 PASSED

- [ ] **Step 5: 运行全量测试，确认无回归**

```bash
pytest tests/ -v --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_parse_node_real.py \
  --ignore=tests/core/parser_workflow/test_slice_node_real.py
```

预期：全部 PASSED，无 FAILED

- [ ] **Step 6: 提交**

```bash
git add app/core/parser_workflow/rules/content_type_rules.json \
        tests/core/parser_workflow/test_classify_node.py
git commit -m "feat: fix standard_header json and add preface content type"
```

---

## Chunk 2: 修改 classify prompt 加入保守切分原则

### Task 3: 为 prompt 内容写失败的单元测试

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node.py`

- [ ] **Step 1: 追加 prompt 相关测试**

在 `tests/core/parser_workflow/test_classify_node.py` 末尾追加：

```python
from unittest.mock import MagicMock, patch

from app.core.parser_workflow.nodes.classify_node import _call_classify_llm


# ── classify prompt 内容 ──────────────────────────────────────────────


def _captured_prompt(content: str, content_types: list) -> str:
    """调用 _call_classify_llm 并捕获传给 chat.invoke 的 prompt 字符串"""
    mock_result = MagicMock()
    mock_result.segments = []

    with patch(
        "app.core.parser_workflow.nodes.classify_node.create_chat_model"
    ) as mock_factory, patch(
        "app.core.parser_workflow.nodes.classify_node.resolve_provider",
        return_value="openai",
    ), patch(
        "app.core.parser_workflow.nodes.classify_node.settings"
    ) as mock_settings:
        mock_settings.CLASSIFY_LLM_PROVIDER = "dashscope"
        mock_settings.CLASSIFY_MODEL = "qwen-plus"
        mock_chat = MagicMock()
        mock_chat.invoke.return_value = mock_result
        mock_factory.return_value = mock_chat

        _call_classify_llm(content, content_types)

    # call_args[0][0] 取第一个位置参数，即 prompt 字符串
    return mock_chat.invoke.call_args[0][0]


def test_classify_prompt_contains_conservative_rule():
    """prompt 应包含保守切分原则说明"""
    prompt = _captured_prompt("任意文本", [{"id": "plain_text", "description": "普通文本"}])
    assert "保守切分" in prompt, "prompt 应包含'保守切分'关键词"


def test_classify_prompt_mentions_preface_type():
    """prompt 应明确提及 preface 类型，引导 LLM 对前言整体归类"""
    prompt = _captured_prompt("任意文本", [{"id": "plain_text", "description": "普通文本"}])
    assert "preface" in prompt, "prompt 应包含'preface'关键词"


def test_classify_prompt_contains_few_shot_example():
    """prompt 应包含前言处理的 few-shot 示例"""
    prompt = _captured_prompt("任意文本", [{"id": "plain_text", "description": "普通文本"}])
    assert "前言" in prompt and "示例" in prompt, "prompt 应包含前言相关的示例说明"
```

- [ ] **Step 2: 运行新增测试，确认失败**

```bash
pytest tests/core/parser_workflow/test_classify_node.py::test_classify_prompt_contains_conservative_rule \
       tests/core/parser_workflow/test_classify_node.py::test_classify_prompt_mentions_preface_type \
       tests/core/parser_workflow/test_classify_node.py::test_classify_prompt_contains_few_shot_example \
       -v
```

预期：3 个 FAILED（prompt 中尚无这些内容）

---

### Task 4: 修改 classify_node.py 的 prompt

**Files:**
- Modify: `app/core/parser_workflow/nodes/classify_node.py`

- [ ] **Step 3: 更新 prompt**

> 注意：只替换 `prompt = f"""..."""` 变量赋值部分。`format_example` 变量定义（第 30-38 行）和函数其他部分保持不变。

将 `_call_classify_llm` 中的 `prompt` 变量替换为：

```python
    prompt = f"""请将以下文本拆分为语义独立的片段，并分析每个片段的 content_type 和置信度（0-1）。

可用的 content_type：
{type_descriptions}

保守切分原则：
1. 只在相邻内容属于明显不同的 content_type 时才切分；同一逻辑章节的内容应保持整体。
2. 标准前言（以"前言"为标题的章节）整体归为 preface 类型，内部变更条目列表（如"——增加了..."）不单独拆分。

示例（前言章节的正确处理方式）：
输入：包含前言标题、版本代替声明和多条变更条目的文本块
正确输出：1 个 segment，content_type=preface，包含完整前言文本
错误输出：多个 segment，将各变更条目拆分为独立的 numbered_list

文本内容：
{chunk_content}

返回格式（json）：
{format_example}
"""
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/core/parser_workflow/test_classify_node.py -v
```

预期：全部 8 个 PASSED

- [ ] **Step 5: 提交**

```bash
git add app/core/parser_workflow/nodes/classify_node.py \
        tests/core/parser_workflow/test_classify_node.py
git commit -m "feat: add conservative splitting rules to classify prompt"
```

---

## Chunk 3: 更新集成测试验证前言 chunk

### Task 5: 更新 test_classify_node_real_llm.py

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node_real_llm.py`

> 注意：此任务使用真实 LLM API，运行耗时约 2 分钟，需要 `LLM_API_KEY` 环境变量（由 `ensure_llm_api_key()` 检查）。

> 背景：GB 标准"前言"是一个有标题的正式章节，`slice_node` 将其切分为 `section_path == ["前言"]` 的 RawChunk，而非 `__preamble__`（`__preamble__` 指第一个顶级标题前的无标题内容，该文档首行即为一级标题，故不存在）。

- [ ] **Step 1: 重写测试文件**

将 `tests/core/parser_workflow/test_classify_node_real_llm.py` 完整替换为：

```python
from typing import List

import pytest

from app.core.parser_workflow.models import ClassifiedChunk, RawChunk, WorkflowState
from app.core.parser_workflow.nodes.classify_node import classify_node
from app.core.parser_workflow.nodes.parse_node import parse_node
from app.core.parser_workflow.nodes.slice_node import slice_node
from .test_utils import ensure_llm_api_key, get_logger, get_rules_dir, load_sample_markdown

logger = get_logger("classify_node_real_llm")


@pytest.fixture(autouse=True)
def _ensure_llm_key():
    ensure_llm_api_key()


def _build_state_with_preface_chunk() -> WorkflowState:
    """构建只包含前言章节 chunk（section_path == ["前言"]）的 WorkflowState"""
    md_content, _ = load_sample_markdown()
    rules_dir = get_rules_dir()

    initial_state = WorkflowState(
        md_content=md_content,
        doc_metadata={"standard_no": "GB1886.47-2016"},
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )

    parsed = parse_node(initial_state)
    sliced = slice_node(
        WorkflowState(
            md_content=md_content,
            doc_metadata=parsed["doc_metadata"],
            config={},
            rules_dir=str(rules_dir),
            raw_chunks=[],
            classified_chunks=[],
            final_chunks=[],
            errors=parsed["errors"],
        )
    )

    raw_chunks: List[RawChunk] = sliced["raw_chunks"]

    # "前言"是有标题的正式章节，section_path == ["前言"]
    # 注意：__preamble__ 指第一个顶级标题前的无标题内容，该文档首行即为一级标题，故不存在
    preface_chunks = [
        c for c in raw_chunks if c["section_path"] == ["前言"]
    ]
    assert preface_chunks, (
        "sample markdown 中未找到 section_path == ['前言'] 的 chunk，"
        f"现有 section_path：{[c['section_path'] for c in raw_chunks]}"
    )

    logger.info(
        "prepared preface chunk; content_preview=%r",
        preface_chunks[0]["content"][:80],
    )

    return WorkflowState(
        md_content=md_content,
        doc_metadata=parsed["doc_metadata"],
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=preface_chunks,
        classified_chunks=[],
        final_chunks=[],
        errors=parsed["errors"],
    )


def test_classify_node_returns_structured_segments_with_real_llm_and_rules():
    """
    通用结构验证：classify_node 能输出结构化 segments，包含必要字段。
    """
    state = _build_state_with_preface_chunk()
    result = classify_node(state)
    classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

    assert classified_chunks, "classify_node 应该返回至少一个 ClassifiedChunk"

    for idx, cc in enumerate(classified_chunks):
        segments = cc["segments"]
        logger.info(
            "classified_chunk[%d]: has_unknown=%s, segments=%d",
            idx, cc["has_unknown"], len(segments),
        )
        assert segments, "每个 ClassifiedChunk 至少应包含一个 segment"
        for s_idx, seg in enumerate(segments):
            logger.info(
                "segment[%d.%d]: type=%s, confidence=%s, content_preview=%r",
                idx, s_idx,
                seg.get("content_type"),
                seg.get("confidence"),
                (seg.get("content") or "")[:60],
            )
            assert seg.get("content"), "segment 应该包含 content"
            assert "content_type" in seg
            assert "confidence" in seg


def test_classify_preface_chunk_as_single_preface_segment():
    """
    核心验证：前言 chunk 应整体分类为 1 个 preface segment，不拆分内部列表项。
    """
    state = _build_state_with_preface_chunk()
    result = classify_node(state)
    classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

    assert len(classified_chunks) == 1
    cc = classified_chunks[0]
    segments = cc["segments"]

    logger.info(
        "preface chunk: segments=%d, types=%s",
        len(segments),
        [s.get("content_type") for s in segments],
    )

    assert len(segments) == 1, (
        f"前言 chunk 应产生 1 个 segment，实际 {len(segments)} 个："
        f"{[s.get('content_type') for s in segments]}"
    )
    assert segments[0]["content_type"] == "preface", (
        f"前言 segment 的 content_type 应为 'preface'，实际：{segments[0]['content_type']!r}"
    )
```

- [ ] **Step 2: 运行集成测试（需要真实 API key）**

```bash
pytest tests/core/parser_workflow/test_classify_node_real_llm.py -v -s
```

预期：2 个 PASSED，前言 chunk 输出 1 个 `preface` segment

- [ ] **Step 3: 提交**

```bash
git add tests/core/parser_workflow/test_classify_node_real_llm.py
git commit -m "test: update classify integration test to assert preface as single segment"
```

---

## 执行顺序总结

| Chunk | Tasks | 是否需要 LLM API |
|-------|-------|-----------------|
| Chunk 1 | Task 1-2 | 否 |
| Chunk 2 | Task 3-4 | 否 |
| Chunk 3 | Task 5 | 是（DASHSCOPE_API_KEY）|
