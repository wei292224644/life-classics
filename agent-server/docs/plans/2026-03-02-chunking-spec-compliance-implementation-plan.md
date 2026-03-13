# 切分规范符合性实施计划（按测试报告 6.3 修改意见）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `cache/chunking_spec_test_report.md` 第 6.3 节建议，补齐国标 Markdown 切分与规范（`docs/plans/2026-03-02-chunking-strategy-spec.md`）的差距：引用展开、文档类型推断、按类型切分与表格识别、content_type 标注、版本元数据、测试断言及报告说明。

**Architecture:** 在现有 `heading_strategy.split_heading_from_markdown` 基础上，先增加「节映射 + 引用识别与展开」与「文档类型推断」两处能力（可抽到独立模块便于单测），再按 inferred_type 分支应用不同切分粒度；表格识别后 3.1 按行、3.3 整表；content_type 与版本元数据在产出 chunk 时写入；最后为 1～2 个样本写规范预期断言并更新报告说明。

**Tech Stack:** Python 3.10+，现有 `app.core.document_chunk.DocumentChunk` / `ContentType`，正则（引用模式、标题、表格），无新增运行时依赖。

**参考:** `docs/plans/2026-03-02-chunking-strategy-spec.md`，`cache/chunking_spec_test_report.md` 第 6 节，`scripts/test_chunking_spec_on_assets.py` 中 `_infer_doc_type` / 引用正则。

---

## Phase 1：P0 引用展开与文档类型推断

### Task 1：文档类型推断函数入仓并单测

**Files:**
- Create: `app/core/kb/strategy/doc_type.py`（提供 `infer_doc_type(filename, first_heading, section_paths) -> str`）
- Create: `tests/core/kb/strategy/test_doc_type.py`
- Modify: 无

**Step 1: Write the failing test**

在 `tests/core/kb/strategy/test_doc_type.py` 中：

```python
from app.core.kb.strategy.doc_type import infer_doc_type


def test_infer_doc_type_single_additive():
    assert infer_doc_type("GB 8821-2011 食品添加剂 β-胡萝卜素.md", "1 范围", [["1 范围"], ["附录 A"]]) == "single_additive"


def test_infer_doc_type_detection_method():
    assert infer_doc_type("GB 5009.33 亚硝酸盐的测定.md", "1 范围", [["第一法 液相色谱法"]]) == "detection_method"


def test_infer_doc_type_microbiological():
    assert infer_doc_type("MinerU_GB_4789.4_沙门氏菌检验.md", None, [["检验程序"]]) == "microbiological"


def test_infer_doc_type_other():
    assert infer_doc_type("硬脂酸钾.md", "概述", [["概述"]]) == "other"
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/wwj/Desktop/self/life-classics/agent-server && uv run pytest tests/core/kb/strategy/test_doc_type.py -v
```
Expected: FAIL (ModuleNotFoundError or import error for doc_type / infer_doc_type).

**Step 3: Write minimal implementation**

创建 `app/core/kb/strategy/doc_type.py`，将 `scripts/test_chunking_spec_on_assets.py` 中 `_infer_doc_type` 逻辑迁入并命名为 `infer_doc_type`，签名 `(filename: str, first_heading: str | None, section_paths: list[list[str]]) -> str`，返回 `single_additive` | `detection_method` | `microbiological` | `product` | `other`。

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/kb/strategy/test_doc_type.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/strategy/doc_type.py tests/core/kb/strategy/test_doc_type.py
git commit -m "feat(kb): add infer_doc_type for chunking spec doc type"
```

---

### Task 2：节号→内容映射（从 Markdown 解析）

**Files:**
- Create: `app/core/kb/strategy/section_map.py`（提供 `build_section_map(markdown_content: str) -> dict[str, str]`，key 为归一化节号如 `A.3.3`，value 为该节正文）
- Create: `tests/core/kb/strategy/test_section_map.py`

**Step 1: Write the failing test**

在 `tests/core/kb/strategy/test_section_map.py` 中：

```python
from app.core.kb.strategy.section_map import build_section_map


def test_section_map_returns_dict():
    md = "## A.3 鉴别\n\n## A.3.3 仪器\n\n紫外分光光度仪。"
    m = build_section_map(md)
    assert isinstance(m, dict)


def test_section_map_resolves_a33():
    md = "# 附录 A\n\n# A.3 鉴别试验\n\n# A.3.3 仪器和设备\n\n紫外分光光度仪。\n\n# A.4 测定"
    m = build_section_map(md)
    # 归一化 key 如 A.3.3，内容应含「紫外」
    found = any("紫外" in v for k, v in m.items() if "3" in k and "3" in k)
    assert found or any("紫外" in v for v in m.values())
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/kb/strategy/test_section_map.py -v
```
Expected: FAIL.

**Step 3: Write minimal implementation**

在 `section_map.py` 中用与 `heading_strategy` 相同的标题正则逐段切分，将「附录 A」「A.3」「A.3.3」等标题归一化为节号（如 `A.3.3`：去空格、统一点号），存入 dict：节号 → 该节从当前标题到下一同级/更高级标题前的正文（不含标题行亦可，与规范 4.2 一致即可）。

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/kb/strategy/test_section_map.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/strategy/section_map.py tests/core/kb/strategy/test_section_map.py
git commit -m "feat(kb): add build_section_map for ref expansion"
```

---

### Task 3：引用识别与展开 + ref_section_code 写入 meta

**Files:**
- Create: `app/core/kb/strategy/ref_expand.py`（提供 `expand_refs_in_content(content: str, section_map: dict[str, str]) -> tuple[str, list[str]]`，返回展开后文本与已解析的 ref_section_code 列表）
- Create: `tests/core/kb/strategy/test_ref_expand.py`

**Step 1: Write the failing test**

```python
from app.core.kb.strategy.ref_expand import expand_refs_in_content


def test_expand_refs_appends_content():
    content = "仪器和设备\n\n同 A.3.3。"
    section_map = {"A.3.3": "紫外分光光度仪。石英池（1 cm）。"}
    expanded, refs = expand_refs_in_content(content, section_map)
    assert "A.3.3" in refs
    assert "紫外" in expanded or "石英" in expanded


def test_expand_refs_returns_ref_section_codes():
    content = "同 A.3.3。"
    section_map = {"A.3.3": "仪器：紫外。"}
    _, refs = expand_refs_in_content(content, section_map)
    assert "A.3.3" in refs
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/kb/strategy/test_ref_expand.py -v
```
Expected: FAIL.

**Step 3: Write minimal implementation**

在 `ref_expand.py` 中用规范 4.1 的引用模式（同 A.x.x、按 A.x、见 X.X 等）匹配，从 `section_map` 用归一化节号取内容，在引用句后追加「（引用自 A.x.x：…）」或直接段落；收集所有成功解析的节号列表作为 `ref_section_code`；未解析到的可记入另一列表供 `ref_section_code_unresolved`（可选）。保留原引用句。

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/kb/strategy/test_ref_expand.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/strategy/ref_expand.py tests/core/kb/strategy/test_ref_expand.py
git commit -m "feat(kb): add expand_refs_in_content and ref_section_code"
```

---

### Task 4：在 split_heading_from_markdown 中接入节映射与引用展开

**Files:**
- Modify: `app/core/kb/strategy/heading_strategy.py`（在产出每个 chunk 后，用 `build_section_map` 得到 section_map，对该 chunk 的 content 调用 `expand_refs_in_content`，用展开后文本替换 content，并将 `ref_section_code` 写入该 chunk 的 `meta`）
- Modify: `tests/core/kb/strategy/test_heading_strategy.py`（增加一条：含「同 A.3.3」且 section_map 中有 A.3.3 时，chunk.content 含展开内容且 meta 含 ref_section_code）

**Step 1: Write the failing test**

在 `test_heading_strategy.py` 末尾添加：

```python
def test_heading_split_expands_refs_and_meta():
    md = "# A.3 鉴别\n\n# A.3.3 仪器\n\n紫外分光光度仪。\n\n# A.4 测定\n\n同 A.3.3。"
    chunks = split_heading_from_markdown(md, doc_id="d3", doc_title="t", source="t.md")
    chunk_with_ref = next((c for c in chunks if "同" in (c.content or "") and "A" in (c.content or "")), None)
    assert chunk_with_ref is not None
    assert chunk_with_ref.meta.get("ref_section_code") is not None
    assert "紫外" in (chunk_with_ref.content or "")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/kb/strategy/test_heading_strategy.py::test_heading_split_expands_refs_and_meta -v
```
Expected: FAIL（当前未做展开或未写 meta）。

**Step 3: Write minimal implementation**

在 `heading_strategy.py` 的 `split_heading_from_markdown` 中：先按现有逻辑生成 chunks；对整份 `markdown_content` 调用 `build_section_map` 一次；遍历每个 chunk，对 `chunk.content` 调用 `expand_refs_in_content(content, section_map)`，将返回的展开文本写回 chunk.content，并将返回的 ref 列表写入 `chunk.meta["ref_section_code"]`（若有）。

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/kb/strategy/test_heading_strategy.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/strategy/heading_strategy.py tests/core/kb/strategy/test_heading_strategy.py
git commit -m "feat(kb): wire ref expansion and ref_section_code into split_heading_from_markdown"
```

---

### Task 5：在流水线中按文档类型分支（仅先分支，仍用标题切分）

**Files:**
- Modify: `app/core/kb/strategy/heading_strategy.py`（在 `split_heading_from_markdown` 开头或产出 chunks 前，调用 `infer_doc_type(source, first_heading, section_paths)`，将 `inferred_type` 写入每个 chunk 的 `meta`，便于后续 P1 按类型换策略）
- Modify: `tests/core/kb/strategy/test_heading_strategy.py`（断言某文件得到的 chunks 的 meta 中含 `inferred_type`）

**Step 1: Write the failing test**

在 `test_heading_strategy.py` 中添加：

```python
def test_heading_split_puts_inferred_type_in_meta():
    md = "## 1 范围\n\n本标准适用于食品添加剂。"
    chunks = split_heading_from_markdown(md, doc_id="d4", doc_title="GB 8821", source="GB 8821-2011 食品添加剂.md")
    assert len(chunks) >= 1
    assert chunks[0].meta.get("inferred_type") in ("single_additive", "detection_method", "microbiological", "product", "other")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/kb/strategy/test_heading_strategy.py::test_heading_split_puts_inferred_type_in_meta -v
```
Expected: FAIL（meta 尚无 inferred_type）。

**Step 3: Write minimal implementation**

在 `split_heading_from_markdown` 中生成 chunks 后，先算 `section_paths = [c.section_path for c in chunks]` 与 `first_heading = section_paths[0][0] if section_paths and section_paths[0] else None`，调用 `infer_doc_type(source, first_heading, section_paths)`，对每个 chunk 执行 `chunk.meta["inferred_type"] = inferred_type`。

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/kb/strategy/test_heading_strategy.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/strategy/heading_strategy.py tests/core/kb/strategy/test_heading_strategy.py
git commit -m "feat(kb): add inferred_type to chunk meta in split_heading_from_markdown"
```

---

## Phase 2：P1 按类型切分粒度与表格识别

### Task 6：表格识别（Markdown 表 + HTML table）

**Files:**
- Create: `app/core/kb/strategy/table_utils.py`（提供 `find_tables_in_text(text: str) -> list[dict]`，每个 dict 含 `start`, `end`, `raw` 或 `rows`，便于后续按行/整表切块）
- Create: `tests/core/kb/strategy/test_table_utils.py`

**Step 1: Write the failing test**

```python
from app.core.kb.strategy.table_utils import find_tables_in_text


def test_find_tables_detects_markdown_table():
    text = "表 1\n\n| 项目 | 指标 |\n|------|------|\n| 水分 | ≤0.2 |"
    tables = find_tables_in_text(text)
    assert len(tables) >= 1
    assert "项目" in str(tables[0]) or "水分" in str(tables[0])


def test_find_tables_detects_html_table():
    text = "表 2\n\n<table><tr><td>A</td></tr></table>"
    tables = find_tables_in_text(text)
    assert len(tables) >= 1
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/kb/strategy/test_table_utils.py -v
```
Expected: FAIL.

**Step 3: Write minimal implementation**

用正则或简单扫描识别 `|...|` 行（Markdown 表）和 `<table>...</table>`（HTML），返回每段表格在文本中的起止位置及原始片段（或解析为 rows），供 3.1 按行、3.3 整表使用。

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/core/kb/strategy/test_table_utils.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add app/core/kb/strategy/table_utils.py tests/core/kb/strategy/test_table_utils.py
git commit -m "feat(kb): add find_tables_in_text for spec 3.1/3.3 table handling"
```

---

### Task 7：single_additive 技术指标表按行产出 chunk（3.1）

**Files:**
- Modify: `app/core/kb/strategy/heading_strategy.py` 或新建 `app/core/kb/strategy/type_strategies.py`（实现 `split_single_additive(markdown_content, doc_id, doc_title, source, markdown_id) -> list[DocumentChunk]`：先按标题切分，对「技术指标表」段用 `find_tables_in_text` 识别表，按行产出多个 chunk，content_type=SPECIFICATION_TABLE，表头+该行；其余段仍按标题块）
- Add test in `tests/core/kb/strategy/test_heading_strategy.py` 或新建 `tests/core/kb/strategy/test_type_strategies.py`：对含「表 2 理化指标」和至少两行数据的 MD，断言有至少 2 个 SPECIFICATION_TABLE chunk 且 section_path 含表所在节

**Step 1: Write the failing test**

使用 `docs/assets/GB 8821-2011 食品安全国家标准 食品添加剂 β-胡萝卜素.md` 或内联简短 MD（含「表 2」「| 项目 | 指标 |」及多行），调用 `split_heading_from_markdown` 或新入口，断言存在 `content_type==SPECIFICATION_TABLE` 的 chunk 且数量 ≥ 表行数。

**Step 2: Run test to verify it fails**

（当前 `split_heading_from_markdown` 未按类型分支，无 SPECIFICATION_TABLE。）

**Step 3: Write minimal implementation**

在 `split_heading_from_markdown` 中：若 `infer_doc_type` 为 `single_additive`，对每个标题块用 `find_tables_in_text` 找表，若为该节「技术指标表」（可由标题或表前一行含「表 1」「表 2」判断），则将该表按行拆成多个 DocumentChunk（表头 + 该行），content_type=ContentType.SPECIFICATION_TABLE；非表部分保持原块。其他类型暂不改变行为。

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git commit -m "feat(kb): single_additive spec table row-level chunks per spec 3.1"
```

---

### Task 8：detection_method 按「第 N 法」+ 方法内功能块（3.2 简化）

**Files:**
- Modify: `app/core/kb/strategy/heading_strategy.py` 或 `type_strategies.py`（当 inferred_type==detection_method 时，先按「第一法」「第二法」等切大块，再在每个「第 N 法」内按标题或功能段落切子块；若实现成本高，可先只做「按第 N 法」大块，功能块仍按标题）
- Add test：含「第一法 液相色谱法」的 MD 至少有一个 chunk 的 section_path 或 content 含「第一法」

**Step 1–5:** 同上 TDD 节奏，先写失败用例再实现再提交。

```bash
git commit -m "feat(kb): detection_method split by 第N法 per spec 3.2"
```

---

### Task 9：microbiological 流程图单块与判定表整表（3.3 简化）

**Files:**
- Modify: 同上（当 inferred_type==microbiological 时，识别「检验程序」或流程图标题为单块；判定表用 `find_tables_in_text` 整表一块，content_type=SPECIFICATION_TABLE）
- Add test：GB 4789.4 类 MD 中至少有一个 SPECIFICATION_TABLE chunk 或「检验程序」单块

**Step 1–5:** TDD，提交。

```bash
git commit -m "feat(kb): microbiological flowchart and table chunking per spec 3.3"
```

---

## Phase 3：P2 content_type、版本元数据与测试断言

### Task 10：按块内容标注 content_type（规范第 7 节）

**Files:**
- Modify: `app/core/kb/strategy/heading_strategy.py` 或各 type_strategies（在产出 chunk 时，根据 section_path 或内容关键词设 content_type：如「1 范围」→ SCOPE，「表」→ SPECIFICATION_TABLE，「试剂」→ REAGENT，「仪器」→ INSTRUMENT，「结果计算」→ CALCULATION_FORMULA，方法名→ TEST_METHOD，其余 GENERAL_RULE）
- Modify: `tests/core/kb/strategy/test_heading_strategy.py`：断言某 MD 中至少有一个 chunk 的 content_type 不是 GENERAL_RULE（例如 SCOPE 或 SPECIFICATION_TABLE）

**Step 1–5:** TDD，提交。

```bash
git commit -m "feat(kb): assign content_type by block content per spec 7"
```

---

### Task 11：导入流水线写入版本元数据（规范 6.2）

**Files:**
- Modify: `app/core/kb/__init__.py`（在 `import_pdf_via_mineru` 或调用 `split_heading_from_markdown` 后，从 `original_filename` 或配置解析 standard_no、standard_year，写入每个 chunk 的 meta：standard_no、standard_year、standard_version 等；解析规则可用正则如 `GB\s*(\d+)`、`-(\d{4})`）
- Add test：对文件名含 GB 8821-2011 的导入，chunks 的 meta 含 standard_no 与 standard_year

**Step 1–5:** TDD，提交。

```bash
git commit -m "feat(kb): inject standard_no, standard_year into chunk meta on import"
```

---

### Task 12：规范预期断言（GB 8821 或 GB 4789.4 样本）

**Files:**
- Modify: `scripts/test_chunking_spec_on_assets.py` 或新建 `tests/integration/test_chunking_spec_sample.py`（对 `docs/assets/GB 8821-2011 食品安全国家标准 食品添加剂 β-胡萝卜素.md` 读入并调用 `split_heading_from_markdown`，断言：chunk 数在合理区间、存在 ref_section_code 非空的 chunk、存在 content_type 为 SPECIFICATION_TABLE 的 chunk；对 GB 4789.4 样本断言存在「检验程序」或判定表相关 chunk）
- Modify: `cache/chunking_spec_test_report.md`（在报告开头增加一句：「本测试为规范符合性审计，当前实现尚未完成规范全部要求；实现本计划后可用集成断言做回归。」）

**Step 1: Write the failing test**

在 `tests/integration/test_chunking_spec_sample.py` 中：

```python
from pathlib import Path
from app.core.kb.strategy.heading_strategy import split_heading_from_markdown

ASSETS = Path(__file__).resolve().parents[2] / "docs" / "assets"


def test_gb8821_has_ref_expanded_and_spec_table():
    path = ASSETS / "GB 8821-2011 食品安全国家标准 食品添加剂 β-胡萝卜素.md"
    if not path.exists():
        return  # 跳过无文件环境
    md = path.read_text(encoding="utf-8", errors="replace")
    chunks = split_heading_from_markdown(md, doc_id="gb8821", doc_title=path.stem, source=path.name)
    assert len(chunks) >= 10
    assert any(c.meta.get("ref_section_code") for c in chunks)
    assert any(getattr(c.content_type, "value", str(c.content_type)) == "specification_table" for c in chunks)
```

**Step 2: Run test to verify it fails**

（若当前无 SPECIFICATION_TABLE 或 ref_section_code 未全覆盖，可能 FAIL；若已实现则 PASS。）

**Step 3–4:** 根据需要调整实现或断言阈值，确保通过。

**Step 5: Commit**

```bash
git add tests/integration/test_chunking_spec_sample.py cache/chunking_spec_test_report.md
git commit -m "test(kb): add spec compliance sample assertions and report note"
```

---

### Task 13：报告开头注明「规范符合性审计、未完成全部要求」（P3）

**Files:**
- Modify: `cache/chunking_spec_test_report.md`（在「国标 Markdown 切分规范符合性测试报告」标题下、概览前增加一段说明：本测试为规范符合性审计，当前实现尚未完成规范全部要求；实现本计划后可用集成断言与本文档 6.3 建议做回归。）

**Step 1:** 已与 Task 12 一并写入报告说明。

**Step 2–5:** 若未在 Task 12 中修改，则单独在报告第 1 节前插入上述说明并提交。

```bash
git add cache/chunking_spec_test_report.md
git commit -m "docs: note chunking report is compliance audit, not full spec"
```

---

## 执行顺序与验收

- **顺序:** Task 1 → 2 → 3 → 4 → 5（P0）；Task 6 → 7 → 8 → 9（P1）；Task 10 → 11 → 12 → 13（P2/P3）。
- **验收:** 全量跑 `uv run pytest tests/core/kb/ tests/integration/ -v` 通过；对 `docs/assets` 中 GB 8821、GB 4789.4 等样本重跑 `scripts/test_chunking_spec_on_assets.py`，报告中「含引用块数」「含表格块数」与规范预期一致或改进；报告开头已注明审计性质与未完成项。

---

## 执行方式选择

计划已保存至 `docs/plans/2026-03-02-chunking-spec-compliance-implementation-plan.md`。两种执行方式：

1. **Subagent-Driven（本会话）**：按任务派发子 agent，每任务后 review，快速迭代。
2. **Parallel Session（新会话）**：在新会话中用 executing-plans，按检查点批量执行。

请选择一种方式。
