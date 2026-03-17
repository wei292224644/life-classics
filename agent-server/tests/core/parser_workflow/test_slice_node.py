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
