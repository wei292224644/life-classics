import pytest

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.nodes.transform_node import (
    apply_strategy,
    dominant_content_type,
    transform_node,
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


def test_dominant_type_single_segment():
    segs = [_seg("短文本", "plain_text")]
    assert dominant_content_type(segs) == "plain_text"


def test_dominant_type_picks_largest_by_char_count():
    segs = [
        _seg("x" * 100, "plain_text"),
        _seg("y" * 20, "table"),
    ]
    assert dominant_content_type(segs) == "plain_text"


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
    assert len(chunks) == 2
    assert all(c["content_type"] == "table" for c in chunks)
    assert all(c["meta"].get("table_row_index") is not None for c in chunks)
    assert all("项目" in c["content"] for c in chunks)


def test_split_rows_preserves_raw_content():
    table_md = "| A | B |\n|---|---|\n| 1 | 2 |"
    seg = _seg(table_md, "table", "split_rows")
    seg["transform_params"]["preserve_header"] = True
    raw = _raw(table_md)
    chunks = apply_strategy([seg], raw, {"standard_no": "GB_TEST", "title": "t"})
    assert all(c["raw_content"] == table_md for c in chunks)


def test_split_rows_header_only_table_falls_back_to_preserve():
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

