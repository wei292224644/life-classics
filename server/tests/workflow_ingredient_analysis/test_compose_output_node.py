"""Tests for compose_output_node."""
import pytest
from unittest.mock import MagicMock, patch
from workflow_ingredient_analysis.nodes.compose_output_node import compose_output_node
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import ComposeOutput, AlternativeItem

pytestmark = pytest.mark.asyncio


async def test_compose_output_node_success():
    """正常生成 safety_info 和 alternatives."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "焦糖色", "function_type": ["着色剂"]},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=[],
        analysis_output={
            "level": "t2",
            "confidence_score": 0.75,
            "decision_trace": {
                "steps": [
                    {
                        "step": "review",
                        "findings": [],
                        "reasoning": "",
                        "conclusion": "中等风险",
                    }
                ],
                "final_conclusion": "中等风险",
            },
        },
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    mock_output = ComposeOutput(
        safety_info="适量食用安全，过量可能不利",
        alternatives=[
            AlternativeItem(
                ingredient_id=0,
                name="天然色素",
                reason="更安全的替代选择",
            )
        ],
    )
    with patch(
        "workflow_ingredient_analysis.nodes.compose_output_node.invoke_structured",
        new_callable=MagicMock,
    ) as mock_invoke:
        mock_invoke.return_value = mock_output
        result = await compose_output_node(state)
        assert result["composed_output"] is not None
        assert "safety_info" in result["composed_output"]
        assert result["status"] == "succeeded"


async def test_compose_output_node_llm_error():
    """LLM 调用失败时返回 failed."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "焦糖色", "function_type": ["着色剂"]},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=[],
        analysis_output={
            "level": "t2",
            "confidence_score": 0.75,
            "decision_trace": {
                "steps": [],
                "final_conclusion": "中等风险",
            },
        },
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    with patch(
        "workflow_ingredient_analysis.nodes.compose_output_node.invoke_structured",
        new_callable=MagicMock,
    ) as mock_invoke:
        mock_invoke.side_effect = Exception("LLM unavailable")
        result = await compose_output_node(state)
        assert result["status"] == "failed"
        assert result["error_code"] == "schema_invalid"
