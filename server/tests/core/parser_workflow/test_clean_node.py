# tests/core/parser_workflow/test_clean_node.py
"""验证 clean_node._clean_md_content 的清洗规则。"""
from worflow_parser_kb.nodes.clean_node import _clean_md_content


def test_removes_electronic_version_disclaimer():
    md = "# 标题\n\n(电子版本仅供参考，以标准正式出版物为准)\n\n正文"
    result = _clean_md_content(md)
    assert "电子版本" not in result
    assert "正文" in result


def test_removes_preface_section():
    md = "# 标题\n\n# 前言\n\n附录A为资料性附录。\n首次发布。\n\n# 1 范围\n\n适用范围。"
    result = _clean_md_content(md)
    assert "前言" not in result
    assert "附录A为资料性附录" not in result
    assert "1 范围" in result
    assert "适用范围" in result


def test_preserves_content_without_preface():
    md = "# 1 范围\n\n本标准适用于..."
    assert _clean_md_content(md) == md


def test_existing_image_rule_still_works():
    md = "内容 ![图](url.png) 继续"
    assert "![图]" not in _clean_md_content(md)
