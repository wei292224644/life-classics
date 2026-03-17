import os

import pytest

from app.core.parser_workflow import parser_graph
from app.core.parser_workflow.models import WorkflowState
from tests.core.parser_workflow.test_utils import (
    get_logger,
    get_rules_dir,
    load_env_if_exists,
    load_sample_markdown,
)

logger = get_logger("workflow")
pytestmark = pytest.mark.real_llm


@pytest.mark.asyncio
async def test_full_parser_workflow_with_real_llm_logs_all_steps():
    """使用真实 LLM + 实际规则目录，通过 LangGraph 跑完整个 parser_workflow，并将每个阶段的结果打日志。"""
    load_env_if_exists()
    if not os.environ.get("LLM_API_KEY"):
        pytest.skip("环境变量 LLM_API_KEY 未设置，跳过真实 LLM 端到端测试")

    md_content, _ = load_sample_markdown()
    rules_dir = get_rules_dir()

    initial_state = WorkflowState(
        md_content=md_content,
        doc_metadata={
            "standard_no": "GB1886.169-2016",
            "title": "《食品安全国家标准 食品添加剂 卡拉胶》（GB 1886.169-2016）第1号修改单",
        },
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )

    # 通过 LangGraph streaming 逐节点记录日志，同时积累最终状态
    result_state = dict(initial_state)
    async for chunk in parser_graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            result_state.update(node_output)
            if node_name == "parse_node":
                logger.info("parse_node result: %s", node_output)
            elif node_name == "structure_node":
                logger.info("structure_node result: %s", node_output)
            elif node_name == "slice_node":
                logger.info(
                    "slice_node result: raw_chunks=%d, errors=%s",
                    len(node_output.get("raw_chunks", [])),
                    node_output.get("errors", []),
                )
            elif node_name == "classify_node":
                logger.info(
                    "classify_node result: classified_chunks=%d",
                    len(node_output.get("classified_chunks", [])),
                )
            elif node_name == "escalate_node":
                logger.info("escalate_node applied: reclassified all unknown segments")
            elif node_name == "transform_node":
                logger.info(
                    "transform_node result: final_chunks=%d",
                    len(node_output.get("final_chunks", [])),
                )

    escalate_count = sum(
        1
        for c in result_state["classified_chunks"]
        if any(s.get("escalated") for s in c["segments"])
    )
    stats = {
        "chunk_count": len(result_state["final_chunks"]),
        "escalate_count": escalate_count,
    }
    logger.info("final doc_metadata: %s", result_state["doc_metadata"])
    logger.info("final stats: %s", stats)
    logger.info("first 3 chunks: %s", result_state["final_chunks"][:3])

    assert len(result_state["final_chunks"]) > 0
    assert not result_state["errors"]
