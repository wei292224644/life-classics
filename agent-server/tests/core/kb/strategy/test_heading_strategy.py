"""按标题切分 Markdown 的测试"""

from app.core.kb.strategy.heading_strategy import split_heading_from_markdown


def test_heading_split_single_section():
    md = "## 适用范围\n\n本标准适用于食品添加剂。"
    chunks = split_heading_from_markdown(md, doc_id="d1", doc_title="test", source="test.md")
    assert len(chunks) >= 1
    assert chunks[0].section_path
    assert "适用范围" in (chunks[0].section_path or []) or "适用范围" in str(chunks[0].content)


def test_heading_split_multiple_sections():
    md = """## 范围
本标准规定食品添加剂。

## 规范性引用文件
GB 2760 食品添加剂使用标准。
"""
    chunks = split_heading_from_markdown(md, doc_id="d2", doc_title="doc", source="x.md")
    assert len(chunks) >= 2
    titles = [c.section_path[0] if c.section_path else "" for c in chunks]
    assert "范围" in titles
    assert "规范性引用文件" in titles
