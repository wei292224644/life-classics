import os
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.core.parser_workflow import parser_graph
from app.core.parser_workflow.models import WorkflowState
from pydantic import BaseModel
from tests.core.parser_workflow.test_utils import (
    get_logger,
    get_rules_dir,
    load_env_if_exists,
    load_sample_markdown,
)

logger = get_logger("workflow")
pytestmark = pytest.mark.real_llm


def _to_jsonable(value):
    """尽量把各种对象转成可 JSON 序列化结构（用于测试调试缓存）。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        # 不缓存 transform_params（内容较长且噪声大，改动频繁），以便专注对比核心产出。
        return {
            str(k): _to_jsonable(v)
            for k, v in value.items()
            if str(k) != "transform_params"
        }
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, set):
        return sorted([_to_jsonable(v) for v in value], key=lambda x: str(x))
    # 兜底：转字符串，避免因不可序列化导致测试中断
    return str(value)


def _summarize_node_output(node_name: str, node_output: dict) -> dict:
    """给每个节点输出附加轻量摘要，便于快速定位变化。"""
    summary: dict = {"node_name": node_name, "keys": sorted(list(node_output.keys()))}
    if node_name == "slice_node":
        summary.update(
            {
                "raw_chunks_count": len(node_output.get("raw_chunks", []) or []),
                "errors_count": len(node_output.get("errors", []) or []),
            }
        )
    elif node_name == "classify_node":
        summary.update(
            {
                "classified_chunks_count": len(
                    node_output.get("classified_chunks", []) or []
                )
            }
        )
    elif node_name == "transform_node":
        summary.update(
            {"final_chunks_count": len(node_output.get("final_chunks", []) or [])}
        )
    return summary


@pytest.mark.asyncio
async def test_full_parser_workflow_with_real_llm_logs_all_steps():
    """使用真实 LLM 跑到 transform_node 前，缓存结构化中间结果。"""
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

    # 将每个流程节点输出缓存为独立 JSON 文件，文件名包含流程名，便于离线分析。
    default_cache_dir = Path(__file__).resolve().parents[2] / "artifacts"
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_run_dir = Path(
        os.environ.get(
            "WORKFLOW_CACHE_DIR",
            str(default_cache_dir / f"parser_workflow_nodes_{run_id}"),
        )
    )
    cache_run_dir.mkdir(parents=True, exist_ok=True)
    structure_cache_path = Path(
        os.environ.get(
            "WORKFLOW_STRUCTURE_CACHE_PATH",
            str(
                default_cache_dir
                / f"parser_workflow_structure_before_transform_{run_id}.json"
            ),
        )
    )
    structure_cache_path.parent.mkdir(parents=True, exist_ok=True)

    index_path = cache_run_dir / "index.json"
    index_data = {
        "type": "meta",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "test": "test_full_parser_workflow_with_real_llm_logs_all_steps",
        "rules_dir": str(rules_dir),
        "doc_metadata": _to_jsonable(initial_state["doc_metadata"]),
        "md_content_len": len(md_content),
        "md_content_preview": md_content[:200],
        "node_files": [],
    }
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    def _write_node_file(step_no: int, node_name: str, node_output: dict) -> None:
        node_file = cache_run_dir / f"{step_no:02d}_{node_name}.json"
        payload = {
            "type": "update",
            "at": datetime.now().isoformat(timespec="seconds"),
            "summary": _summarize_node_output(node_name, node_output),
            "node_output": _to_jsonable(node_output),
        }
        with node_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        index_data["node_files"].append(node_file.name)
        with index_path.open("w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    # 通过 LangGraph streaming 逐节点记录日志，同时积累 transform 前的状态
    result_state = dict(initial_state)
    step_no = 0
    async for chunk in parser_graph.astream(
        initial_state,
        stream_mode="updates",
        interrupt_before=["transform_node"],
    ):
        for node_name, node_output in chunk.items():
            step_no += 1
            result_state.update(node_output)
            _write_node_file(step_no, node_name, node_output)
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

    with structure_cache_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "type": "structure_snapshot_before_transform",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "test": "test_full_parser_workflow_with_real_llm_logs_all_steps",
                "rules_dir": str(rules_dir),
                "doc_metadata": _to_jsonable(result_state.get("doc_metadata", {})),
                "raw_chunks": _to_jsonable(result_state.get("raw_chunks", [])),
                "classified_chunks": _to_jsonable(
                    result_state.get("classified_chunks", [])
                ),
                "errors": _to_jsonable(result_state.get("errors", [])),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    escalate_count = sum(
        1
        for c in result_state["classified_chunks"]
        if any(s.get("escalated") for s in c["segments"])
    )
    stats = {
        "chunk_count": len(result_state.get("final_chunks", [])),
        "classified_chunks_count": len(result_state.get("classified_chunks", [])),
        "escalate_count": escalate_count,
    }
    logger.info("final doc_metadata: %s", result_state["doc_metadata"])
    logger.info("final stats: %s", stats)
    logger.info("workflow node files cached to: %s", cache_run_dir)
    logger.info("workflow structure cached to: %s", structure_cache_path)

    assert len(result_state["classified_chunks"]) > 0
    assert len(result_state.get("final_chunks", [])) == 0
    assert not result_state["errors"]
