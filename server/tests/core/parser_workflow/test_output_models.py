# tests/core/parser_workflow/test_output_models.py
from parser.nodes.output import SegmentItem, ClassifyOutput


def test_segment_item_has_structure_and_semantic_type():
    item = SegmentItem(
        content="试样处理：称取约2g试样",
        structure_type="list",
        semantic_type="procedure",
        confidence=0.9,
    )
    assert item.structure_type == "list"
    assert item.semantic_type == "procedure"


def test_segment_item_rejects_content_type():
    """SegmentItem 不再有 content_type 字段"""
    import pytest
    from pydantic import ValidationError
    with pytest.raises((ValidationError, TypeError)):
        SegmentItem(content="x", content_type="table", confidence=0.8)


def test_classify_output_segments_use_dual_type():
    output = ClassifyOutput(segments=[
        SegmentItem(content="a", structure_type="paragraph", semantic_type="scope", confidence=0.85),
        SegmentItem(content="b", structure_type="table", semantic_type="limit", confidence=0.92),
    ])
    assert output.segments[0].structure_type == "paragraph"
    assert output.segments[1].semantic_type == "limit"
