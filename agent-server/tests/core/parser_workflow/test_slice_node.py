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


# ── 整体超 hard_max 时必须拆分 ──────────────────────────────────────


def test_block_exceeding_hard_max_is_split_even_if_no_single_sub_exceeds():
    """
    block > hard_max，即使所有直接子节均 <= hard_max，也必须递归拆分。
    模拟附录 A 场景：多个 ## 节各自在 hard_max 以内，但合计远超 hard_max。
    """
    # 构造 8 个子节，每个约 600 chars，合计 ~4800 chars > hard_max=3000
    sub_sections = "".join(
        _make_section(f"A.{i}", level=2, body_chars=580)
        for i in range(1, 9)
    )
    block = "# 附录 A 检验方法\n\n" + sub_sections
    # 确认整体超 hard_max
    assert len(block) > 3000
    # 确认每个子节单独不超 hard_max
    for i in range(1, 9):
        sub = _make_section(f"A.{i}", level=2, body_chars=580)
        assert len(sub) <= 3000
    errors: list = []
    chunks = recursive_slice(block, [1, 2], [], soft_max=1500, hard_max=3000, errors=errors)
    assert len(chunks) > 1, (
        f"整体超 hard_max 时应被拆分，实际生成 {len(chunks)} 个 chunk"
    )


def test_section_path_latex_is_normalized():
    """heading 中的 LaTeX 符号在 section_path 中应被渲染为 Unicode"""
    md = "## A.3 硫酸酯（以 $\\mathrm{SO}_4$ 计）的测定\n\n正文内容。"
    result = recursive_slice(md, [2], [], soft_max=5000, hard_max=10000, errors=[])
    assert len(result) == 1
    path = result[0]["section_path"]
    assert "$" not in path[0], f"section_path 中不应含 LaTeX: {path}"
    assert "SO₄" in path[0] or "SO4" in path[0], f"应含渲染后的化学式: {path}"


def test_section_path_mathbf_ph_normalized():
    """$\\mathbf{pH}$ 应在 section_path 中渲染为 pH"""
    md = "## A.8 $\\mathbf{pH}$ 的测定\n\n正文内容。"
    result = recursive_slice(md, [2], [], soft_max=5000, hard_max=10000, errors=[])
    path = result[0]["section_path"]
    assert "$" not in path[0]
    assert "pH" in path[0]
