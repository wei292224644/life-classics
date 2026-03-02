# Adaptive KB Splitter for GB Markdown Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the `adaptive_kb_splitter` pipeline that converts cleaned GB/technical-standard Markdown into high-quality `DocumentChunk`s, and wire it into the KB pipeline via `strategy="adaptive"`.

**Architecture:** Core logic lives in `app/core/kb/adaptive_split.py`, which defines `Block`, content-type classification, handlers, and `adaptive_split_markdown`. A thin Tool wraps this for agents, and `split_step(..., strategy="adaptive")` in `app/core/kb/__init__.py` routes documents into this splitter. MinerU PDF→Markdown and Markdown cleaning are assumed to exist; this plan only leaves TODO hooks for them.

**Tech Stack:** Python 3, existing KB models (`DocumentChunk`), your current test stack (assumed `pytest`), LLM client(s) already used in the project for tools/agents.

---

### Task 1: Define AdaptiveSplitOptions and ContentType Constants

**Files:**
- Modify: `app/core/kb/__init__.py` (import/export types as needed)
- Create or modify: `app/core/kb/adaptive_split.py` (type definitions)
- Test: `tests/kb/test_adaptive_split_types.py`

**Step 1: Write the failing test**

Create `tests/kb/test_adaptive_split_types.py`:

```python
from app.core.kb.adaptive_split import AdaptiveSplitOptions, ContentType


def test_adaptive_split_options_defaults():
    opts = AdaptiveSplitOptions()
    assert opts.enable_qa is True
    assert opts.max_block_tokens is None
    assert opts.debug is False


def test_content_type_constants_exist():
    assert ContentType.NARRATIVE == "narrative"
    assert ContentType.SCOPE == "scope"
    assert ContentType.DEFINITION == "definition"
    assert ContentType.SPEC_TEXT == "specification_text"
    assert ContentType.SPEC_TABLE == "specification_table"
    assert ContentType.METHOD_PERFORMANCE == "method_performance"
    assert ContentType.CALCULATION_FORMULA == "calculation_formula"
    assert ContentType.TEST_METHOD == "test_method"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/kb/test_adaptive_split_types.py -v
```

Expected: FAIL because `AdaptiveSplitOptions` / `ContentType` are not defined.

**Step 3: Write minimal implementation**

In `app/core/kb/adaptive_split.py` (new file if not present):

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class AdaptiveSplitOptions:
    enable_qa: bool = True
    max_block_tokens: Optional[int] = None
    debug: bool = False


class ContentType:
    NARRATIVE = "narrative"
    SCOPE = "scope"
    DEFINITION = "definition"
    SPEC_TEXT = "specification_text"
    SPEC_TABLE = "specification_table"
    METHOD_PERFORMANCE = "method_performance"
    CALCULATION_FORMULA = "calculation_formula"
    TEST_METHOD = "test_method"  # method_step is an alias at the doc level
```

If you want these types importable from `app.core.kb`, export them in `app/core/kb/__init__.py`.

**Step 4: Run test to verify it passes**

```bash
pytest tests/kb/test_adaptive_split_types.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/adaptive_split.py app/core/kb/__init__.py tests/kb/test_adaptive_split_types.py
git commit -m "feat(kb): add adaptive split options and content type constants"
```

---

### Task 2: Implement Block dataclass and split_markdown_to_blocks

**Files:**
- Modify: `app/core/kb/adaptive_split.py`
- Test: `tests/kb/test_adaptive_split_blocks.py`
- Create fixture: `tests/fixtures/gb_standard_sample.md`

**Step 1: Write the failing test**

Create `tests/fixtures/gb_standard_sample.md` with a small synthetic GB-like snippet, e.g.:

```markdown
# 1 范围

本标准适用于某某产品。

# 2 术语和定义

2.1 某术语

某术语的定义文本。
```

Then create `tests/kb/test_adaptive_split_blocks.py`:

```python
from pathlib import Path

from app.core.kb.adaptive_split import Block, split_markdown_to_blocks


FIXTURE = Path(__file__).parent.parent / "fixtures" / "gb_standard_sample.md"


def test_split_markdown_to_blocks_basic():
    md_text = FIXTURE.read_text(encoding="utf-8")
    blocks = split_markdown_to_blocks(md_text, doc_type="gb_standard")

    assert len(blocks) >= 2
    assert all(isinstance(b, Block) for b in blocks)

    headings = [" ".join(b.heading_path) for b in blocks]
    assert any("1 范围" in h for h in headings)
    assert any("2 术语和定义" in h for h in headings)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/kb/test_adaptive_split_blocks.py -v
```

Expected: FAIL because `Block`/`split_markdown_to_blocks` don’t exist or are incomplete.

**Step 3: Write minimal implementation**

In `app/core/kb/adaptive_split.py`:

```python
from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class Block:
    id: str
    heading_path: List[str]
    raw_text: str
    order_index: int
    table_html: Optional[str] = None
    table_rows: Optional[List[List[str]]] = None


_HEADING_RE = re.compile(r"^(#+)\s+(.*)")


def split_markdown_to_blocks(md_text: str, doc_type: str) -> List[Block]:
    """
    Simple heuristic splitter:
    - Uses markdown headings (#..######) as block boundaries.
    - Associates paragraphs under the nearest preceding heading.
    - doc_type is reserved for future heuristics (gb_standard vs generic).
    """
    lines = md_text.splitlines()
    blocks: List[Block] = []
    current_heading: List[str] = []
    current_lines: List[str] = []
    order_index = 0

    def flush_block():
        nonlocal order_index, current_lines
        if not current_lines:
            return
        raw = "\n".join(current_lines).strip()
        if not raw:
            current_lines = []
            return
        block_id = f"block_{order_index}"
        blocks.append(
            Block(
                id=block_id,
                heading_path=list(current_heading),
                raw_text=raw,
                order_index=order_index,
            )
        )
        order_index += 1
        current_lines = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            # New heading -> flush previous block
            flush_block()
            level = len(m.group(1))
            title = m.group(2).strip()
            # Truncate heading_path to current level-1 then append
            current_heading[:] = current_heading[: level - 1]
            current_heading.append(title)
            current_lines.append(line)
        else:
            current_lines.append(line)

    flush_block()
    return blocks
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/kb/test_adaptive_split_blocks.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/adaptive_split.py tests/kb/test_adaptive_split_blocks.py tests/fixtures/gb_standard_sample.md
git commit -m "feat(kb): add Block and basic markdown pre-splitting"
```

---

### Task 3: Implement classify_blocks_content_type (LLM-driven, stubbed for tests)

**Files:**
- Modify: `app/core/kb/adaptive_split.py`
- Test: `tests/kb/test_adaptive_split_classify.py`

**Step 1: Write the failing test**

Create `tests/kb/test_adaptive_split_classify.py`:

```python
from pathlib import Path

from app.core.kb.adaptive_split import (
    split_markdown_to_blocks,
    classify_blocks_content_type,
    ContentType,
)


FIXTURE = Path(__file__).parent.parent / "fixtures" / "gb_standard_sample.md"


def test_classify_blocks_content_type_returns_mapping():
    md_text = FIXTURE.read_text(encoding="utf-8")
    blocks = split_markdown_to_blocks(md_text, doc_type="gb_standard")

    type_map = classify_blocks_content_type(blocks, doc_type="gb_standard")

    assert set(type_map.keys()) == {b.id for b in blocks}
    # At least one block is recognized as scope or definition in GB-like docs.
    assert any(
        t in {ContentType.SCOPE, ContentType.DEFINITION, ContentType.NARRATIVE}
        for t in type_map.values()
    )
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/kb/test_adaptive_split_classify.py -v
```

Expected: FAIL because `classify_blocks_content_type` not implemented.

**Step 3: Write minimal implementation (stub-friendly)**

In `app/core/kb/adaptive_split.py`:

```python
from typing import Dict, Sequence


def classify_blocks_content_type(
    blocks: Sequence[Block],
    doc_type: str,
) -> Dict[str, str]:
    """
    LLM-driven in production; for now, implement simple heuristics suitable for tests.
    - If heading contains '范围' -> scope
    - If heading contains '术语' or '定义' -> definition
    - Else -> narrative
    """
    type_map: Dict[str, str] = {}
    for block in blocks:
        heading = " ".join(block.heading_path)
        if "范围" in heading:
            type_map[block.id] = ContentType.SCOPE
        elif "术语" in heading or "定义" in heading:
            type_map[block.id] = ContentType.DEFINITION
        else:
            type_map[block.id] = ContentType.NARRATIVE
    return type_map
```

Later you can swap this body to actually call your LLM, keeping the same signature.

**Step 4: Run test to verify it passes**

```bash
pytest tests/kb/test_adaptive_split_classify.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/adaptive_split.py tests/kb/test_adaptive_split_classify.py
git commit -m "feat(kb): add basic content-type classification for adaptive split"
```

---

### Task 4: Implement SKILL_REGISTRY and basic handlers (narrative, scope, definition)

**Files:**
- Modify: `app/core/kb/adaptive_split.py`
- Test: `tests/kb/test_adaptive_split_handlers.py`

**Step 1: Write the failing test**

Create `tests/kb/test_adaptive_split_handlers.py`:

```python
from app.core.kb.adaptive_split import (
    Block,
    ContentType,
    SKILL_REGISTRY,
)
from app.core.kb import DocumentChunk  # adjust import if path differs


def test_narrative_handler_registered_and_returns_chunk():
    handler = SKILL_REGISTRY[ContentType.NARRATIVE]
    block = Block(
        id="b1",
        heading_path=["前言"],
        raw_text="这是前言内容。",
        order_index=0,
    )

    chunks = handler(block, doc_id="doc1", doc_title="测试标准", doc_type="gb_standard")

    assert len(chunks) == 1
    assert isinstance(chunks[0], DocumentChunk)
    assert chunks[0].content_type == ContentType.NARRATIVE
    assert "这是前言内容" in chunks[0].content


def test_scope_handler_registered():
    assert ContentType.SCOPE in SKILL_REGISTRY
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/kb/test_adaptive_split_handlers.py -v
```

Expected: FAIL because `SKILL_REGISTRY` / handlers don’t exist or are incomplete.

**Step 3: Write minimal implementation**

In `app/core/kb/adaptive_split.py`:

```python
from typing import Protocol, Callable, List, Dict

from app.core.kb import DocumentChunk  # adjust import to your real path


class ChunkHandler(Protocol):
    def __call__(
        self,
        block: Block,
        *,
        doc_id: str,
        doc_title: str,
        doc_type: str,
    ) -> List[DocumentChunk]:
        ...


SKILL_REGISTRY: Dict[str, ChunkHandler] = {}


def register_content_type_handler(content_type: str, handler: ChunkHandler) -> None:
    SKILL_REGISTRY[content_type] = handler


def handle_narrative_block(
    block: Block,
    *,
    doc_id: str,
    doc_title: str,
    doc_type: str,
) -> List[DocumentChunk]:
    chunk = DocumentChunk(
        doc_id=doc_id,
        doc_title=doc_title,
        section_path=block.heading_path,
        content_type=ContentType.NARRATIVE,
        content=block.raw_text,
        meta={"doc_type": doc_type, "block_id": block.id},
    )
    return [chunk]


def handle_scope_block(
    block: Block,
    *,
    doc_id: str,
    doc_title: str,
    doc_type: str,
) -> List[DocumentChunk]:
    chunk = DocumentChunk(
        doc_id=doc_id,
        doc_title=doc_title,
        section_path=block.heading_path,
        content_type=ContentType.SCOPE,
        content=block.raw_text,
        meta={"doc_type": doc_type, "block_id": block.id},
    )
    return [chunk]


def handle_definition_block(
    block: Block,
    *,
    doc_id: str,
    doc_title: str,
    doc_type: str,
) -> List[DocumentChunk]:
    # For now, treat the whole block as one definition chunk.
    chunk = DocumentChunk(
        doc_id=doc_id,
        doc_title=doc_title,
        section_path=block.heading_path,
        content_type=ContentType.DEFINITION,
        content=block.raw_text,
        meta={"doc_type": doc_type, "block_id": block.id},
    )
    return [chunk]


# Registration
register_content_type_handler(ContentType.NARRATIVE, handle_narrative_block)
register_content_type_handler(ContentType.SCOPE, handle_scope_block)
register_content_type_handler(ContentType.DEFINITION, handle_definition_block)
# TODO: register and implement spec_text, spec_table, method_performance, calculation_formula, test_method
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/kb/test_adaptive_split_handlers.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/adaptive_split.py tests/kb/test_adaptive_split_handlers.py
git commit -m "feat(kb): add adaptive split handlers and registry"
```

---

### Task 5: Implement adaptive_split_markdown core function

**Files:**
- Modify: `app/core/kb/adaptive_split.py`
- Test: `tests/kb/test_adaptive_split_core.py`

**Step 1: Write the failing test**

Create `tests/kb/test_adaptive_split_core.py`:

```python
from pathlib import Path

from app.core.kb.adaptive_split import adaptive_split_markdown
from app.core.kb import DocumentChunk


FIXTURE = Path(__file__).parent.parent / "fixtures" / "gb_standard_sample.md"


def test_adaptive_split_markdown_produces_chunks():
    md_text = FIXTURE.read_text(encoding="utf-8")

    chunks = adaptive_split_markdown(
        md_text,
        doc_id="doc1",
        doc_title="测试标准",
        doc_type="gb_standard",
        options=None,
    )

    assert len(chunks) > 0
    assert all(isinstance(c, DocumentChunk) for c in chunks)
    assert any("范围" in " ".join(c.section_path) for c in chunks)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/kb/test_adaptive_split_core.py -v
```

Expected: FAIL because `adaptive_split_markdown` not implemented or incomplete.

**Step 3: Write minimal implementation**

In `app/core/kb/adaptive_split.py`:

```python
from typing import List


def adaptive_split_markdown(
    md_text: str,
    *,
    doc_id: str,
    doc_title: str,
    doc_type: str,
    options: AdaptiveSplitOptions | None = None,
) -> List[DocumentChunk]:
    blocks = split_markdown_to_blocks(md_text, doc_type=doc_type)
    type_map = classify_blocks_content_type(blocks, doc_type=doc_type)

    chunks: List[DocumentChunk] = []
    for block in blocks:
        ctype = type_map.get(block.id, ContentType.NARRATIVE)
        handler = SKILL_REGISTRY.get(ctype, handle_narrative_block)
        block_chunks = handler(
            block,
            doc_id=doc_id,
            doc_title=doc_title,
            doc_type=doc_type,
        )
        chunks.extend(block_chunks)
    return chunks
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/kb/test_adaptive_split_core.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/adaptive_split.py tests/kb/test_adaptive_split_core.py
git commit -m "feat(kb): wire adaptive_split_markdown core flow"
```

---

### Task 6: Wire adaptive strategy into KB split_step and split_adaptive

**Files:**
- Modify: `app/core/kb/__init__.py`
- Test: `tests/kb/test_kb_split_adaptive_integration.py`

**Step 1: Write the failing test**

Create `tests/kb/test_kb_split_adaptive_integration.py`:

```python
from app.core.kb import split_step, DocumentChunk


def test_split_step_with_adaptive_strategy_smoke():
    # Pretend we already have a DocumentChunk representing a whole markdown doc
    base = DocumentChunk(
        doc_id="doc1",
        doc_title="测试标准",
        section_path=[],
        content_type="raw_markdown",
        content="# 1 范围\n\n本标准适用于某某产品。\n",
        meta={},
    )

    result = split_step(
        [base],
        strategy="adaptive",
        doc_type="gb_standard",
        adaptive_options=None,
    )

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(c, DocumentChunk) for c in result)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/kb/test_kb_split_adaptive_integration.py -v
```

Expected: FAIL because `split_step`/`split_adaptive` don’t support `adaptive` signature yet.

**Step 3: Implement split_step + split_adaptive**

In `app/core/kb/__init__.py`, adjust `split_step` to:

```python
from typing import List, Optional

from app.core.kb import DocumentChunk  # or local import
from app.core.kb.adaptive_split import AdaptiveSplitOptions, adaptive_split_markdown


def split_step(
    documents: List[DocumentChunk],
    strategy: str,
    *,
    doc_type: Optional[str] = None,
    adaptive_options: Optional[AdaptiveSplitOptions] = None,
) -> List[DocumentChunk]:
    if strategy == "structured":
        return split_structured(documents)
    elif strategy == "adaptive":
        return split_adaptive(
            documents,
            doc_type=doc_type,
            options=adaptive_options,
        )
    else:
        return split_text(documents)


def split_adaptive(
    documents: List[DocumentChunk],
    *,
    doc_type: Optional[str],
    options: Optional[AdaptiveSplitOptions],
) -> List[DocumentChunk]:
    # Fallback: if doc_type not provided, treat as generic tech standard
    effective_doc_type = doc_type or "tech_standard_generic"
    result: List[DocumentChunk] = []

    for doc in documents:
        chunks = adaptive_split_markdown(
            doc.content,
            doc_id=doc.doc_id,
            doc_title=doc.doc_title,
            doc_type=effective_doc_type,
            options=options,
        )
        result.extend(chunks)

    return result
```

Adjust imports and existing `split_structured`/`split_text` calls to match your codebase.

**Step 4: Run test to verify it passes**

```bash
pytest tests/kb/test_kb_split_adaptive_integration.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/__init__.py tests/kb/test_kb_split_adaptive_integration.py
git commit -m "feat(kb): integrate adaptive split strategy into KB pipeline"
```

---

### Task 7: Expose adaptive_kb_splitter as an Agent Tool (optional but recommended)

**Files:**
- Create: `app/agents/tools/adaptive_kb_splitter.py` (adjust to your agent/tool layout)
- Modify: any tool registration/config files
- Test: `tests/agents/test_adaptive_kb_splitter_tool.py`

**Step 1: Write the failing test (or smoke test)**

Create `tests/agents/test_adaptive_kb_splitter_tool.py`:

```python
from app.agents.tools.adaptive_kb_splitter import adaptive_kb_splitter_tool


def test_adaptive_kb_splitter_tool_runs_smoke():
    markdown_text = "# 1 范围\n\n本标准适用于某某产品。\n"
    result = adaptive_kb_splitter_tool(
        doc_id="doc1",
        doc_title="测试标准",
        markdown_text=markdown_text,
        doc_type="gb_standard",
        options=None,
    )

    chunks = result["chunks"]
    assert isinstance(chunks, list)
    assert len(chunks) > 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/agents/test_adaptive_kb_splitter_tool.py -v
```

Expected: FAIL because tool not implemented.

**Step 3: Implement the tool wrapper**

In `app/agents/tools/adaptive_kb_splitter.py`:

```python
from typing import Any, Dict, Optional

from app.core.kb.adaptive_split import (
    AdaptiveSplitOptions,
    adaptive_split_markdown,
)


def adaptive_kb_splitter_tool(
    doc_id: str,
    doc_title: str,
    markdown_text: str,
    doc_type: str,
    options: Optional[AdaptiveSplitOptions],
) -> Dict[str, Any]:
    chunks = adaptive_split_markdown(
        markdown_text,
        doc_id=doc_id,
        doc_title=doc_title,
        doc_type=doc_type,
        options=options,
    )
    # Convert DocumentChunk instances to plain dicts if your agent expects JSON
    return {
        "chunks": [c.to_dict() if hasattr(c, "to_dict") else c for c in chunks],
    }
```

Then register this tool in your agent/tool configuration so it can be invoked by name.

**Step 4: Run test to verify it passes**

```bash
pytest tests/agents/test_adaptive_kb_splitter_tool.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/agents/tools/adaptive_kb_splitter.py tests/agents/test_adaptive_kb_splitter_tool.py
git commit -m "feat(agent): expose adaptive_kb_splitter tool"
```

---

### Task 8: Add TODO hooks for MinerU PDF→Markdown and Markdown cleaning

**Files:**
- Modify: `app/core/kb/imports/import_markdown.py`
- Modify: `app/core/kb/imports/import_pdf_via_mineru.py` (or equivalent)

**Step 1: Add TODO comments (no tests required yet)**

In your PDF import path (file name may differ), add a clear TODO near where Markdown is produced:

```python
# TODO(adaptive_kb): ensure pdf -> markdown goes through clean_mineru_markdown(markdown)
# before passing into adaptive_split_markdown / strategy="adaptive".
```

In your Markdown import path:

```python
# TODO(adaptive_kb): when using strategy="adaptive", ensure content has been
# normalized similarly to clean_mineru_markdown to avoid layout noise.
```

**Step 2: Commit**

```bash
git add app/core/kb/imports/import_markdown.py app/core/kb/imports/import_pdf_via_mineru.py
git commit -m "chore(kb): add TODOs for MinerU markdown cleaning integration"
```

---

Plan complete and saved to `docs/plans/2026-03-02-kb-adaptive-impl-plan.md`. Two execution options:

1. **Subagent-Driven (this session)** - I dispatch a fresh subagent per task, we review between tasks，快速迭代完成实现。
2. **Parallel Session (separate)** - 你在新的工作树或会话中，用 executing-plans 按任务批量执行，我这边只做阶段性 review。

你更倾向哪一种执行方式？如果想先「小步试水」，我们也可以只从 Task 1–2 开始实现。

