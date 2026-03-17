# slice_node soft_max 语义修复 + 空头 chunk 过滤 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `recursive_slice` 中 `soft_max` 被误用为强制拆分阈值、以及仅含标题行的 block 不被过滤的两个问题。

**Architecture:** 在 `slice_node.py` 中新增 `_has_body_content` 纯函数，并修改 `recursive_slice` 的 else 分支逻辑。只修改一个文件，不改变任何外部接口。

**Tech Stack:** Python 3.x, pytest

---

## 文件结构

| 文件 | 操作 | 说明 |
|---|---|---|
| `agent-server/app/core/parser_workflow/nodes/slice_node.py` | **修改** | 新增 `_has_body_content`；修改 `recursive_slice` 第 68-85 行 |
| `agent-server/tests/core/parser_workflow/test_slice_node.py` | **新建** | 7 个单元测试用例，全部覆盖修改路径 |

---

## Task 1：新建测试文件，写 `_has_body_content` 相关测试

**Files:**
- Create: `agent-server/tests/core/parser_workflow/test_slice_node.py`

- [ ] **Step 1：新建测试文件，写 `_has_body_content` 的测试**

  创建 `agent-server/tests/core/parser_workflow/test_slice_node.py`，内容如下：

  ```python
  from __future__ import annotations

  import pytest

  from app.core.parser_workflow.nodes.slice_node import (
      _has_body_content,
      recursive_slice,
  )


  # ── _has_body_content ────────────────────────────────────────────────


  def test_has_body_content_heading_only_returns_false():
      """仅含标题行的 block 应返回 False"""
      block = "## A.9 残留溶剂（异丙醇、甲醇）的测定\n\n"
      assert _has_body_content(block) is False


  def test_has_body_content_with_body_returns_true():
      """含实质内容的 block 应返回 True"""
      block = "## 3.1 定义\n\n本标准中所用术语定义如下。\n"
      assert _has_body_content(block) is True


  def test_has_body_content_multiple_headings_only_returns_false():
      """多个标题行但无正文的 block 应返回 False"""
      block = "# 附录 A\n## A.1 范围\n"
      assert _has_body_content(block) is False
  ```

- [ ] **Step 2：运行测试，确认失败（函数尚未存在）**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py -v 2>&1 | head -20
  ```

  预期：`ImportError: cannot import name '_has_body_content'`

---

## Task 2：实现 `_has_body_content`

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/slice_node.py`

- [ ] **Step 1：在 `_split_by_heading` 函数之后添加 `_has_body_content`**

  在 `slice_node.py` 第 40 行（`_split_by_heading` 函数结束后）插入：

  ```python
  def _has_body_content(block: str) -> bool:
      """
      判断 block 是否有标题行以外的实质内容。
      去除所有以 # 开头的行后，检查剩余内容是否非空。
      """
      lines = block.splitlines()
      body = "\n".join(line for line in lines if not line.startswith("#"))
      return bool(body.strip())
  ```

- [ ] **Step 2：运行测试，确认通过**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py::test_has_body_content_heading_only_returns_false tests/core/parser_workflow/test_slice_node.py::test_has_body_content_with_body_returns_true tests/core/parser_workflow/test_slice_node.py::test_has_body_content_multiple_headings_only_returns_false -v
  ```

  预期：3 个 PASSED

- [ ] **Step 3：提交**

  ```bash
  cd agent-server && git add app/core/parser_workflow/nodes/slice_node.py tests/core/parser_workflow/test_slice_node.py && git commit -m "feat: add _has_body_content helper for empty chunk filtering"
  ```

---

## Task 3：写 P2-01（空头 chunk 过滤）的测试

**Files:**
- Modify: `agent-server/tests/core/parser_workflow/test_slice_node.py`

- [ ] **Step 1：追加测试用例**

  在 `test_slice_node.py` 末尾追加：

  ```python
  # ── P2-01：空头 chunk 过滤 ───────────────────────────────────────────


  def test_heading_only_block_not_emitted_when_within_soft_max():
      """
      仅含标题行的 block（char_count <= soft_max）不应生成 chunk（P2-01 回归）。
      关键：相邻同级标题之间没有正文，切分后对应 block 为纯标题行。
      """
      # "# 2 技术要求\n\n" 和 "# 3 检验方法\n\n正文" 各自是独立 block
      # "2 技术要求" 的 block = "# 2 技术要求\n\n"，无正文，应被过滤
      md = "# 2 技术要求\n\n# 3 检验方法\n\n颜色应为白色或淡黄色。\n"
      errors: list = []
      chunks = recursive_slice(md, [1], [], soft_max=1500, hard_max=3000, errors=errors)
      paths = [c["section_path"] for c in chunks]
      # "2 技术要求" 节仅含标题行，不应出现在结果中
      assert ["2 技术要求"] not in paths, f"空头 chunk 不应被生成，实际 paths={paths}"
      # "3 检验方法" 有实质内容，应出现
      assert any("3 检验方法" in p for p in paths), f"实质内容 chunk 应被生成，实际 paths={paths}"
  ```

- [ ] **Step 2：运行测试，确认失败**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py::test_heading_only_block_not_emitted_when_within_soft_max -v
  ```

  预期：FAILED（当前代码会为 "2 技术要求" 生成空头 chunk，导致 `["2 技术要求"] not in paths` 断言失败）

---

## Task 4：实现 P2-01 修复（在 `<= soft_max` 分支加 `_has_body_content` 检查）

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/slice_node.py:73-81`

- [ ] **Step 1：修改 `recursive_slice` 的 `<= soft_max` 分支**

  将当前第 73-81 行：

  ```python
          if char_count <= soft_max or len(heading_levels) <= 1:
              chunk = RawChunk(
                  content=block, section_path=path, char_count=len(block)
              )
              if len(block) > hard_max:
                  errors.append(
                      f"WARN: chunk exceeds HARD_MAX ({len(block)} chars) at {path}"
                  )
              result.append(chunk)
  ```

  替换为：

  ```python
          if char_count <= soft_max or len(heading_levels) <= 1:
              if _has_body_content(block):
                  if len(block) > hard_max:
                      errors.append(
                          f"WARN: chunk exceeds HARD_MAX ({len(block)} chars) at {path}"
                      )
                  result.append(RawChunk(content=block, section_path=path, char_count=len(block)))
  ```

- [ ] **Step 2：运行 P2-01 测试，确认通过**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py -v
  ```

  预期：全部 PASSED

- [ ] **Step 3：提交**

  ```bash
  cd agent-server && git add app/core/parser_workflow/nodes/slice_node.py tests/core/parser_workflow/test_slice_node.py && git commit -m "fix(P2-01): filter heading-only chunks using _has_body_content"
  ```

---

## Task 5：写 P1-02（soft_max 粒度一致性）的测试

**Files:**
- Modify: `agent-server/tests/core/parser_workflow/test_slice_node.py`

- [ ] **Step 1：追加测试用例**

  在 `test_slice_node.py` 末尾追加：

  ```python
  # ── P1-02：soft_max 粒度一致性 ──────────────────────────────────────


  def _make_section(title: str, level: int, body_chars: int) -> str:
      """生成指定长度正文的 Markdown 节"""
      prefix = "#" * level
      body = "文" * body_chars
      return f"{prefix} {title}\n\n{body}\n"


  def test_soft_max_exceeded_but_no_sub_exceeds_hard_max_keeps_as_single_chunk():
      """
      block > soft_max，但所有直接子节均 <= hard_max 时，整体保留为 1 个 chunk（P1-02 修复）。
      模拟 A.9 场景：总长 ~2777 chars，soft_max=1500，hard_max=3000。
      """
      # 构造 6 个子节，每个约 450 chars，合计 ~2700 chars
      sub_sections = "".join(
          _make_section(f"A.9.{i}", level=3, body_chars=440)
          for i in range(1, 7)
      )
      block = _make_section("A.9 残留溶剂测定", level=2, body_chars=0).rstrip("\n") + "\n\n" + sub_sections
      # 确认总长超 soft_max
      assert len(block) > 1500
      # 确认每个子节不超 hard_max（构造时已控制）
      errors: list = []
      chunks = recursive_slice(block, [2, 3], [], soft_max=1500, hard_max=3000, errors=errors)
      assert len(chunks) == 1, f"应整体保留为 1 个 chunk，实际 {len(chunks)} 个"
      assert any("INFO: soft_max exceeded" in e for e in errors), "应有 INFO 日志"


  def test_soft_max_exceeded_and_sub_exceeds_hard_max_triggers_split():
      """
      block > soft_max，且存在直接子节 > hard_max 时，触发递归拆分（P1-02 回归）。
      """
      # 构造 1 个子节超过 hard_max=3000
      big_sub = _make_section("A.9.1 仪器", level=3, body_chars=3100)
      small_sub = _make_section("A.9.2 试剂", level=3, body_chars=100)
      block = _make_section("A.9 残留溶剂测定", level=2, body_chars=0).rstrip("\n") + "\n\n" + big_sub + small_sub
      errors: list = []
      chunks = recursive_slice(block, [2, 3], [], soft_max=1500, hard_max=3000, errors=errors)
      assert len(chunks) > 1, "存在超 hard_max 的子节时，应触发拆分"


  def test_block_within_soft_max_is_kept_unchanged():
      """block <= soft_max 时，行为与修改前完全一致（回归测试）"""
      block = _make_section("A.3 硫酸酯测定", level=2, body_chars=1300)
      errors: list = []
      chunks = recursive_slice(block, [2, 3], [], soft_max=1500, hard_max=3000, errors=errors)
      assert len(chunks) == 1
      assert not any("INFO" in e for e in errors)


  def test_single_heading_level_forces_keep():
      """heading_levels 只剩 1 级时，无论大小都强制整体保留（回归测试）"""
      block = _make_section("A.9 残留溶剂测定", level=2, body_chars=2000)
      errors: list = []
      chunks = recursive_slice(block, [2], [], soft_max=1500, hard_max=3000, errors=errors)
      assert len(chunks) == 1
  ```

- [ ] **Step 2：运行新测试，确认 P1-02 相关测试失败（当前代码会强制拆分）**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py::test_soft_max_exceeded_but_no_sub_exceeds_hard_max_keeps_as_single_chunk -v
  ```

  预期：FAILED（当前代码返回多个 chunk）

---

## Task 6：实现 P1-02 修复（修改 else 分支）

**Files:**
- Modify: `agent-server/app/core/parser_workflow/nodes/slice_node.py:82-86`

- [ ] **Step 1：修改 `recursive_slice` 的 else 分支**

  将当前 else 分支：

  ```python
          else:
              result.extend(
                  recursive_slice(block, heading_levels[1:], path, soft_max, hard_max, errors)
              )
  ```

  替换为：

  ```python
          else:
              # soft_max 超限时，检查直接子节是否真的需要拆分
              # 仅检查一层（heading_levels[1]），孙节超限由下层递归处理（有意设计）
              sub_parts = _split_by_heading(block, heading_levels[1])
              # 过滤纯标题行子节，避免影响 hard_max 判断
              any_sub_exceeds_hard = any(
                  len(p[1]) > hard_max for p in sub_parts if p[1].strip()
              )
              if not any_sub_exceeds_hard:
                  # 所有直接子节均在 hard_max 以内，整体保留
                  # 注：不需要 _has_body_content 检查——block > soft_max > 1500，不可能是纯标题行
                  errors.append(f"INFO: soft_max exceeded but kept as single chunk at {path}")
                  result.append(RawChunk(content=block, section_path=path, char_count=len(block)))
              else:
                  result.extend(
                      recursive_slice(block, heading_levels[1:], path, soft_max, hard_max, errors)
                  )
  ```

- [ ] **Step 2：运行全部测试，确认通过**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_slice_node.py -v
  ```

  预期：全部 PASSED

- [ ] **Step 3：运行整个 parser_workflow 测试套件，确认无回归**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/ -v --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py
  ```

  预期：全部 PASSED（real_llm 系列需要 API key，跳过）

- [ ] **Step 4：提交**

  ```bash
  cd agent-server && git add app/core/parser_workflow/nodes/slice_node.py tests/core/parser_workflow/test_slice_node.py && git commit -m "fix(P1-02): restore soft_max as advisory threshold, keep whole section when no sub-exceeds hard_max"
  ```
