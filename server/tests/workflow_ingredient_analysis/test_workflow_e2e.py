"""End-to-end integration test for ingredient_analysis workflow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workflow_ingredient_analysis.entry import run_ingredient_analysis
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import AnalyzeOutput, AnalysisDecisionTrace, AnalysisDecisionStep, ComposeOutput, AlternativeItem

pytestmark = pytest.mark.asyncio


async def test_e2e_happy_path():
    """完整流程：有证据 → 全部节点正常执行 → succeeded."""
    ingredient = {
        "ingredient_id": 1,
        "name": "焦糖色",
        "function_type": ["着色剂"],
        "origin_type": "合成",
        "limit_usage": "按需添加",
        "safety_info": "",
        "cas": "8028-89-5",
    }

    with patch(
        "workflow_ingredient_analysis.nodes.retrieve_evidence_node.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = [
            {
                "chunk_id": "chunk_1",
                "standard_no": "GB 2762-2022",
                "semantic_type": "limit",
                "section_path": "第二章",
                "content": "焦糖色限量规定...",
                "raw_content": "原始",
                "score": 0.9,
            }
        ]

        with patch(
            "workflow_ingredient_analysis.nodes.analyze_node.invoke_structured",
            new_callable=AsyncMock,
        ) as mock_analyze:
            mock_analyze.return_value = AnalyzeOutput(
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
                "workflow_ingredient_analysis.nodes.compose_output_node.invoke_structured",
                new_callable=AsyncMock,
            ) as mock_compose:
                mock_compose.return_value = ComposeOutput(
                    safety_info="适量食用安全",
                    alternatives=[],
                )

                result = await run_ingredient_analysis(
                    ingredient=ingredient,
                    task_id="test-task",
                    ai_model="claude-opus-4-6",
                )

    assert result["status"] == "succeeded"
    assert result["ingredient_id"] == 1
    assert result["analysis_output"]["level"] == "t2"
    assert result["composed_output"]["safety_info"] == "适量食用安全"


async def test_e2e_no_evidence_skips_analyze():
    """无证据时 analyze_node 被跳过，流程继续."""
    ingredient = {
        "ingredient_id": 1,
        "name": "新配料",
        "function_type": [],
        "origin_type": "",
        "limit_usage": "",
        "safety_info": "",
        "cas": "",
    }

    with patch(
        "workflow_ingredient_analysis.nodes.retrieve_evidence_node.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = []  # 无证据

        with patch(
            "workflow_ingredient_analysis.nodes.compose_output_node.invoke_structured",
            new_callable=AsyncMock,
        ) as mock_compose:
            mock_compose.return_value = ComposeOutput(
                safety_info="无相关证据，请咨询专业人士",
                alternatives=[],
            )

            result = await run_ingredient_analysis(
                ingredient=ingredient,
                task_id="test-task",
            )

    assert result["status"] == "succeeded"
    assert result["evidence_refs"] == []
    assert result["analysis_output"] is None
    assert result["composed_output"]["safety_info"] == "无相关证据，请咨询专业人士"
