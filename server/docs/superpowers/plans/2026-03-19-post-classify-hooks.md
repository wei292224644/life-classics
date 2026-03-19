# Post-Classify Hooks 架构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 classify 阶段现有的两个私有 merge 函数提取为独立的 hook 注册表，同时新增两个 hook 修复公式导言分离和步骤段落+列表分离问题。

**Architecture:** 新建 `post_classify_hooks.py`，定义 `PostClassifyHook` 类型和 `POST_CLASSIFY_HOOKS` 注册列表。`classify_node.py` 移除私有 merge 函数，改为循环执行注册表中的所有 hook。每个 hook 是纯函数 `(list[TypedSegment]) -> list[TypedSegment]`，互相独立，顺序执行。

**Tech Stack:** Python，无新依赖，纯函数变换。

---

## 文件结构

| 操作 | 路径 | 说明 |
|------|------|------|
| 创建 | `app/core/parser_workflow/post_classify_hooks.py` | Hook 注册表 + 全部 4 个 hook 实现 |
| 修改 | `app/core/parser_workflow/nodes/classify_node.py` | 移除私有 merge 函数，改为执行 hook 注册表 |
| 创建 | `tests/core/parser_workflow/test_post_classify_hooks.py` | 全部 hook 的单元测试（含迁移自 unit 测试的现有 merge 测试） |
| 修改 | `tests/core/parser_workflow/test_classify_node_unit.py` | 更新 import 路径，移除已迁移的 merge 测试 |

---

## Task 1：创建 post_classify_hooks.py（含 4 个 hook + 注册表）

**Files:**
- Create: `app/core/parser_workflow/post_classify_hooks.py`

- [ ] **Step 1：写失败测试——merge_formula_preamble（新 hook）**

在 `tests/core/parser_workflow/test_post_classify_hooks.py` 写：

```python
import pytest
from app.core.parser_workflow.models import TypedSegment
from app.core.parser_workflow.post_classify_hooks import (
    merge_formula_preamble,
    merge_procedure_list,
    POST_CLASSIFY_HOOKS,
)

_CALC_PARAMS = {
    "strategy": "formula_embed",
    "prompt_template": "将以下计算公式及变量说明转化为可检索的混合文本。",
}
_PLAIN_PARAMS = {
    "strategy": "plain_embed",
    "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
}


def _seg(content, structure_type, semantic_type, params=None) -> TypedSegment:
    return TypedSegment(
        content=content,
        structure_type=structure_type,
        semantic_type=semantic_type,
        transform_params=params or _PLAIN_PARAMS,
        confidence=0.95,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )


FORMULA = "$$\nX = \\frac{C \\times V}{m}\n$$\n\n式中：\n\nX——残留量，μg/kg；\nC——浓度，ng/mL；\nV——体积，mL；\nm——质量，g。"
PREAMBLE = "试料中甲砜霉素的残留量（μg/kg）按下式计算："


def test_merge_formula_preamble_merges_preamble_and_formula():
    """calculation paragraph 紧随 formula segment 时应合并为一个 formula segment。"""
    segments = [
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 1
    assert result[0]["structure_type"] == "formula"
    assert result[0]["semantic_type"] == "calculation"
    assert PREAMBLE in result[0]["content"]
    assert FORMULA in result[0]["content"]


def test_merge_formula_preamble_no_merge_when_different_semantic():
    """paragraph.semantic_type != formula.semantic_type 时不合并。"""
    segments = [
        _seg("步骤说明段落", "paragraph", "procedure"),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 2


def test_merge_formula_preamble_no_merge_when_not_adjacent_formula():
    """calculation paragraph 后面不是 formula 时不合并。"""
    segments = [
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg("其他段落内容", "paragraph", "calculation", _CALC_PARAMS),
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 2


def test_merge_formula_preamble_preserves_surrounding():
    """只合并匹配对，前后 segment 原样保留。"""
    before = _seg("前置说明", "paragraph", "procedure")
    after = _seg("结果注意事项", "paragraph", "limit")
    segments = [
        before,
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
        after,
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 3
    assert result[0]["content"] == before["content"]
    assert result[2]["content"] == after["content"]


# ── merge_procedure_list ────────────────────────────────────────────────────

PROC_INTRO = "取适量新鲜或冷藏的空白或供试牛奶，混合均匀。"
PROC_LIST = "取均质后的供试样品，作为供试试料。取均质后的空白样品，作为空白试料。"


def test_merge_procedure_list_merges_intro_and_list():
    """procedure paragraph + procedure list 相邻时应合并为一个 list segment。"""
    segments = [
        _seg(PROC_INTRO, "paragraph", "procedure"),
        _seg(PROC_LIST, "list", "procedure"),
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 1
    assert result[0]["structure_type"] == "list"
    assert result[0]["semantic_type"] == "procedure"
    assert PROC_INTRO in result[0]["content"]
    assert PROC_LIST in result[0]["content"]


def test_merge_procedure_list_no_merge_different_semantic():
    """paragraph.semantic_type != list.semantic_type 时不合并。"""
    segments = [
        _seg("通用试剂说明", "paragraph", "material"),
        _seg(PROC_LIST, "list", "procedure"),
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 2


def test_merge_procedure_list_no_merge_same_type_not_list():
    """procedure paragraph + procedure paragraph（不是 list）不合并。"""
    segments = [
        _seg(PROC_INTRO, "paragraph", "procedure"),
        _seg("另一段步骤说明", "paragraph", "procedure"),
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 2


def test_merge_procedure_list_preserves_surrounding():
    """只合并匹配对，前后 segment 原样保留。"""
    before = _seg("章节标题", "header", "metadata")
    after = _seg("保存条件", "paragraph", "procedure")
    segments = [
        before,
        _seg(PROC_INTRO, "paragraph", "procedure"),
        _seg(PROC_LIST, "list", "procedure"),
        after,
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 3
    assert result[0]["content"] == before["content"]
    assert result[2]["content"] == after["content"]


# ── 跨 hook 链式合并 ─────────────────────────────────────────────────────────

def test_hooks_chain_preamble_formula_variables():
    """三段连续：导言 → 公式 → 变量说明，两个 hook 依次执行后应合并为一个 segment。

    hook 1 (merge_formula_preamble) 先将导言+公式合并为 formula segment，
    hook 2 (merge_formula_with_variables) 再将合并结果与变量说明合并。
    """
    from app.core.parser_workflow.post_classify_hooks import (
        merge_formula_with_variables,
        POST_CLASSIFY_HOOKS,
    )

    VARIABLES = "式中：\n\nX——残留量，μg/kg；\nC——浓度，ng/mL；"
    segments = [
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
        _seg(VARIABLES, "list", "calculation", _CALC_PARAMS),
    ]

    # 模拟 POST_CLASSIFY_HOOKS 中 hook1 → hook2 的执行顺序
    result = segments
    for hook in [merge_formula_preamble, merge_formula_with_variables]:
        result = hook(result)

    assert len(result) == 1
    assert result[0]["structure_type"] == "formula"
    assert PREAMBLE in result[0]["content"]
    assert FORMULA in result[0]["content"]
    assert VARIABLES in result[0]["content"]


# ── POST_CLASSIFY_HOOKS 注册表 ───────────────────────────────────────────────

def test_post_classify_hooks_is_list_of_callables():
    """POST_CLASSIFY_HOOKS 应是可调用函数的列表。"""
    assert isinstance(POST_CLASSIFY_HOOKS, list)
    assert all(callable(h) for h in POST_CLASSIFY_HOOKS)
    assert len(POST_CLASSIFY_HOOKS) == 4


def test_post_classify_hooks_contains_all_four():
    """注册表应包含全部 4 个 hook（顺序不限）。"""
    from app.core.parser_workflow.post_classify_hooks import (
        merge_formula_preamble,
        merge_formula_with_variables,
        merge_procedure_list,
        merge_short_segments,
    )
    for hook in [merge_formula_preamble, merge_formula_with_variables,
                 merge_procedure_list, merge_short_segments]:
        assert hook in POST_CLASSIFY_HOOKS
```

- [ ] **Step 2：运行测试确认失败**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_post_classify_hooks.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.parser_workflow.post_classify_hooks'`

- [ ] **Step 3：创建 post_classify_hooks.py**

创建 `app/core/parser_workflow/post_classify_hooks.py`：

```python
"""Post-classify segment merge hooks.

每个 hook 是一个纯函数，签名为：
    (list[TypedSegment]) -> list[TypedSegment]

在 classify_raw_chunk() 完成 LLM 分类后，按 POST_CLASSIFY_HOOKS 的顺序
依次执行，对 segments 做确定性修正。

添加新 hook：
  1. 在本文件末尾定义函数，写清触发条件和合并逻辑
  2. 将函数名追加到 POST_CLASSIFY_HOOKS 列表（注意顺序）
"""

from __future__ import annotations

from typing import Callable, List

from app.core.parser_workflow.models import TypedSegment

PostClassifyHook = Callable[[List[TypedSegment]], List[TypedSegment]]


def merge_formula_preamble(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将计算导言段落与其后紧邻的公式 segment 合并。

    触发条件（同时满足）：
    - 当前 segment：structure_type=paragraph, semantic_type=calculation
    - 下一 segment：structure_type=formula,   semantic_type=calculation

    GB 标准中"按下式计算："这类导言句和公式体是同一语义单元，
    LLM 有时会将两者切分为相邻的两个 segment。
    合并后 structure_type 取 formula，保留计算类语义。
    """
    result: List[TypedSegment] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if (
            seg["structure_type"] == "paragraph"
            and seg["semantic_type"] == "calculation"
            and i + 1 < len(segments)
            and segments[i + 1]["structure_type"] == "formula"
            and segments[i + 1]["semantic_type"] == "calculation"
        ):
            next_seg = segments[i + 1]
            result.append(
                TypedSegment(
                    **{
                        **next_seg,  # formula segment 的 transform_params 为主
                        "content": seg["content"] + "\n\n" + next_seg["content"],
                    }
                )
            )
            i += 2
        else:
            result.append(seg)
            i += 1
    return result


def merge_formula_with_variables(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将 formula segment 与其后紧邻的变量说明 segment 合并。

    触发条件（同时满足）：
    - 当前 segment：structure_type=formula
    - 下一 segment：semantic_type=calculation，content 以"式中"开头

    GB 标准中公式块（$$...$$）和变量说明（式中：m1——...）是同一语义单元，
    但 LLM 有时会将两者切分为相邻的两个 segment。
    """
    result: List[TypedSegment] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if (
            seg["structure_type"] == "formula"
            and i + 1 < len(segments)
            and segments[i + 1]["semantic_type"] == "calculation"
            and segments[i + 1]["content"].lstrip().startswith("式中")
        ):
            next_seg = segments[i + 1]
            result.append(
                TypedSegment(
                    **{
                        **seg,
                        "content": seg["content"] + "\n\n" + next_seg["content"],
                    }
                )
            )
            i += 2
        else:
            result.append(seg)
            i += 1
    return result


def merge_procedure_list(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将步骤介绍段落与其后紧邻的步骤列表 segment 合并。

    触发条件（同时满足）：
    - 当前 segment：structure_type=paragraph, semantic_type=procedure
    - 下一 segment：structure_type=list,      semantic_type=procedure

    GB 标准中"取适量...混合均匀。"这类总说明句和其后的——列表项
    是同一步骤的整体，LLM 有时将两者分为相邻 segment。
    合并后 structure_type 取 list（列表项更具体，检索价值更高）。
    """
    result: List[TypedSegment] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if (
            seg["structure_type"] == "paragraph"
            and seg["semantic_type"] == "procedure"
            and i + 1 < len(segments)
            and segments[i + 1]["structure_type"] == "list"
            and segments[i + 1]["semantic_type"] == "procedure"
        ):
            next_seg = segments[i + 1]
            result.append(
                TypedSegment(
                    **{
                        **next_seg,  # list segment 的 transform_params 为主
                        "content": seg["content"] + "\n\n" + next_seg["content"],
                    }
                )
            )
            i += 2
        else:
            result.append(seg)
            i += 1
    return result


_MERGE_SHORT_THRESHOLD = 60


def merge_short_segments(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将相邻且 semantic_type 相同的短 segment 合并，避免生成无独立检索价值的碎片 chunk。

    左向扫描：若当前 segment 长度 < 阈值，且与前一个 segment 的 semantic_type 相同，
    则并入前一个。单次 O(n) 扫描即可处理任意长度的连续短 segment 链。
    """
    result: List[TypedSegment] = []
    for seg in segments:
        if (
            result
            and result[-1]["semantic_type"] == seg["semantic_type"]
            and len(seg["content"]) < _MERGE_SHORT_THRESHOLD
        ):
            result[-1] = TypedSegment(
                **{
                    **result[-1],
                    "content": result[-1]["content"] + "\n\n" + seg["content"],
                }
            )
        else:
            result.append(seg)
    return result


# Hook 注册表 —— 顺序执行，先合并结构性单元，最后处理碎片
POST_CLASSIFY_HOOKS: List[PostClassifyHook] = [
    merge_formula_preamble,        # 1. 导言+公式合并（避免产生孤立导言碎片）
    merge_formula_with_variables,  # 2. 公式+变量说明合并
    merge_procedure_list,          # 3. 步骤说明+步骤列表合并
    merge_short_segments,          # 4. 最后清理剩余短碎片
]
```

- [ ] **Step 4：运行测试确认通过**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_post_classify_hooks.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 5：commit**

```bash
git add app/core/parser_workflow/post_classify_hooks.py \
        tests/core/parser_workflow/test_post_classify_hooks.py
git commit -m "feat(parser): add post_classify_hooks registry with formula-preamble and procedure-list merge hooks"
```

---

## Task 2：更新 classify_node.py 使用 hook 注册表

**Files:**
- Modify: `app/core/parser_workflow/nodes/classify_node.py`
- Modify: `tests/core/parser_workflow/test_classify_node_unit.py`

- [ ] **Step 1：写回归测试——classify_node 仍正确执行所有 hook**

在 `tests/core/parser_workflow/test_classify_node_unit.py` 末尾追加：

```python
def test_classify_node_applies_all_hooks(tmp_path):
    """classify_node 应通过 POST_CLASSIFY_HOOKS 注册表应用所有 hook。

    回归测试：确保重构后 hook 仍被执行（以 merge_formula_with_variables 为例）。
    公式 segment 后紧跟"式中..."时，最终应合并为一个 segment。
    """
    formula_content = "$$\nX = C \\times V / m\n$$"
    var_content = "式中：\n\nX——残留量；\nC——浓度；\nV——体积；\nm——质量。"

    mock_output = ClassifyOutput(segments=[
        SegmentItem(
            content=formula_content,
            structure_type="formula",
            semantic_type="calculation",
            confidence=0.99,
        ),
        SegmentItem(
            content=var_content,
            structure_type="list",
            semantic_type="calculation",
            confidence=0.98,
        ),
    ])

    with patch(
        "app.core.parser_workflow.nodes.classify_node.invoke_structured",
        return_value=mock_output,
    ):
        state = _make_state(formula_content + "\n\n" + var_content, tmp_path)
        result = classify_node(state)

    segments = result["classified_chunks"][0]["segments"]
    assert len(segments) == 1, "公式与变量说明应已合并为一个 segment"
    assert segments[0]["structure_type"] == "formula"
```

- [ ] **Step 2：运行测试确认当前仍通过**（基线验证，重构前应全部 PASS）

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py -v
```

Expected: 所有测试 PASS（含新加的回归测试）

- [ ] **Step 3：重构 classify_node.py**

修改 `app/core/parser_workflow/nodes/classify_node.py`：

**删除**：
- `_MERGE_SHORT_THRESHOLD = 60`（第 71 行）
- `_merge_short_segments()` 函数（第 74-95 行）
- `_merge_formula_with_variables()` 函数（第 98-127 行）

**在文件顶部 import 区域追加**：
```python
from app.core.parser_workflow.post_classify_hooks import POST_CLASSIFY_HOOKS
```

**替换** `classify_raw_chunk()` 函数末尾的两行 merge 调用：
```python
# 删除这两行：
segments = _merge_formula_with_variables(segments)
segments = _merge_short_segments(segments)

# 替换为：
for hook in POST_CLASSIFY_HOOKS:
    segments = hook(segments)
```

最终 `classify_raw_chunk()` 函数末尾应为：

```python
    for hook in POST_CLASSIFY_HOOKS:
        segments = hook(segments)

    return ClassifiedChunk(
        raw_chunk=raw_chunk,
        segments=segments,
        has_unknown=has_unknown,
    )
```

- [ ] **Step 4：更新 test_classify_node_unit.py——迁移 merge 测试并更新 import**

**4a. 删除已迁移到 test_post_classify_hooks.py 的测试函数**（共 15 个，位于文件第 194-402 行的两个 section）：

```
# 删除 "── _merge_formula_with_variables ──" section 下的全部函数：
test_merge_formula_splits_merged_when_separated
test_merge_formula_no_change_when_already_merged
test_merge_formula_two_consecutive_formulas
test_merge_formula_skips_non_shizong_calculation_list
test_merge_formula_preserves_surrounding_segments

# 删除 "── _merge_short_segments ──" section 下的全部函数：
test_merge_short_merges_same_semantic_both_short
test_merge_short_short_after_long_merges_in
test_merge_short_short_before_long_stays_separate
test_merge_short_no_merge_both_long
test_merge_short_no_merge_different_semantic
test_merge_short_cascades_multiple_short
test_merge_short_preserves_content
test_merge_short_keeps_first_segment_metadata
test_merge_short_long_boundary_between_short_groups

# 同时删除这两个 section 用到的辅助函数和常量：
_formula_seg, _var_seg, _para_seg, _mat_seg, _proc_seg
FORMULA, VARIABLES, SHORT, LONG（第 207-319 行）
_CALC_PARAMS, _PLAIN_PARAMS（若仅被 merge 测试使用则一并删除；
  若其他测试也用到则保留）
```

**4b. 更新 import**，将文件顶部的 import 从：
```python
from app.core.parser_workflow.nodes.classify_node import (
    classify_node,
    _escape_for_json_prompt,
    _merge_formula_with_variables,
    _merge_short_segments,
    _MERGE_SHORT_THRESHOLD,
)
```
改为：
```python
from app.core.parser_workflow.nodes.classify_node import (
    classify_node,
    _escape_for_json_prompt,
)
```

`_CALC_PARAMS` 和 `_PLAIN_PARAMS` 若被保留的测试用到，保持原位不动。

- [ ] **Step 5：运行全部相关测试确认通过**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py \
              tests/core/parser_workflow/test_post_classify_hooks.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 6：commit**

```bash
git add app/core/parser_workflow/nodes/classify_node.py \
        tests/core/parser_workflow/test_classify_node_unit.py
git commit -m "refactor(parser): wire classify_node to POST_CLASSIFY_HOOKS registry"
```

---

## 注意事项

- `_MERGE_SHORT_THRESHOLD` 常量从 `classify_node.py` 移至 `post_classify_hooks.py`，如有其他地方引用需同步更新（当前代码中只有测试文件引用）
- hook 的执行顺序有语义含义：先做结构合并（导言+公式、公式+变量说明、步骤+列表），最后才清理碎片——不要随意调换顺序
- 新增 hook 时：在 `post_classify_hooks.py` 末尾定义函数，追加到 `POST_CLASSIFY_HOOKS` 列表，在 `test_post_classify_hooks.py` 补充测试，更新 `test_post_classify_hooks_contains_all_four` 中的数量断言
