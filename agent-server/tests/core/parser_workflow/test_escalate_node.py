import pytest
from unittest.mock import patch

from app.core.parser_workflow.models import ClassifiedChunk, RawChunk, TypedSegment, WorkflowState
from app.core.parser_workflow.nodes.escalate_node import escalate_node


def _seg(content: str, ct: str, confidence: float = 0.9) -> TypedSegment:
    return TypedSegment(
        content=content,
        content_type=ct,
        transform_params={"strategy": "plain_embed"},
        confidence=confidence,
        escalated=False,
    )


def _raw(content: str) -> RawChunk:
    return RawChunk(content=content, section_path=["3"], char_count=len(content))


def _make_state(classified: list, rules_dir: str) -> WorkflowState:
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "GB_TEST", "title": "t"},
        config={"escalate_model": "gpt-mock", "llm_api_key": "test"},
        rules_dir=rules_dir,
        raw_chunks=[],
        classified_chunks=classified,
        final_chunks=[],
        errors=[],
    )


MOCK_ESCALATE_CREATE = {
    "action": "create_new",
    "content_type": "flowchart",
    "description": "流程图描述文字",
    "transform": {
        "strategy": "llm_transform",
        "prompt_template": "请将以下GB标准流程图文字描述转化为规范化文本：\n{content}",
    },
}

MOCK_ESCALATE_USE_EXISTING = {
    "action": "use_existing",
    "content_type": "plain_text",
}


def test_escalate_resolves_unknown_segment_by_creating_new_type(tmp_path):
    classified = [
        ClassifiedChunk(
            raw_chunk=_raw("流程图内容"),
            segments=[_seg("流程图内容", "unknown", 0.3)],
            has_unknown=True,
        )
    ]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=MOCK_ESCALATE_CREATE,
    ):
        result = escalate_node(_make_state(classified, str(tmp_path)))
    cc = result["classified_chunks"][0]
    assert cc["has_unknown"] is False
    assert cc["segments"][0]["content_type"] == "flowchart"
    assert cc["segments"][0]["escalated"] is True
    assert cc["segments"][0]["confidence"] == 1.0
    assert cc["segments"][0]["transform_params"]["strategy"] == "llm_transform"


def test_escalate_uses_existing_type_without_creating_rule(tmp_path):
    """LLM 判断匹配已有类型时，不写文件，直接回写 content_type。"""
    classified = [
        ClassifiedChunk(
            raw_chunk=_raw("普通说明文字"),
            segments=[_seg("普通说明文字", "unknown", 0.3)],
            has_unknown=True,
        )
    ]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=MOCK_ESCALATE_USE_EXISTING,
    ):
        result = escalate_node(_make_state(classified, str(tmp_path)))
    cc = result["classified_chunks"][0]
    assert cc["has_unknown"] is False
    assert cc["segments"][0]["content_type"] == "plain_text"
    assert cc["segments"][0]["escalated"] is True

    from app.core.parser_workflow.rules import RulesStore

    store = RulesStore(str(tmp_path))
    ids = [ct["id"] for ct in store.get_content_type_rules()["content_types"]]
    assert "plain_text" in ids


def test_escalate_appends_new_rule_to_file(tmp_path):
    classified = [
        ClassifiedChunk(
            raw_chunk=_raw("流程图内容"),
            segments=[_seg("流程图内容", "unknown", 0.3)],
            has_unknown=True,
        )
    ]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=MOCK_ESCALATE_CREATE,
    ):
        escalate_node(_make_state(classified, str(tmp_path)))

    from app.core.parser_workflow.rules import RulesStore

    store = RulesStore(str(tmp_path))
    ct_rules = store.get_content_type_rules()["content_types"]
    ids = [ct["id"] for ct in ct_rules]
    assert "flowchart" in ids
    flowchart_rule = next(ct for ct in ct_rules if ct["id"] == "flowchart")
    assert "prompt_template" in flowchart_rule["transform"]


def test_escalate_skips_chunks_without_unknown(tmp_path):
    classified = [
        ClassifiedChunk(
            raw_chunk=_raw("普通内容"),
            segments=[_seg("普通内容", "plain_text", 0.95)],
            has_unknown=False,
        )
    ]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm"
    ) as mock_llm:
        escalate_node(_make_state(classified, str(tmp_path)))
    mock_llm.assert_not_called()


def test_escalate_only_resolves_unknown_segments_not_known_ones(tmp_path):
    classified = [
        ClassifiedChunk(
            raw_chunk=_raw("内容A\n内容B"),
            segments=[
                _seg("内容A", "plain_text", 0.95),
                _seg("内容B", "unknown", 0.2),
            ],
            has_unknown=True,
        )
    ]
    with patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=MOCK_ESCALATE_CREATE,
    ):
        result = escalate_node(_make_state(classified, str(tmp_path)))
    segs = result["classified_chunks"][0]["segments"]
    assert segs[0]["content_type"] == "plain_text"
    assert segs[0]["escalated"] is False
    assert segs[1]["content_type"] == "flowchart"
    assert segs[1]["escalated"] is True

