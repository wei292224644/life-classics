# GB 国家标准解析 Workflow 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建独立的 LangGraph Workflow，将 MinerU 输出的 Markdown 文件解析为结构化 `List[DocumentChunk]`，供外部写入知识库。

**Architecture:** 6 个 LangGraph 节点顺序执行：parse → structure（规则推断 doc_type，LLM 兜底）→ slice（纯规则递归切分）→ classify（小模型分段+分类）→ escalate（大模型处理 unknown，可选）→ transform（按策略转化输出）。规则以外部 JSON 文件管理，运行时动态加载，新规则自动追加。

**Tech Stack:** Python 3.12+, langgraph>=1.1.0, langchain>=1.2.0, langchain-openai>=1.1.3, pytest

**Spec:** `docs/superpowers/specs/2026-03-13-gb-standard-parser-workflow-design.md`

---

## 文件结构

```
agent-server/
├── app/core/parser_workflow/
│   ├── __init__.py                   # 导出 run_parser_workflow, ParserResult
│   ├── models.py                     # 所有 TypedDict：WorkflowState, RawChunk, TypedSegment,
│   │                                 #   ClassifiedChunk, DocumentChunk, ParserResult
│   ├── config.py                     # ParserConfig TypedDict + 默认值常量
│   ├── rules.py                      # RulesStore：加载/追加 doc_type 和 content_type 规则
│   ├── default_rules/
│   │   ├── doc_type_rules.json       # 内置默认文档类型规则
│   │   └── content_type_rules.json   # 内置默认内容类型规则
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── parse_node.py             # 验证并规范化 doc_metadata
│   │   ├── structure_node.py         # 提取标题 + 规则推断 doc_type + LLM 兜底
│   │   ├── slice_node.py             # 递归标题切分 + SOFT/HARD_MAX
│   │   ├── classify_node.py          # 小模型同时分段+分类
│   │   ├── escalate_node.py          # 大模型处理 unknown + 回写状态 + 追加规则
│   │   └── transform_node.py         # 按 strategy 转化，输出 List[DocumentChunk]
│   └── graph.py                      # StateGraph 装配 + run_parser_workflow 入口
└── tests/core/parser_workflow/
    ├── __init__.py
    ├── test_models.py                # make_chunk_id 生成规则
    ├── test_rules.py                 # RulesStore 加载/追加/自动初始化
    ├── test_parse_node.py            # metadata 验证与规范化
    ├── test_structure_node.py        # 规则匹配评分、LLM 兜底（mock）
    ├── test_slice_node.py            # 前言、SOFT_MAX、HARD_MAX、递归、无标题
    ├── test_transform_node.py        # split_rows、preserve_as_is、plain_embed
    ├── test_classify_node.py         # LLM 分段分类（mock）、has_unknown 检测
    ├── test_escalate_node.py         # LLM 推断、状态回写、规则追加（mock）
    ├── test_graph.py                 # _should_escalate 路由、图装配
    └── test_workflow.py              # 端到端集成（全 mock LLM）
```

---

## Chunk 1：数据结构与规则系统

### Task 1：核心数据结构（models.py + config.py）

**Files:**
- Create: `app/core/parser_workflow/models.py`
- Create: `app/core/parser_workflow/config.py`
- Create: `tests/core/parser_workflow/__init__.py`
- Create: `tests/core/parser_workflow/test_models.py`

- [ ] **Step 1：写测试**

`tests/core/parser_workflow/test_models.py`:
```python
from app.core.parser_workflow.models import make_chunk_id


def test_chunk_id_is_16_hex_chars():
    cid = make_chunk_id("GB2760", ["3 范围"], "本标准规定食品添加剂的使用。")
    assert len(cid) == 16
    assert all(c in "0123456789abcdef" for c in cid)  # 必须是合法十六进制字符


def test_chunk_id_same_input_same_output():
    a = make_chunk_id("GB2760", ["3 范围"], "内容")
    b = make_chunk_id("GB2760", ["3 范围"], "内容")
    assert a == b


def test_chunk_id_different_content_different_id():
    a = make_chunk_id("GB2760", ["3 范围"], "内容A")
    b = make_chunk_id("GB2760", ["3 范围"], "内容B")
    assert a != b


def test_chunk_id_different_section_different_id():
    a = make_chunk_id("GB2760", ["3 范围"], "内容")
    b = make_chunk_id("GB2760", ["4 定义"], "内容")
    assert a != b
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_models.py -v
```
预期：`ModuleNotFoundError: No module named 'app.core.parser_workflow'`

- [ ] **Step 3：创建目录和文件**

`app/core/parser_workflow/__init__.py`（空文件）
`app/core/parser_workflow/nodes/__init__.py`（空文件）
`tests/core/parser_workflow/__init__.py`（空文件）

`app/core/parser_workflow/models.py`:
```python
from __future__ import annotations
import hashlib
from typing import List, Optional
from typing_extensions import TypedDict


class RawChunk(TypedDict):
    content: str
    section_path: List[str]   # 如 ["3 范围", "3.1 适用范围"]
    char_count: int


class TypedSegment(TypedDict):
    content: str
    content_type: str         # "table" / "formula" / "plain_text" / ...
    transform_params: dict    # 来自 content_type_rules.json
    confidence: float
    escalated: bool           # escalate_node 处理后置 True


class ClassifiedChunk(TypedDict):
    raw_chunk: RawChunk
    segments: List[TypedSegment]
    has_unknown: bool


class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    content_type: str
    content: str
    raw_content: str
    meta: dict


class ParserResult(TypedDict):
    chunks: List[DocumentChunk]
    doc_metadata: dict
    errors: List[str]
    stats: dict


class WorkflowState(TypedDict):
    md_content: str
    doc_metadata: dict
    config: dict              # ParserConfig（TypedDict 不支持前向引用，用 dict）
    rules_dir: str
    raw_chunks: List[RawChunk]
    classified_chunks: List[ClassifiedChunk]
    final_chunks: List[DocumentChunk]
    errors: List[str]


def make_chunk_id(standard_no: str, section_path: List[str], content: str) -> str:
    key = f"{standard_no}|{'|'.join(section_path)}|{content[:100]}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
```

`app/core/parser_workflow/config.py`:
```python
from typing import List, Optional
from typing_extensions import TypedDict

CHUNK_SOFT_MAX_DEFAULT = 1500
CHUNK_HARD_MAX_DEFAULT = 3000
SLICE_HEADING_LEVELS_DEFAULT = [2, 3, 4]


class ParserConfig(TypedDict, total=False):
    chunk_soft_max: int
    chunk_hard_max: int
    slice_heading_levels: List[int]
    classify_model: str
    escalate_model: str
    doc_type_llm_model: str
    llm_api_key: str
    llm_base_url: str
    confidence_threshold: float


def get_config_value(config: dict, key: str, default):
    return config.get(key, default)
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_models.py -v
```
预期：4 个测试全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add app/core/parser_workflow/ tests/core/parser_workflow/
git commit -m "feat(parser-workflow): add core data models and config"
```

---

### Task 2：默认规则文件

**Files:**
- Create: `app/core/parser_workflow/default_rules/doc_type_rules.json`
- Create: `app/core/parser_workflow/default_rules/content_type_rules.json`

- [ ] **Step 1：创建 default_rules 目录和文件**

`app/core/parser_workflow/default_rules/doc_type_rules.json`:
```json
{
  "version": "1.0",
  "match_threshold": 2,
  "doc_types": [
    {
      "id": "single_additive",
      "description": "单一食品添加剂或产品标准，含技术要求和理化指标",
      "detect_keywords": ["技术要求", "理化指标", "鉴别", "含量"],
      "detect_heading_patterns": ["技术要求", "检验规则"],
      "source": "rule"
    },
    {
      "id": "detection_method",
      "description": "检测方法标准，含多种方法、试剂、仪器、操作步骤",
      "detect_keywords": ["方法一", "方法二", "试剂", "仪器", "操作步骤"],
      "detect_heading_patterns": ["试剂和材料", "仪器和设备", "分析步骤"],
      "source": "rule"
    },
    {
      "id": "microbiological",
      "description": "微生物检验标准，含培养基、流程图、判定规则",
      "detect_keywords": ["培养基", "菌落", "接种", "判定"],
      "detect_heading_patterns": ["培养基和试剂", "检验程序"],
      "source": "rule"
    }
  ]
}
```

`app/core/parser_workflow/default_rules/content_type_rules.json`:
```json
{
  "version": "1.0",
  "confidence_threshold": 0.7,
  "content_types": [
    {
      "id": "table",
      "description": "Markdown 表格，以 | 开头的连续行",
      "transform": {
        "strategy": "split_rows",
        "preserve_header": true
      }
    },
    {
      "id": "formula",
      "description": "数学或化学公式，含 LaTeX 语法或化学分子式",
      "transform": {
        "strategy": "preserve_as_is"
      }
    },
    {
      "id": "numbered_list",
      "description": "有序编号列表，步骤或条款",
      "transform": {
        "strategy": "preserve_as_list"
      }
    },
    {
      "id": "plain_text",
      "description": "普通说明性段落，无特殊结构",
      "transform": {
        "strategy": "plain_embed"
      }
    }
  ]
}
```

- [ ] **Step 2：校验 JSON 文件结构合法**

```bash
cd agent-server
python -c "
import json, pathlib
for fname in ['app/core/parser_workflow/default_rules/doc_type_rules.json',
              'app/core/parser_workflow/default_rules/content_type_rules.json']:
    data = json.loads(pathlib.Path(fname).read_text())
    assert 'version' in data, f'{fname} missing version'
print('JSON structure OK')
"
```
预期：`JSON structure OK`

- [ ] **Step 3：提交**

```bash
cd agent-server
git add app/core/parser_workflow/default_rules/
git commit -m "feat(parser-workflow): add default rules JSON files"
```

---

### Task 3：规则存储（rules.py）

**Files:**
- Create: `app/core/parser_workflow/rules.py`
- Create: `tests/core/parser_workflow/test_rules.py`

- [ ] **Step 1：写测试**

`tests/core/parser_workflow/test_rules.py`:
```python
import json
import os
import pytest
from app.core.parser_workflow.rules import RulesStore


@pytest.fixture
def rules_dir(tmp_path):
    return str(tmp_path)


def test_loads_defaults_when_files_missing(rules_dir):
    store = RulesStore(rules_dir)
    ct = store.get_content_type_rules()
    dt = store.get_doc_type_rules()
    assert len(ct["content_types"]) >= 4
    assert any(c["id"] == "table" for c in ct["content_types"])
    assert len(dt["doc_types"]) >= 3
    assert any(d["id"] == "single_additive" for d in dt["doc_types"])


def test_creates_files_on_disk_after_init(rules_dir):
    RulesStore(rules_dir)
    assert os.path.exists(os.path.join(rules_dir, "content_type_rules.json"))
    assert os.path.exists(os.path.join(rules_dir, "doc_type_rules.json"))


def test_append_new_content_type(rules_dir):
    store = RulesStore(rules_dir)
    new_type = {
        "id": "image_caption",
        "description": "图片说明文字",
        "transform": {"strategy": "preserve_as_is"}
    }
    store.append_content_type(new_type)
    # 重新加载验证持久化
    store2 = RulesStore(rules_dir)
    ids = [c["id"] for c in store2.get_content_type_rules()["content_types"]]
    assert "image_caption" in ids


def test_append_new_doc_type(rules_dir):
    store = RulesStore(rules_dir)
    new_doc = {
        "id": "safety_assessment",
        "description": "食品安全风险评估报告",
        "detect_keywords": ["风险评估", "暴露量"],
        "detect_heading_patterns": ["风险特征描述"],
        "source": "llm"
    }
    store.append_doc_type(new_doc)
    store2 = RulesStore(rules_dir)
    ids = [d["id"] for d in store2.get_doc_type_rules()["doc_types"]]
    assert "safety_assessment" in ids


def test_reload_reflects_appended_rules(rules_dir):
    store = RulesStore(rules_dir)
    store.append_content_type({
        "id": "code_block",
        "description": "代码块",
        "transform": {"strategy": "preserve_as_is"}
    })
    store.reload()
    ids = [c["id"] for c in store.get_content_type_rules()["content_types"]]
    assert "code_block" in ids


def test_get_confidence_threshold_default(rules_dir):
    store = RulesStore(rules_dir)
    assert store.get_confidence_threshold() == 0.7


def test_get_transform_params_for_known_type(rules_dir):
    store = RulesStore(rules_dir)
    params = store.get_transform_params("table")
    assert params["strategy"] == "split_rows"


def test_get_transform_params_for_unknown_type_returns_plain(rules_dir):
    store = RulesStore(rules_dir)
    params = store.get_transform_params("nonexistent_type")
    assert params["strategy"] == "plain_embed"
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_rules.py -v
```
预期：`ModuleNotFoundError`

- [ ] **Step 3：实现 rules.py**

`app/core/parser_workflow/rules.py`:
```python
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict

_DEFAULT_RULES_DIR = Path(__file__).parent / "default_rules"


class RulesStore:
    """运行时动态加载的规则文件管理器。"""

    def __init__(self, rules_dir: str):
        self._dir = Path(rules_dir)
        self._ct_path = self._dir / "content_type_rules.json"
        self._dt_path = self._dir / "doc_type_rules.json"
        self._ct: Dict[str, Any] = {}
        self._dt: Dict[str, Any] = {}
        self._init_files()
        self.reload()

    # ── 初始化 ──────────────────────────────────────────────

    def _init_files(self) -> None:
        """文件不存在时从默认规则复制创建。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        for src_name, dst in [
            ("content_type_rules.json", self._ct_path),
            ("doc_type_rules.json", self._dt_path),
        ]:
            if not dst.exists():
                src = _DEFAULT_RULES_DIR / src_name
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    # ── 加载 ─────────────────────────────────────────────────

    def reload(self) -> None:
        """从磁盘重新加载规则（escalate_node 追加后调用）。"""
        self._ct = json.loads(self._ct_path.read_text(encoding="utf-8"))
        self._dt = json.loads(self._dt_path.read_text(encoding="utf-8"))

    # ── 读取 ─────────────────────────────────────────────────

    def get_content_type_rules(self) -> Dict[str, Any]:
        return self._ct

    def get_doc_type_rules(self) -> Dict[str, Any]:
        return self._dt

    def get_confidence_threshold(self, config_override: float | None = None) -> float:
        if config_override is not None:
            return config_override
        return self._ct.get("confidence_threshold", 0.7)

    def get_transform_params(self, content_type_id: str) -> dict:
        for ct in self._ct.get("content_types", []):
            if ct["id"] == content_type_id:
                return ct.get("transform", {"strategy": "plain_embed"})
        return {"strategy": "plain_embed"}

    # ── 追加 ─────────────────────────────────────────────────

    def append_content_type(self, new_entry: dict) -> None:
        """追加新 content_type，持久化后立即 reload。"""
        self._ct.setdefault("content_types", []).append(new_entry)
        self._ct_path.write_text(
            json.dumps(self._ct, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.reload()

    def append_doc_type(self, new_entry: dict) -> None:
        """追加新 doc_type，持久化后立即 reload。"""
        self._dt.setdefault("doc_types", []).append(new_entry)
        self._dt_path.write_text(
            json.dumps(self._dt, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.reload()
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_rules.py -v
```
预期：8 个测试全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add app/core/parser_workflow/rules.py tests/core/parser_workflow/test_rules.py
git commit -m "feat(parser-workflow): add RulesStore with auto-init and append"
```

---

## Chunk 2：纯规则节点（无 LLM）

### Task 4：parse_node

**Files:**
- Create: `app/core/parser_workflow/nodes/parse_node.py`
- Create: `tests/core/parser_workflow/test_parse_node.py`

- [ ] **Step 1：写测试**

`tests/core/parser_workflow/test_parse_node.py`:
```python
import pytest
from app.core.parser_workflow.nodes.parse_node import parse_node
from app.core.parser_workflow.models import WorkflowState


def _make_state(md: str, meta: dict) -> WorkflowState:
    return WorkflowState(
        md_content=md,
        doc_metadata=meta,
        config={},
        rules_dir="/tmp",
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


def test_passes_through_provided_metadata():
    state = _make_state("## 范围\n内容", {"standard_no": "GB2760", "title": "食品添加剂"})
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB2760"
    assert result["doc_metadata"]["title"] == "食品添加剂"


def test_extracts_title_from_first_heading_when_missing():
    state = _make_state("# GB 2760-2024 食品添加剂使用标准\n\n## 范围", {"standard_no": "GB2760"})
    result = parse_node(state)
    assert "GB 2760" in result["doc_metadata"]["title"]


def test_does_not_override_provided_title():
    state = _make_state("# 不同标题\n内容", {"standard_no": "GB2760", "title": "提供的标题"})
    result = parse_node(state)
    assert result["doc_metadata"]["title"] == "提供的标题"


def test_missing_standard_no_adds_error():
    state = _make_state("## 范围\n内容", {"title": "某标准"})
    result = parse_node(state)
    assert len(result["errors"]) > 0
    assert "standard_no" in result["errors"][0]


def test_md_content_preserved():
    md = "## 范围\n内容"
    state = _make_state(md, {"standard_no": "GB2760", "title": "t"})
    result = parse_node(state)
    assert result["md_content"] == md
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_parse_node.py -v
```

- [ ] **Step 3：实现 parse_node**

`app/core/parser_workflow/nodes/parse_node.py`:
```python
from __future__ import annotations
import re
from app.core.parser_workflow.models import WorkflowState


def parse_node(state: WorkflowState) -> dict:
    """验证并规范化 doc_metadata，从 MD 首行标题补全缺失的 title。"""
    meta = dict(state["doc_metadata"])
    errors = list(state.get("errors", []))

    # 若未提供 title，尝试从第一个 # 标题提取
    if not meta.get("title"):
        for line in state["md_content"].splitlines():
            if line.startswith("# "):
                meta["title"] = line[2:].strip()
                break

    # standard_no 必须存在
    if not meta.get("standard_no"):
        errors.append("ERROR: doc_metadata missing required field 'standard_no'")

    return {"doc_metadata": meta, "errors": errors}
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_parse_node.py -v
```
预期：5 个测试全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add app/core/parser_workflow/nodes/parse_node.py tests/core/parser_workflow/test_parse_node.py
git commit -m "feat(parser-workflow): add parse_node"
```

---

### Task 5：slice_node

**Files:**
- Create: `app/core/parser_workflow/nodes/slice_node.py`
- Create: `tests/core/parser_workflow/test_slice_node.py`

- [ ] **Step 1：写测试**

`tests/core/parser_workflow/test_slice_node.py`:
```python
import pytest
from app.core.parser_workflow.nodes.slice_node import slice_node, recursive_slice
from app.core.parser_workflow.models import WorkflowState


def _make_state(md: str, config: dict = None) -> WorkflowState:
    return WorkflowState(
        md_content=md,
        doc_metadata={"standard_no": "GB_TEST", "title": "测试标准"},
        config=config or {},
        rules_dir="/tmp",
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


def test_preamble_content_before_first_heading():
    md = "这是前言内容。\n\n## 范围\n\n本标准适用范围。"
    result = slice_node(_make_state(md))
    paths = [c["section_path"] for c in result["raw_chunks"]]
    assert ["__preamble__"] in paths


def test_preamble_not_created_when_no_leading_content():
    md = "## 范围\n\n本标准适用范围。"
    result = slice_node(_make_state(md))
    paths = [c["section_path"] for c in result["raw_chunks"]]
    assert ["__preamble__"] not in paths


def test_splits_on_level2_headings():
    md = "## 范围\n\n内容A。\n\n## 定义\n\n内容B。"
    result = slice_node(_make_state(md))
    section_titles = [c["section_path"][-1] for c in result["raw_chunks"]]
    assert "范围" in section_titles
    assert "定义" in section_titles


def test_recursive_split_when_exceeds_soft_max():
    # 一个 ## 块内有 ### 子块，整体超过 SOFT_MAX
    big_content = "x" * 100
    md = f"## 大章节\n\n### 子节A\n\n{big_content}\n\n### 子节B\n\n{big_content}"
    config = {"chunk_soft_max": 50, "chunk_hard_max": 500}
    result = slice_node(_make_state(md, config))
    section_titles = [c["section_path"][-1] for c in result["raw_chunks"]]
    assert "子节A" in section_titles
    assert "子节B" in section_titles


def test_keeps_chunk_when_no_more_headings_even_if_exceeds_hard_max():
    big_content = "x" * 200
    md = f"## 大章节\n\n{big_content}"
    config = {"chunk_soft_max": 50, "chunk_hard_max": 100}
    result = slice_node(_make_state(md, config))
    assert len(result["raw_chunks"]) >= 1
    # 超出 HARD_MAX 的块应有 warning
    assert any("WARN" in e for e in result["errors"])


def test_chunk_char_count_matches_content():
    md = "## 范围\n\n内容。"
    result = slice_node(_make_state(md))
    for chunk in result["raw_chunks"]:
        assert chunk["char_count"] == len(chunk["content"])


def test_no_headings_produces_single_chunk():
    md = "这是一段没有标题的内容。" * 5
    result = slice_node(_make_state(md))
    assert len(result["raw_chunks"]) == 1


def test_section_path_reflects_heading_hierarchy():
    md = "## 检验方法\n\n### 试剂\n\n硫酸。\n\n### 仪器\n\n分光光度计。"
    config = {"chunk_soft_max": 20}
    result = slice_node(_make_state(md, config))
    paths = [c["section_path"] for c in result["raw_chunks"]]
    # 子节路径必须包含父标题
    assert any(len(p) >= 2 and "检验方法" in p[0] and "试剂" in p[-1] for p in paths)
    assert any(len(p) >= 2 and "检验方法" in p[0] and "仪器" in p[-1] for p in paths)


def test_chunk_content_includes_heading_line():
    """每个切片的 content 必须包含其自身的标题行（spec：含其标题）。"""
    md = "## 技术要求\n\n理化指标见下表。"
    result = slice_node(_make_state(md))
    chunks = [c for c in result["raw_chunks"] if "技术要求" in c["section_path"][-1]]
    assert len(chunks) == 1
    assert "技术要求" in chunks[0]["content"]
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py -v
```

- [ ] **Step 3：实现 slice_node**

`app/core/parser_workflow/nodes/slice_node.py`:
```python
from __future__ import annotations
import re
from typing import List, Tuple
from app.core.parser_workflow.models import WorkflowState, RawChunk
from app.core.parser_workflow.config import (
    CHUNK_SOFT_MAX_DEFAULT,
    CHUNK_HARD_MAX_DEFAULT,
    SLICE_HEADING_LEVELS_DEFAULT,
    get_config_value,
)


def _heading_pattern(level: int) -> re.Pattern:
    prefix = "#" * level
    return re.compile(rf"^{re.escape(prefix)} (.+)$", re.MULTILINE)


def _split_by_heading(text: str, level: int) -> List[Tuple[str, str]]:
    """
    按指定级别标题切分。
    返回 [(heading_title, block_content), ...]
    - heading_title 为空字符串时表示标题前的内容（前言）
    - block_content 包含标题行本身（spec 要求"含其标题"）
    """
    pattern = _heading_pattern(level)
    parts: List[Tuple[str, str]] = []
    last_end = 0
    last_title = ""

    for m in pattern.finditer(text):
        segment = text[last_end:m.start()]
        if segment.strip() or last_title == "":
            parts.append((last_title, segment))
        last_title = m.group(1).strip()
        last_end = m.start()  # 从标题行开头开始，确保标题行包含在 content 中

    # 最后一段（包含标题行）
    parts.append((last_title, text[last_end:]))
    return parts


def recursive_slice(
    content: str,
    heading_levels: List[int],
    parent_path: List[str],
    soft_max: int,
    hard_max: int,
    errors: List[str],
) -> List[RawChunk]:
    if not heading_levels:
        chunk = RawChunk(content=content, section_path=parent_path[:], char_count=len(content))
        if len(content) > hard_max:
            errors.append(f"WARN: chunk exceeds HARD_MAX ({len(content)} chars) at {parent_path}")
        return [chunk]

    level = heading_levels[0]
    parts = _split_by_heading(content, level)

    # 如果没找到该级别标题（只有一个空标题的部分）
    if len(parts) == 1 and parts[0][0] == "":
        return recursive_slice(content, heading_levels[1:], parent_path, soft_max, hard_max, errors)

    result: List[RawChunk] = []
    for title, block in parts:
        if not block.strip() and not title:
            continue
        path = parent_path + ([title] if title else [])
        char_count = len(block)
        if char_count <= soft_max or len(heading_levels) <= 1:
            chunk = RawChunk(content=block, section_path=path, char_count=len(block))
            if len(block) > hard_max:
                errors.append(f"WARN: chunk exceeds HARD_MAX ({len(block)} chars) at {path}")
            result.append(chunk)
        else:
            result.extend(
                recursive_slice(block, heading_levels[1:], path, soft_max, hard_max, errors)
            )
    return result


def slice_node(state: WorkflowState) -> dict:
    cfg = state.get("config", {})
    soft_max = get_config_value(cfg, "chunk_soft_max", CHUNK_SOFT_MAX_DEFAULT)
    hard_max = get_config_value(cfg, "chunk_hard_max", CHUNK_HARD_MAX_DEFAULT)
    levels = get_config_value(cfg, "slice_heading_levels", SLICE_HEADING_LEVELS_DEFAULT)

    md = state["md_content"]
    errors = list(state.get("errors", []))
    raw_chunks: List[RawChunk] = []

    # 前言处理：提取第一个顶级标题前的内容
    first_heading_level = levels[0]
    pattern = _heading_pattern(first_heading_level)
    first_match = pattern.search(md)
    if first_match and first_match.start() > 0:
        preamble = md[: first_match.start()].strip()
        if preamble:
            raw_chunks.append(
                RawChunk(content=preamble, section_path=["__preamble__"], char_count=len(preamble))
            )
        md = md[first_match.start():]

    raw_chunks.extend(recursive_slice(md, levels, [], soft_max, hard_max, errors))
    return {"raw_chunks": raw_chunks, "errors": errors}
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py -v
```
预期：8 个测试全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add app/core/parser_workflow/nodes/slice_node.py tests/core/parser_workflow/test_slice_node.py
git commit -m "feat(parser-workflow): add slice_node with recursive heading split"
```

---

### Task 6：structure_node（规则匹配部分，LLM 兜底在 Task 9 添加）

**Files:**
- Create: `app/core/parser_workflow/nodes/structure_node.py`
- Create: `tests/core/parser_workflow/test_structure_node.py`

- [ ] **Step 1：写测试**

`tests/core/parser_workflow/test_structure_node.py`:
```python
import json
import pytest
from unittest.mock import patch, MagicMock
from app.core.parser_workflow.nodes.structure_node import structure_node, match_doc_type_by_rules
from app.core.parser_workflow.models import WorkflowState


def _make_state(md: str, rules_dir: str = "/tmp") -> WorkflowState:
    return WorkflowState(
        md_content=md,
        doc_metadata={"standard_no": "GB_TEST", "title": "测试"},
        config={},
        rules_dir=rules_dir,
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


DETECTION_MD = """# 乙氧基喹的测定

## 范围

本标准规定乙氧基喹检测方法。

## 试剂和材料

硫酸铵。

## 仪器和设备

分光光度计。

## 分析步骤

操作步骤如下。
"""

SINGLE_ADDITIVE_MD = """# β-胡萝卜素

## 范围

食品添加剂使用标准。

## 技术要求

理化指标见下表。含量不得少于 96%。

## 检验规则

按批次检验。
"""


def test_match_detection_method_by_keywords(tmp_path):
    from app.core.parser_workflow.rules import RulesStore
    store = RulesStore(str(tmp_path))
    doc_type, source = match_doc_type_by_rules(DETECTION_MD, store)
    assert doc_type == "detection_method"
    assert source == "rule"


def test_match_single_additive_by_keywords(tmp_path):
    from app.core.parser_workflow.rules import RulesStore
    store = RulesStore(str(tmp_path))
    doc_type, source = match_doc_type_by_rules(SINGLE_ADDITIVE_MD, store)
    assert doc_type == "single_additive"
    assert source == "rule"


def test_returns_none_when_no_match(tmp_path):
    from app.core.parser_workflow.rules import RulesStore
    store = RulesStore(str(tmp_path))
    md = "## 随机内容\n\n没有任何匹配关键词。"
    result = match_doc_type_by_rules(md, store)
    assert result is None


def test_structure_node_sets_doc_type_in_metadata(tmp_path):
    state = _make_state(SINGLE_ADDITIVE_MD, str(tmp_path))
    result = structure_node(state)
    assert result["doc_metadata"]["doc_type"] == "single_additive"
    assert result["doc_metadata"]["doc_type_source"] == "rule"


def test_structure_node_calls_llm_when_no_rule_match(tmp_path):
    state = _make_state("## 随机内容\n\n无任何关键词匹配", str(tmp_path))
    mock_response = {
        "id": "generic_standard",
        "description": "通用国家标准",
        "detect_keywords": ["范围"],
        "detect_heading_patterns": ["范围"],
        "source": "llm"
    }
    with patch(
        "app.core.parser_workflow.nodes.structure_node._infer_doc_type_with_llm",
        return_value=mock_response,
    ):
        result = structure_node(state)
    assert result["doc_metadata"]["doc_type"] == "generic_standard"
    assert result["doc_metadata"]["doc_type_source"] == "llm"


def test_structure_node_llm_fallback_persists_new_rule_to_disk(tmp_path):
    """LLM 推断的新类型必须写入 doc_type_rules.json（spec §5.1 要求）。"""
    state = _make_state("## 随机内容\n\n无任何关键词匹配", str(tmp_path))
    mock_response = {
        "id": "new_persisted_type",
        "description": "新文档类型",
        "detect_keywords": ["新关键词"],
        "detect_heading_patterns": [],
        "source": "llm"
    }
    with patch(
        "app.core.parser_workflow.nodes.structure_node._infer_doc_type_with_llm",
        return_value=mock_response,
    ):
        structure_node(state)
    from app.core.parser_workflow.rules import RulesStore
    store = RulesStore(str(tmp_path))
    ids = [d["id"] for d in store.get_doc_type_rules()["doc_types"]]
    assert "new_persisted_type" in ids
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_structure_node.py -v
```

- [ ] **Step 3：实现 structure_node（规则部分 + LLM 桩）**

`app/core/parser_workflow/nodes/structure_node.py`:
```python
from __future__ import annotations
import re
from typing import Optional, Tuple
from app.core.parser_workflow.models import WorkflowState
from app.core.parser_workflow.rules import RulesStore


def _extract_headings(md: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^## (.+)$", md, re.MULTILINE)]


def match_doc_type_by_rules(
    md: str, store: RulesStore
) -> Optional[Tuple[str, str]]:
    """按规则匹配文档类型。命中返回 (doc_type_id, "rule")，否则返回 None。"""
    rules = store.get_doc_type_rules()
    threshold = rules.get("match_threshold", 2)
    headings = _extract_headings(md)

    best_id = None
    best_score = 0
    for dt in rules.get("doc_types", []):
        score = 0
        for kw in dt.get("detect_keywords", []):
            if kw in md:
                score += 1
        for hp in dt.get("detect_heading_patterns", []):
            if any(hp in h for h in headings):
                score += 1
        if score >= threshold and score > best_score:
            best_score = score
            best_id = dt["id"]

    if best_id:
        return best_id, "rule"
    return None


def _infer_doc_type_with_llm(headings: list[str], existing_types: list, config: dict) -> dict:
    """调用 LLM 推断文档类型。实际实现在 Task 9 完成，此处为桩函数。"""
    raise NotImplementedError("LLM doc type inference not yet implemented")


def structure_node(state: WorkflowState) -> dict:
    meta = dict(state["doc_metadata"])
    errors = list(state.get("errors", []))
    store = RulesStore(state["rules_dir"])

    match = match_doc_type_by_rules(state["md_content"], store)
    if match:
        meta["doc_type"], meta["doc_type_source"] = match
    else:
        headings = _extract_headings(state["md_content"])
        existing_types = store.get_doc_type_rules().get("doc_types", [])
        new_rule = _infer_doc_type_with_llm(headings, existing_types, state.get("config", {}))
        store.append_doc_type(new_rule)
        meta["doc_type"] = new_rule["id"]
        meta["doc_type_source"] = "llm"

    return {"doc_metadata": meta, "errors": errors}
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_structure_node.py -v
```
预期：7 个测试全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add app/core/parser_workflow/nodes/structure_node.py \
        tests/core/parser_workflow/test_structure_node.py
git commit -m "feat(parser-workflow): add structure_node with rule-based doc_type inference"
```

---

### Task 7：transform_node

**Files:**
- Create: `app/core/parser_workflow/nodes/transform_node.py`
- Create: `tests/core/parser_workflow/test_transform_node.py`

- [ ] **Step 1：写测试**

`tests/core/parser_workflow/test_transform_node.py`:
```python
import pytest
from app.core.parser_workflow.nodes.transform_node import (
    transform_node,
    apply_strategy,
    dominant_content_type,
)
from app.core.parser_workflow.models import (
    WorkflowState, ClassifiedChunk, RawChunk, TypedSegment
)


def _seg(content: str, ct: str, strategy: str = "plain_embed") -> TypedSegment:
    return TypedSegment(
        content=content,
        content_type=ct,
        transform_params={"strategy": strategy},
        confidence=0.9,
        escalated=False,
    )


def _raw(content: str) -> RawChunk:
    return RawChunk(content=content, section_path=["3 范围"], char_count=len(content))


def _make_state(classified: list) -> WorkflowState:
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "GB_TEST", "title": "t"},
        config={},
        rules_dir="/tmp",
        raw_chunks=[],
        classified_chunks=classified,
        final_chunks=[],
        errors=[],
    )


# ── dominant_content_type ──────────────────────────────────

def test_dominant_type_single_segment():
    segs = [_seg("短文本", "plain_text")]
    assert dominant_content_type(segs) == "plain_text"


def test_dominant_type_picks_largest_by_char_count():
    segs = [
        _seg("x" * 100, "plain_text"),
        _seg("y" * 20, "table"),
    ]
    assert dominant_content_type(segs) == "plain_text"


# ── apply_strategy ─────────────────────────────────────────

def test_preserve_as_is_returns_single_chunk():
    seg = _seg("公式内容 $E=mc^2$", "formula", "preserve_as_is")
    raw = _raw("公式内容 $E=mc^2$")
    chunks = apply_strategy([seg], raw, {"standard_no": "GB_TEST", "title": "t"})
    assert len(chunks) == 1
    assert chunks[0]["content"] == "公式内容 $E=mc^2$"
    assert chunks[0]["content_type"] == "formula"


def test_plain_embed_strips_extra_whitespace():
    seg = _seg("  内容  \n\n  说明  ", "plain_text", "plain_embed")
    raw = _raw("  内容  \n\n  说明  ")
    chunks = apply_strategy([seg], raw, {"standard_no": "GB_TEST", "title": "t"})
    assert len(chunks) == 1
    assert chunks[0]["content"].strip() == chunks[0]["content"]


def test_split_rows_produces_one_chunk_per_data_row():
    table_md = "| 项目 | 指标 |\n|---|---|\n| 含量 | ≥96% |\n| 水分 | ≤0.5% |"
    seg = _seg(table_md, "table", "split_rows")
    seg["transform_params"]["preserve_header"] = True
    raw = _raw(table_md)
    chunks = apply_strategy([seg], raw, {"standard_no": "GB_TEST", "title": "t"})
    # 2 data rows → 2 chunks
    assert len(chunks) == 2
    assert all(c["content_type"] == "table" for c in chunks)
    assert all(c["meta"].get("table_row_index") is not None for c in chunks)
    # 每个 chunk 的 content 应包含表头
    assert all("项目" in c["content"] for c in chunks)


def test_split_rows_preserves_raw_content():
    table_md = "| A | B |\n|---|---|\n| 1 | 2 |"
    seg = _seg(table_md, "table", "split_rows")
    seg["transform_params"]["preserve_header"] = True
    raw = _raw(table_md)
    chunks = apply_strategy([seg], raw, {"standard_no": "GB_TEST", "title": "t"})
    assert all(c["raw_content"] == table_md for c in chunks)


def test_split_rows_header_only_table_falls_back_to_preserve():
    """只有表头没有数据行时，降级为 preserve_as_is 输出 1 个 chunk。"""
    header_only = "| 项目 | 指标 |\n|---|---|"
    seg = _seg(header_only, "table", "split_rows")
    seg["transform_params"]["preserve_header"] = True
    raw = _raw(header_only)
    chunks = apply_strategy([seg], raw, {"standard_no": "GB_TEST", "title": "t"})
    assert len(chunks) == 1
    assert chunks[0]["content"] == header_only


def test_transform_node_produces_final_chunks():
    classified = [
        ClassifiedChunk(
            raw_chunk=_raw("普通文本内容"),
            segments=[_seg("普通文本内容", "plain_text")],
            has_unknown=False,
        )
    ]
    result = transform_node(_make_state(classified))
    assert len(result["final_chunks"]) >= 1
    assert result["final_chunks"][0]["content_type"] == "plain_text"
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_transform_node.py -v
```

- [ ] **Step 3：实现 transform_node**

`app/core/parser_workflow/nodes/transform_node.py`:
```python
from __future__ import annotations
import re
from typing import List
from app.core.parser_workflow.models import (
    WorkflowState, ClassifiedChunk, TypedSegment, DocumentChunk
)
from app.core.parser_workflow.models import make_chunk_id


def dominant_content_type(segments: List[TypedSegment]) -> str:
    """按字符数占比最高的 segment 的 content_type。"""
    if not segments:
        return "plain_text"
    return max(segments, key=lambda s: len(s["content"]))["content_type"]


def _parse_table(table_md: str):
    """解析 Markdown 表格，返回 (header_row, [data_rows])。"""
    lines = [l for l in table_md.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return None, []
    header = lines[0]
    # lines[1] 是分隔行 (---|---)
    data_rows = lines[2:]
    return header, data_rows


def apply_strategy(
    segments: List[TypedSegment],
    raw_chunk,
    doc_metadata: dict,
) -> List[DocumentChunk]:
    """将一组 TypedSegment 按各自策略转化为 DocumentChunk 列表。"""
    results: List[DocumentChunk] = []

    # 整个 RawChunk 的主类型（用于多 segment 的单输出情况）
    main_ct = dominant_content_type(segments)

    for seg in segments:
        strategy = seg["transform_params"].get("strategy", "plain_embed")
        raw_content = raw_chunk["content"]

        if strategy == "split_rows":
            header, data_rows = _parse_table(seg["content"])
            if not data_rows:
                # 无法解析表格，降级为 preserve_as_is
                results.append(_make_single_chunk(seg, raw_chunk, doc_metadata, seg["content_type"]))
                continue
            for i, row in enumerate(data_rows):
                content = f"{header}\n{row}" if header else row
                results.append(DocumentChunk(
                    chunk_id=make_chunk_id(
                        doc_metadata.get("standard_no", ""),
                        raw_chunk["section_path"],
                        content,
                    ),
                    doc_metadata=doc_metadata,
                    section_path=raw_chunk["section_path"],
                    content_type=seg["content_type"],
                    content=content,
                    raw_content=raw_content,
                    meta={"table_row_index": i},
                ))

        elif strategy == "plain_embed":
            content = " ".join(seg["content"].split())
            results.append(DocumentChunk(
                chunk_id=make_chunk_id(
                    doc_metadata.get("standard_no", ""),
                    raw_chunk["section_path"],
                    content,
                ),
                doc_metadata=doc_metadata,
                section_path=raw_chunk["section_path"],
                content_type=seg["content_type"],
                content=content,
                raw_content=raw_content,
                meta={},
            ))

        else:  # preserve_as_is, preserve_as_list
            results.append(_make_single_chunk(seg, raw_chunk, doc_metadata, seg["content_type"]))

    return results


def _make_single_chunk(seg, raw_chunk, doc_metadata, content_type) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=make_chunk_id(
            doc_metadata.get("standard_no", ""),
            raw_chunk["section_path"],
            seg["content"],
        ),
        doc_metadata=doc_metadata,
        section_path=raw_chunk["section_path"],
        content_type=content_type,
        content=seg["content"],
        raw_content=raw_chunk["content"],
        meta={},
    )


def transform_node(state: WorkflowState) -> dict:
    final_chunks: List[DocumentChunk] = []
    for classified in state["classified_chunks"]:
        chunks = apply_strategy(
            classified["segments"],
            classified["raw_chunk"],
            state["doc_metadata"],
        )
        final_chunks.extend(chunks)
    return {"final_chunks": final_chunks}
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_transform_node.py -v
```
预期：8 个测试全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add app/core/parser_workflow/nodes/transform_node.py \
        tests/core/parser_workflow/test_transform_node.py
git commit -m "feat(parser-workflow): add transform_node with split_rows/preserve/plain_embed"
```

---

## Chunk 3：LLM 节点与图装配

### Task 8：classify_node（小模型 LLM）

**Files:**
- Create: `app/core/parser_workflow/nodes/classify_node.py`
- Create: `tests/core/parser_workflow/test_classify_node.py`

说明：classify_node 使用 `langchain_openai.ChatOpenAI` 的 `with_structured_output`，通过 Pydantic 模型强制 structured output。LLM 调用在测试中完全 mock，不需要真实 API key。

- [ ] **Step 1：写测试**

`tests/core/parser_workflow/test_classify_node.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from app.core.parser_workflow.nodes.classify_node import classify_node, classify_raw_chunk
from app.core.parser_workflow.models import WorkflowState, RawChunk


def _raw(content: str) -> RawChunk:
    return RawChunk(content=content, section_path=["3 范围"], char_count=len(content))


def _make_state(chunks: list, rules_dir: str = "/tmp", config: dict = None) -> WorkflowState:
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "GB_TEST", "title": "t"},
        config=config or {"classify_model": "gpt-mock", "llm_api_key": "test"},
        rules_dir=rules_dir,
        raw_chunks=chunks,
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


MOCK_LLM_RESPONSE = {
    "segments": [
        {"content": "普通文本内容", "content_type": "plain_text", "confidence": 0.95}
    ]
}

TABLE_MD = "## 技术指标\n\n| 项目 | 值 |\n|---|---|\n| 含量 | 96% |"
MIXED_RESPONSE = {
    "segments": [
        {"content": "## 技术指标", "content_type": "plain_text", "confidence": 0.9},
        {"content": "| 项目 | 值 |\n|---|---|\n| 含量 | 96% |", "content_type": "table", "confidence": 0.92},
    ]
}


def test_classify_marks_all_confident_segments(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=MOCK_LLM_RESPONSE,
    ):
        state = _make_state([_raw("普通文本内容")], rules_dir=str(tmp_path))
        result = classify_node(state)
    assert len(result["classified_chunks"]) == 1
    cc = result["classified_chunks"][0]
    assert cc["has_unknown"] is False
    assert cc["segments"][0]["content_type"] == "plain_text"
    assert cc["segments"][0]["escalated"] is False


def test_classify_marks_low_confidence_as_unknown(tmp_path):
    low_conf_response = {
        "segments": [
            {"content": "奇怪内容", "content_type": "plain_text", "confidence": 0.3}
        ]
    }
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=low_conf_response,
    ):
        state = _make_state([_raw("奇怪内容")], rules_dir=str(tmp_path),
                            config={"classify_model": "m", "llm_api_key": "k",
                                    "confidence_threshold": 0.7})
        result = classify_node(state)
    assert result["classified_chunks"][0]["has_unknown"] is True
    assert result["classified_chunks"][0]["segments"][0]["content_type"] == "unknown"


def test_classify_mixed_chunk_partial_unknown(tmp_path):
    mixed_low = {
        "segments": [
            {"content": "正常内容", "content_type": "plain_text", "confidence": 0.95},
            {"content": "奇怪片段", "content_type": "plain_text", "confidence": 0.2},
        ]
    }
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=mixed_low,
    ):
        state = _make_state([_raw("正常内容\n奇怪片段")], rules_dir=str(tmp_path))
        result = classify_node(state)
    cc = result["classified_chunks"][0]
    assert cc["has_unknown"] is True
    # 只有低置信度的那个是 unknown
    unknowns = [s for s in cc["segments"] if s["content_type"] == "unknown"]
    assert len(unknowns) == 1


def test_classify_fills_transform_params_from_rules(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=MOCK_LLM_RESPONSE,
    ):
        state = _make_state([_raw("普通文本内容")], rules_dir=str(tmp_path))
        result = classify_node(state)
    seg = result["classified_chunks"][0]["segments"][0]
    assert "strategy" in seg["transform_params"]


def test_classify_multiple_chunks_all_classified(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=MOCK_LLM_RESPONSE,
    ):
        state = _make_state(
            [_raw("内容A"), _raw("内容B")], rules_dir=str(tmp_path)
        )
        result = classify_node(state)
    assert len(result["classified_chunks"]) == 2
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_classify_node.py -v
```

- [ ] **Step 3：实现 classify_node**

`app/core/parser_workflow/nodes/classify_node.py`:
```python
from __future__ import annotations
from typing import Any, Dict, List
from app.core.parser_workflow.models import (
    WorkflowState, RawChunk, ClassifiedChunk, TypedSegment
)
from app.core.parser_workflow.rules import RulesStore
from app.core.parser_workflow.config import get_config_value


def _call_classify_llm(
    chunk_content: str,
    content_types: List[Dict],
    config: dict,
) -> Dict[str, Any]:
    """
    调用小模型对 chunk 做分段 + 分类。
    返回 {"segments": [{"content": ..., "content_type": ..., "confidence": ...}]}
    """
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel

    class SegmentItem(BaseModel):
        content: str
        content_type: str
        confidence: float

    class ClassifyOutput(BaseModel):
        segments: List[SegmentItem]

    type_descriptions = "\n".join(
        f"- {ct['id']}: {ct['description']}" for ct in content_types
    )
    prompt = (
        f"请将以下文本拆分为语义独立的片段，并为每段指定 content_type 和置信度（0-1）。\n\n"
        f"可用的 content_type：\n{type_descriptions}\n\n"
        f"文本内容：\n{chunk_content}"
    )

    model = ChatOpenAI(
        model=config.get("classify_model", "gpt-4o-mini"),
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    ).with_structured_output(ClassifyOutput)

    result: ClassifyOutput = model.invoke(prompt)
    return {"segments": [s.model_dump() for s in result.segments]}


def classify_raw_chunk(
    raw_chunk: RawChunk,
    store: RulesStore,
    config: dict,
) -> ClassifiedChunk:
    threshold = store.get_confidence_threshold(
        config.get("confidence_threshold")
    )
    ct_rules = store.get_content_type_rules()
    content_types = ct_rules.get("content_types", [])

    llm_output = _call_classify_llm(raw_chunk["content"], content_types, config)

    segments: List[TypedSegment] = []
    has_unknown = False
    for item in llm_output.get("segments", []):
        confidence = item.get("confidence", 0.0)
        if confidence < threshold:
            seg = TypedSegment(
                content=item["content"],
                content_type="unknown",
                transform_params={"strategy": "plain_embed"},
                confidence=confidence,
                escalated=False,
            )
            has_unknown = True
        else:
            ct_id = item["content_type"]
            transform_params = store.get_transform_params(ct_id)
            seg = TypedSegment(
                content=item["content"],
                content_type=ct_id,
                transform_params=transform_params,
                confidence=confidence,
                escalated=False,
            )
        segments.append(seg)

    return ClassifiedChunk(
        raw_chunk=raw_chunk,
        segments=segments,
        has_unknown=has_unknown,
    )


def classify_node(state: WorkflowState) -> dict:
    store = RulesStore(state["rules_dir"])
    config = state.get("config", {})
    classified: List[ClassifiedChunk] = [
        classify_raw_chunk(chunk, store, config)
        for chunk in state["raw_chunks"]
    ]
    return {"classified_chunks": classified}
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_classify_node.py -v
```
预期：5 个测试全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add app/core/parser_workflow/nodes/classify_node.py \
        tests/core/parser_workflow/test_classify_node.py
git commit -m "feat(parser-workflow): add classify_node with structured LLM output"
```

---

### Task 9：escalate_node + structure_node LLM 兜底

**Files:**
- Create: `app/core/parser_workflow/nodes/escalate_node.py`
- Modify: `app/core/parser_workflow/nodes/structure_node.py`（实现 `_infer_doc_type_with_llm`）
- Create: `tests/core/parser_workflow/test_escalate_node.py`

- [ ] **Step 1：写 escalate_node 测试**

`tests/core/parser_workflow/test_escalate_node.py`:
```python
import json
import pytest
from unittest.mock import patch
from app.core.parser_workflow.nodes.escalate_node import escalate_node
from app.core.parser_workflow.models import (
    WorkflowState, ClassifiedChunk, RawChunk, TypedSegment
)


def _seg(content: str, ct: str, confidence: float = 0.9) -> TypedSegment:
    return TypedSegment(
        content=content, content_type=ct,
        transform_params={"strategy": "plain_embed"},
        confidence=confidence, escalated=False,
    )


def _raw(content: str) -> RawChunk:
    return RawChunk(content=content, section_path=["3"], char_count=len(content))


def _make_state(classified: list, rules_dir: str) -> WorkflowState:
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "GB_TEST", "title": "t"},
        config={"escalate_model": "gpt-mock", "llm_api_key": "test"},
        rules_dir=rules_dir,
        raw_chunks=[],
        classified_chunks=classified,
        final_chunks=[],
        errors=[],
    )


MOCK_ESCALATE_RESPONSE = {
    "content_type": "flowchart",
    "description": "流程图描述文字",
    "transform": {"strategy": "preserve_as_is"}
}


def test_escalate_resolves_unknown_segment(tmp_path):
    classified = [ClassifiedChunk(
        raw_chunk=_raw("流程图内容"),
        segments=[_seg("流程图内容", "unknown", 0.3)],
        has_unknown=True,
    )]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=MOCK_ESCALATE_RESPONSE,
    ):
        result = escalate_node(_make_state(classified, str(tmp_path)))
    cc = result["classified_chunks"][0]
    assert cc["has_unknown"] is False
    assert cc["segments"][0]["content_type"] == "flowchart"
    assert cc["segments"][0]["escalated"] is True
    assert cc["segments"][0]["confidence"] == 1.0


def test_escalate_appends_new_rule_to_file(tmp_path):
    classified = [ClassifiedChunk(
        raw_chunk=_raw("流程图内容"),
        segments=[_seg("流程图内容", "unknown", 0.3)],
        has_unknown=True,
    )]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=MOCK_ESCALATE_RESPONSE,
    ):
        escalate_node(_make_state(classified, str(tmp_path)))
    from app.core.parser_workflow.rules import RulesStore
    store = RulesStore(str(tmp_path))
    ids = [ct["id"] for ct in store.get_content_type_rules()["content_types"]]
    assert "flowchart" in ids


def test_escalate_skips_chunks_without_unknown(tmp_path):
    classified = [ClassifiedChunk(
        raw_chunk=_raw("普通内容"),
        segments=[_seg("普通内容", "plain_text", 0.95)],
        has_unknown=False,
    )]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm"
    ) as mock_llm:
        escalate_node(_make_state(classified, str(tmp_path)))
    mock_llm.assert_not_called()


def test_escalate_only_resolves_unknown_segments_not_known_ones(tmp_path):
    classified = [ClassifiedChunk(
        raw_chunk=_raw("内容A\n内容B"),
        segments=[
            _seg("内容A", "plain_text", 0.95),
            _seg("内容B", "unknown", 0.2),
        ],
        has_unknown=True,
    )]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=MOCK_ESCALATE_RESPONSE,
    ):
        result = escalate_node(_make_state(classified, str(tmp_path)))
    segs = result["classified_chunks"][0]["segments"]
    assert segs[0]["content_type"] == "plain_text"   # 未被改动
    assert segs[0]["escalated"] is False
    assert segs[1]["content_type"] == "flowchart"    # 被 escalate 处理
    assert segs[1]["escalated"] is True
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_escalate_node.py -v
```

- [ ] **Step 3：实现 escalate_node**

`app/core/parser_workflow/nodes/escalate_node.py`:
```python
from __future__ import annotations
from typing import Any, Dict, List
from app.core.parser_workflow.models import WorkflowState, ClassifiedChunk, TypedSegment
from app.core.parser_workflow.rules import RulesStore


def _call_escalate_llm(
    segment_content: str,
    existing_types: List[Dict],
    config: dict,
) -> Dict[str, Any]:
    """
    大模型判断 unknown 片段的类型，返回新 content_type 规则。
    """
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel

    class EscalateOutput(BaseModel):
        content_type: str
        description: str
        transform: Dict[str, Any]

    type_list = "\n".join(f"- {t['id']}: {t['description']}" for t in existing_types)
    prompt = (
        f"以下文本片段无法被现有内容类型识别。请判断它属于什么类型，"
        f"并提供新的 content_type 定义。\n\n"
        f"现有类型：\n{type_list}\n\n"
        f"文本内容：\n{segment_content}\n\n"
        f"请返回新的 content_type（若已有合适类型可直接使用现有 id）、"
        f"描述和 transform 参数（strategy 选 preserve_as_is / plain_embed / split_rows / preserve_as_list）。"
    )

    model = ChatOpenAI(
        model=config.get("escalate_model", "gpt-4o"),
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    ).with_structured_output(EscalateOutput)

    result: EscalateOutput = model.invoke(prompt)
    return result.model_dump()


def escalate_node(state: WorkflowState) -> dict:
    store = RulesStore(state["rules_dir"])
    config = state.get("config", {})
    classified_chunks: List[ClassifiedChunk] = [
        dict(c) for c in state["classified_chunks"]
    ]

    for i, cc in enumerate(classified_chunks):
        if not cc["has_unknown"]:
            continue

        existing_types = store.get_content_type_rules().get("content_types", [])
        new_segments = list(cc["segments"])

        for j, seg in enumerate(new_segments):
            if seg["content_type"] != "unknown":
                continue

            llm_result = _call_escalate_llm(seg["content"], existing_types, config)
            new_ct_id = llm_result["content_type"]

            # 若是全新类型，追加到规则文件
            known_ids = {t["id"] for t in existing_types}
            if new_ct_id not in known_ids:
                store.append_content_type({
                    "id": new_ct_id,
                    "description": llm_result["description"],
                    "transform": llm_result["transform"],
                })
                # 重新获取（reload 已在 append 内部完成）
                existing_types = store.get_content_type_rules().get("content_types", [])

            transform_params = store.get_transform_params(new_ct_id)
            new_segments[j] = TypedSegment(
                content=seg["content"],
                content_type=new_ct_id,
                transform_params=transform_params,
                confidence=1.0,
                escalated=True,
            )

        classified_chunks[i] = ClassifiedChunk(
            raw_chunk=cc["raw_chunk"],
            segments=new_segments,
            has_unknown=False,
        )

    return {"classified_chunks": classified_chunks}
```

- [ ] **Step 4：实现 structure_node 的 LLM 兜底**

修改 `app/core/parser_workflow/nodes/structure_node.py`，替换 `_infer_doc_type_with_llm` 桩函数：

```python
def _infer_doc_type_with_llm(headings: list[str], existing_types: list, config: dict) -> dict:
    """调用 LLM 推断文档类型并返回新规则条目。"""
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel
    from typing import List as TList

    class DocTypeOutput(BaseModel):
        id: str
        description: str
        detect_keywords: TList[str]
        detect_heading_patterns: TList[str]

    existing_ids = "\n".join(f"- {t['id']}: {t['description']}" for t in existing_types)
    headings_str = "\n".join(headings)
    prompt = (
        f"以下是一份国家标准文档的章节标题列表，请推断其文档类型。\n\n"
        f"现有类型：\n{existing_ids}\n\n"
        f"章节标题：\n{headings_str}\n\n"
        f"若与现有类型不符，请定义新的文档类型，提供 id（英文下划线）、"
        f"描述、detect_keywords（用于将来规则匹配的关键词）、"
        f"detect_heading_patterns（标题模式）。"
    )

    model = ChatOpenAI(
        model=config.get("doc_type_llm_model", "gpt-4o-mini"),
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    ).with_structured_output(DocTypeOutput)

    result: DocTypeOutput = model.invoke(prompt)
    return {**result.model_dump(), "source": "llm"}
```

（将此函数替换掉 `structure_node.py` 中的 `raise NotImplementedError` 版本）

- [ ] **Step 5：运行所有 escalate 和 structure 测试**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_escalate_node.py \
    tests/core/parser_workflow/test_structure_node.py -v
```
预期：全部 PASS

- [ ] **Step 6：提交**

```bash
cd agent-server
git add app/core/parser_workflow/nodes/escalate_node.py \
        app/core/parser_workflow/nodes/structure_node.py \
        tests/core/parser_workflow/test_escalate_node.py
git commit -m "feat(parser-workflow): add escalate_node and complete structure_node LLM fallback"
```

---

### Task 10：LangGraph 图装配 + run_parser_workflow

**Files:**
- Create: `app/core/parser_workflow/graph.py`
- Modify: `app/core/parser_workflow/__init__.py`
- Test: `tests/core/parser_workflow/test_graph.py`

- [ ] **Step 1：写 _should_escalate 测试**

`tests/core/parser_workflow/test_graph.py`:
```python
from app.core.parser_workflow.models import WorkflowState, ClassifiedChunk, RawChunk, TypedSegment


def _make_state(classified: list) -> WorkflowState:
    return WorkflowState(
        md_content="", doc_metadata={}, config={}, rules_dir="/tmp",
        raw_chunks=[], classified_chunks=classified, final_chunks=[], errors=[],
    )


def _cc(has_unknown: bool) -> ClassifiedChunk:
    seg = TypedSegment(
        content="x", content_type="unknown" if has_unknown else "plain_text",
        transform_params={}, confidence=0.5 if has_unknown else 0.9, escalated=False,
    )
    return ClassifiedChunk(
        raw_chunk=RawChunk(content="x", section_path=["3"], char_count=1),
        segments=[seg], has_unknown=has_unknown,
    )


def test_should_escalate_routes_to_escalate_when_any_unknown():
    from app.core.parser_workflow.graph import _should_escalate
    state = _make_state([_cc(False), _cc(True)])
    assert _should_escalate(state) == "escalate_node"


def test_should_escalate_routes_to_transform_when_all_known():
    from app.core.parser_workflow.graph import _should_escalate
    state = _make_state([_cc(False), _cc(False)])
    assert _should_escalate(state) == "transform_node"


def test_should_escalate_routes_to_transform_when_no_chunks():
    from app.core.parser_workflow.graph import _should_escalate
    state = _make_state([])
    assert _should_escalate(state) == "transform_node"
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_graph.py -v
```
预期：`ImportError`（graph.py 尚不存在）

- [ ] **Step 3：实现 graph.py**

`app/core/parser_workflow/graph.py`:
```python
from __future__ import annotations
from typing import Any
from langgraph.graph import StateGraph, END
from app.core.parser_workflow.models import WorkflowState, ParserResult
from app.core.parser_workflow.nodes.parse_node import parse_node
from app.core.parser_workflow.nodes.structure_node import structure_node
from app.core.parser_workflow.nodes.slice_node import slice_node
from app.core.parser_workflow.nodes.classify_node import classify_node
from app.core.parser_workflow.nodes.escalate_node import escalate_node
from app.core.parser_workflow.nodes.transform_node import transform_node


def _should_escalate(state: WorkflowState) -> str:
    if any(c["has_unknown"] for c in state["classified_chunks"]):
        return "escalate_node"
    return "transform_node"


def _build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("parse_node", parse_node)
    builder.add_node("structure_node", structure_node)
    builder.add_node("slice_node", slice_node)
    builder.add_node("classify_node", classify_node)
    builder.add_node("escalate_node", escalate_node)
    builder.add_node("transform_node", transform_node)

    builder.set_entry_point("parse_node")
    builder.add_edge("parse_node", "structure_node")
    builder.add_edge("structure_node", "slice_node")
    builder.add_edge("slice_node", "classify_node")
    builder.add_conditional_edges("classify_node", _should_escalate)
    builder.add_edge("escalate_node", "transform_node")
    builder.add_edge("transform_node", END)
    return builder.compile()


_graph = _build_graph()


async def run_parser_workflow(
    md_content: str,
    doc_metadata: dict,
    rules_dir: str,
    config: dict = None,
) -> ParserResult:
    initial_state = WorkflowState(
        md_content=md_content,
        doc_metadata=doc_metadata,
        config=config or {},
        rules_dir=rules_dir,
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )
    result_state = await _graph.ainvoke(initial_state)
    escalate_count = sum(
        1 for c in result_state["classified_chunks"]
        if any(s.get("escalated") for s in c["segments"])
    )
    return ParserResult(
        chunks=result_state["final_chunks"],
        doc_metadata=result_state["doc_metadata"],
        errors=result_state["errors"],
        stats={
            "chunk_count": len(result_state["final_chunks"]),
            "escalate_count": escalate_count,
        },
    )
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_graph.py -v
```
预期：3 个测试全部 PASS

- [ ] **Step 5：更新 `__init__.py`**

`app/core/parser_workflow/__init__.py`:
```python
from app.core.parser_workflow.graph import run_parser_workflow
from app.core.parser_workflow.models import ParserResult, DocumentChunk

__all__ = ["run_parser_workflow", "ParserResult", "DocumentChunk"]
```

- [ ] **Step 6：验证图可以正常导入**

```bash
cd agent-server && python -c "from app.core.parser_workflow import run_parser_workflow; print('OK')"
```
预期：`OK`

- [ ] **Step 7：提交**

```bash
cd agent-server
git add app/core/parser_workflow/graph.py app/core/parser_workflow/__init__.py \
        tests/core/parser_workflow/test_graph.py
git commit -m "feat(parser-workflow): assemble LangGraph and expose run_parser_workflow"
```

---

## Chunk 4：集成测试

### Task 11：端到端集成测试

**Files:**
- Create: `tests/core/parser_workflow/test_workflow.py`

- [ ] **Step 1：写集成测试**

`tests/core/parser_workflow/test_workflow.py`:
```python
import pytest
import asyncio
from unittest.mock import patch
from app.core.parser_workflow import run_parser_workflow

# 一份模拟的 GB 单品标准 MD 文件内容
SAMPLE_MD = """# GB 8821-2011 食品安全国家标准 食品添加剂 β-胡萝卜素

## 范围

本标准适用于以β-胡萝卜素为主要成分的食品添加剂。

## 技术要求

本品应符合以下理化指标要求。含量不低于 96%。

### 理化指标

| 项目 | 指标 |
|---|---|
| 含量（以干基计）% | ≥96.0 |
| 干燥减量 % | ≤0.2 |
| 灼烧残渣 % | ≤0.2 |

## 检验规则

按批次检验。每批次应提供检验报告。
"""

CLASSIFY_MOCK = {
    "segments": [
        {"content": SAMPLE_MD, "content_type": "plain_text", "confidence": 0.88}
    ]
}

TABLE_CLASSIFY_MOCK = {
    "segments": [
        {"content": "| 项目 | 指标 |\n|---|---|\n| 含量（以干基计）% | ≥96.0 |\n| 干燥减量 % | ≤0.2 |\n| 灼烧残渣 % | ≤0.2 |",
         "content_type": "table", "confidence": 0.95},
    ]
}


def _mock_classify(chunk_content, content_types, config):
    if "|" in chunk_content and "---" in chunk_content:
        return TABLE_CLASSIFY_MOCK
    return CLASSIFY_MOCK


@pytest.mark.asyncio
async def test_end_to_end_produces_document_chunks(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        side_effect=_mock_classify,
    ):
        result = await run_parser_workflow(
            md_content=SAMPLE_MD,
            doc_metadata={"standard_no": "GB8821", "title": "β-胡萝卜素"},
            rules_dir=str(tmp_path),
            config={},
        )
    assert len(result["chunks"]) > 0
    assert result["doc_metadata"]["standard_no"] == "GB8821"
    assert result["stats"]["chunk_count"] == len(result["chunks"])


@pytest.mark.asyncio
async def test_end_to_end_table_produces_split_row_chunks(tmp_path):
    table_md = """# GB 8821-2011

## 技术要求

### 理化指标

| 项目 | 指标 |
|---|---|
| 含量 | ≥96% |
| 水分 | ≤0.5% |
"""
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=TABLE_CLASSIFY_MOCK,
    ):
        result = await run_parser_workflow(
            md_content=table_md,
            doc_metadata={"standard_no": "GB8821", "title": "t"},
            rules_dir=str(tmp_path),
            config={},
        )
    table_chunks = [c for c in result["chunks"] if c["content_type"] == "table"]
    assert len(table_chunks) == 2  # 2 data rows


@pytest.mark.asyncio
async def test_end_to_end_no_llm_key_still_works_with_mocked_classify(tmp_path):
    """验证在没有真实 LLM 密钥时，通过 mock 可以完整运行。
    使用含 '技术要求' 关键词的 MD，确保 structure_node 规则命中，无需 LLM 兜底。"""
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=CLASSIFY_MOCK,
    ):
        result = await run_parser_workflow(
            md_content="## 技术要求\n\n含量不低于 96%。\n\n## 检验规则\n\n按批次检验。",
            doc_metadata={"standard_no": "GB0000", "title": "测试标准"},
            rules_dir=str(tmp_path),
            config={},
        )
    assert len(result["errors"]) == 0 or all("standard_no" not in e for e in result["errors"])
    assert result["stats"]["chunk_count"] >= 1


@pytest.mark.asyncio
async def test_end_to_end_records_error_when_standard_no_missing(tmp_path):
    """使用含规则关键词的 MD，确保 structure_node 规则命中，不触发 LLM 兜底。"""
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=CLASSIFY_MOCK,
    ):
        result = await run_parser_workflow(
            md_content="## 技术要求\n\n含量不低于 96%。",
            doc_metadata={"title": "无编号标准"},
            rules_dir=str(tmp_path),
            config={},
        )
    assert any("standard_no" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_end_to_end_escalate_path_and_stats(tmp_path):
    """验证含 unknown 片段时，escalate 路径被触发，stats.escalate_count 正确。
    使用含规则关键词的 MD，确保 structure_node 规则命中。"""
    low_conf_classify = {
        "segments": [{"content": "奇怪内容", "content_type": "plain_text", "confidence": 0.2}]
    }
    escalate_response = {
        "content_type": "new_type",
        "description": "新类型描述",
        "transform": {"strategy": "preserve_as_is"},
    }
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=low_conf_classify,
    ), patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=escalate_response,
    ):
        result = await run_parser_workflow(
            md_content="## 技术要求\n\n奇怪内容。\n\n## 检验规则\n\n按批次检验。",
            doc_metadata={"standard_no": "GB0000", "title": "t"},
            rules_dir=str(tmp_path),
            config={"confidence_threshold": 0.7},
        )
    assert result["stats"]["escalate_count"] >= 1
    # 最终 chunk 应有类型（不再是 unknown）
    assert all(c["content_type"] != "unknown" for c in result["chunks"])
```

- [ ] **Step 2：安装 pytest-asyncio（如未安装）**

```bash
cd agent-server && uv add --dev pytest-asyncio
```

在 `pyproject.toml` 中确认或添加：
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3：运行集成测试**

```bash
cd agent-server && pytest tests/core/parser_workflow/test_workflow.py -v
```
预期：5 个测试全部 PASS

- [ ] **Step 4：运行所有 parser_workflow 测试确认无回归**

```bash
cd agent-server && pytest tests/core/parser_workflow/ -v
```
预期：全部 PASS

- [ ] **Step 5：提交**

```bash
cd agent-server
git add tests/core/parser_workflow/test_workflow.py pyproject.toml
git commit -m "test(parser-workflow): add end-to-end integration tests"
```

- [ ] **Step 6：最终整体测试**

```bash
cd agent-server && pytest tests/ -v
```
预期：所有测试全部 PASS（含现有测试）

---

Plan 已保存于 `docs/superpowers/plans/2026-03-13-gb-standard-parser-workflow.md`。如需执行，请使用 superpowers:subagent-driven-development 或 superpowers:executing-plans。
