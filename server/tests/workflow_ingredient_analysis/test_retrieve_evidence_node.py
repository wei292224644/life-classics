"""Tests for retrieve_evidence_node."""
import pytest
from unittest.mock import AsyncMock, patch
from workflow_ingredient_analysis.nodes.retrieve_evidence_node import retrieve_evidence_node
from workflow_ingredient_analysis.models import WorkflowState

pytestmark = pytest.mark.asyncio


async def test_retrieve_evidence_node_success():
    """有 KB 结果时返回 evidence_refs."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "焦糖色"},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=None,
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
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
                "content": "焦糖色的使用限量...",
                "raw_content": "原始文本",
                "score": 0.95,
            }
        ]
        result = await retrieve_evidence_node(state)
        assert result["evidence_refs"] is not None
        assert len(result["evidence_refs"]) == 1
        assert result["status"] == "running"


async def test_retrieve_evidence_node_no_results():
    """KB 无结果时返回空列表."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "新配料"},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=None,
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    with patch(
        "workflow_ingredient_analysis.nodes.retrieve_evidence_node.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = []
        result = await retrieve_evidence_node(state)
        assert result["evidence_refs"] == []
        assert result["status"] == "running"


async def test_retrieve_evidence_node_missing_ingredient():
    """无 ingredient 数据时返回 failed."""
    state = WorkflowState(
        ingredient={},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=None,
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    result = await retrieve_evidence_node(state)
    assert result["status"] == "failed"
    assert result["error_code"] == "ingredient_not_found"


async def test_retrieve_evidence_node_kb_error():
    """KB 查询异常时返回 failed."""
    state = WorkflowState(
        ingredient={"ingredient_id": 1, "name": "焦糖色"},
        task_id="test-task",
        run_id="test-run",
        ai_model="claude-opus-4-6",
        evidence_refs=None,
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    with patch(
        "workflow_ingredient_analysis.nodes.retrieve_evidence_node.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.side_effect = Exception("KB unavailable")
        result = await retrieve_evidence_node(state)
        assert result["status"] == "failed"
        assert result["error_code"] == "knowledge_base_unavailable"
