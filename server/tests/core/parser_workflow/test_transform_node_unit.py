from unittest.mock import patch

from parser.models import (
    ClassifiedChunk, RawChunk, TypedSegment, WorkflowState,
)
from parser.nodes.output import TransformOutput
from parser.nodes.transform_node import transform_node


def _make_state(structure_type: str, semantic_type: str) -> WorkflowState:
    seg = TypedSegment(
        content="称取试样",
        structure_type=structure_type,
        semantic_type=semantic_type,
        transform_params={"strategy": "plain_embed", "prompt_template": "请转化：\n"},
        confidence=0.9,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    raw_chunk = RawChunk(content="称取试样", section_path=["A.3"], char_count=5)
    classified = ClassifiedChunk(raw_chunk=raw_chunk, segments=[seg], has_unknown=False)
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "TEST001"},
        config={},
        rules_dir="",
        raw_chunks=[raw_chunk],
        classified_chunks=[classified],
        final_chunks=[],
        errors=[],
    )


def test_transform_node_output_chunk_has_dual_type_fields():
    """transform_node 产出的 DocumentChunk 应包含 structure_type + semantic_type"""
    with patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="规范化文本",
    ):
        result = transform_node(_make_state("list", "procedure"))

    chunks = result["final_chunks"]
    assert chunks
    chunk = chunks[0]
    assert chunk["structure_type"] == "list"
    assert chunk["semantic_type"] == "procedure"
    assert "content_type" not in chunk
