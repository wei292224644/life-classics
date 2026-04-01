"""Tests for analyze_node."""
import pytest
from unittest.mock import MagicMock, patch
from workflow_ingredient_analysis.nodes.analyze_node import analyze_node
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import AnalyzeOutput, AnalysisDecisionTrace, AnalysisDecisionStep

pytestmark = pytest.mark.asyncio


async def test_analyze_node_success():
    """有 evidence_refs 时正常分析."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "焦糖色", "function_type": ["着色剂"]},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=[
            {
                "source_id": "chunk_1",
                "source_type": "gb_standard_chunk",
                "standard_no": "GB 2762-2022",
                "semantic_type": "limit",
                "section_path": "第二章",
                "content": "焦糖色在碳酸饮料中的使用限量...",
                "raw_content": "原始",
                "score": 0.9,
            }
        ],
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    mock_output = AnalyzeOutput(
        level="t2",
        confidence_score=0.8,
        decision_trace=AnalysisDecisionTrace(
            steps=[
                AnalysisDecisionStep(
                    step="evidence_review",
                    findings=["发现限量规定"],
                    reasoning="根据GB 2762-2022",
                    conclusion="中等风险",
                )
            ],
            final_conclusion="中等风险",
        ),
    )
    with patch(
        "workflow_ingredient_analysis.nodes.analyze_node.invoke_structured",
        new_callable=MagicMock,
    ) as mock_invoke:
        mock_invoke.return_value = mock_output
        result = await analyze_node(state)
        assert result["analysis_output"] is not None
        assert result["analysis_output"]["level"] == "t2"
        assert 0 <= result["analysis_output"]["confidence_score"] <= 1
        assert result["status"] == "running"


async def test_analyze_node_empty_evidence():
    """空 evidence_refs 时也正常执行（降级为 unknown 由 workflow 条件边处理）."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "新配料", "function_type": []},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=[],
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    mock_output = AnalyzeOutput(
        level="unknown",
        confidence_score=0.1,
        decision_trace=AnalysisDecisionTrace(
            steps=[],
            final_conclusion="证据不足",
        ),
    )
    with patch(
        "workflow_ingredient_analysis.nodes.analyze_node.invoke_structured",
        new_callable=MagicMock,
    ) as mock_invoke:
        mock_invoke.return_value = mock_output
        result = await analyze_node(state)
        assert result["analysis_output"] is not None
        assert result["status"] == "running"


async def test_analyze_node_llm_error():
    """LLM 调用失败时返回 failed."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "焦糖色", "function_type": ["着色剂"]},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=[
            {
                "source_id": "chunk_1",
                "source_type": "gb_standard_chunk",
                "standard_no": "GB 2762-2022",
                "semantic_type": "limit",
                "section_path": "第二章",
                "content": "焦糖色...",
                "raw_content": "原始",
                "score": 0.9,
            }
        ],
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    with patch(
        "workflow_ingredient_analysis.nodes.analyze_node.invoke_structured",
        new_callable=MagicMock,
    ) as mock_invoke:
        mock_invoke.side_effect = Exception("LLM unavailable")
        result = await analyze_node(state)
        assert result["status"] == "failed"
        assert result["error_code"] == "schema_invalid"
