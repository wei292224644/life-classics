from parser.models import TypedSegment, DocumentChunk


def test_typed_segment_has_dual_type_fields():
    seg = TypedSegment(
        content="试剂：异丙醇溶液 60%",
        structure_type="list",
        semantic_type="material",
        transform_params={"strategy": "plain_embed", "prompt_template": "..."},
        confidence=0.88,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    assert seg["structure_type"] == "list"
    assert seg["semantic_type"] == "material"
    assert "content_type" not in seg


def test_document_chunk_has_dual_type_fields():
    chunk = DocumentChunk(
        chunk_id="abc123",
        doc_metadata={"standard_no": "GB1886.47"},
        section_path=["A.3", "A.3.1"],
        structure_type="list",
        semantic_type="procedure",
        content="转化后文本",
        raw_content="原始文本",
        meta={},
    )
    assert chunk["structure_type"] == "list"
    assert chunk["semantic_type"] == "procedure"
    assert "content_type" not in chunk
