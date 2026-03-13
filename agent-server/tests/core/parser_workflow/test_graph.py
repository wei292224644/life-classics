from app.core.parser_workflow.models import ClassifiedChunk, RawChunk, TypedSegment, WorkflowState


def _make_state(classified: list) -> WorkflowState:
    return WorkflowState(
        md_content="",
        doc_metadata={},
        config={},
        rules_dir="/tmp",
        raw_chunks=[],
        classified_chunks=classified,
        final_chunks=[],
        errors=[],
    )


def _cc(has_unknown: bool) -> ClassifiedChunk:
    seg = TypedSegment(
        content="x",
        content_type="unknown" if has_unknown else "plain_text",
        transform_params={},
        confidence=0.5 if has_unknown else 0.9,
        escalated=False,
    )
    return ClassifiedChunk(
        raw_chunk=RawChunk(content="x", section_path=["3"], char_count=1),
        segments=[seg],
        has_unknown=has_unknown,
    )


def test_should_escalate_routes_to_escalate_when_any_unknown():
    from app.core.parser_workflow.graph import _should_escalate

    state = _make_state([_cc(False), _cc(True)])
    assert _should_escalate(state) == "escalate_node"


def test_should_escalate_routes_to_transform_when_all_known():
    from app.core.parser_workflow.graph import _should_escalate

    state = _make_state([_cc(False), _cc(False)])
    assert _should_escalate(state) == "transform_node"


def test_should_escalate_routes_to_transform_when_no_chunks():
    from app.core.parser_workflow.graph import _should_escalate

    state = _make_state([])
    assert _should_escalate(state) == "transform_node"

