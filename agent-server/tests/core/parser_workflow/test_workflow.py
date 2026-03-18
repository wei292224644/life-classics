# import os
# import json
# from datetime import datetime
# from pathlib import Path

# import pytest

# from app.core.parser_workflow import parser_graph
# from app.core.parser_workflow.nodes.classify_node import classify_node
# from app.core.parser_workflow.nodes.enrich_node import enrich_node
# from app.core.parser_workflow.nodes.escalate_node import escalate_node
# from app.core.parser_workflow.nodes.parse_node import parse_node
# from app.core.parser_workflow.nodes.slice_node import slice_node
# from app.core.parser_workflow.nodes.structure_node import structure_node
# from app.core.parser_workflow.nodes.transform_node import transform_node
# from app.core.parser_workflow.models import WorkflowState
# from app.core.parser_workflow.rules import RulesStore
# from pydantic import BaseModel
# from tests.core.parser_workflow.test_utils import (
#     get_logger,
#     get_rules_dir,
#     load_env_if_exists,
#     load_sample_markdown,
# )

# logger = get_logger("workflow")
# pytestmark = pytest.mark.real_llm

# _CACHE_NODE_ORDER = [
#     "parse_node",
#     "structure_node",
#     "slice_node",
#     "classify_node",
#     "enrich_node",
# ]


# def _get_artifact_dir() -> Path:
#     default_dir = (
#         Path(__file__).resolve().parents[2]
#         / "artifacts"
#         / "parser_workflow_nodes_20260317_215214"
#     )
#     return Path(os.environ.get("WORKFLOW_RESUME_ARTIFACT_DIR", str(default_dir)))


# def _load_artifact_node_output(artifact_dir: Path, node_name: str) -> dict:
#     matches = sorted(artifact_dir.glob(f"*_{node_name}.json"))
#     if not matches:
#         raise FileNotFoundError(
#             f"未找到节点缓存文件: {artifact_dir}/*_{node_name}.json"
#         )
#     payload = json.loads(matches[-1].read_text(encoding="utf-8"))
#     output = payload.get("node_output")
#     if not isinstance(output, dict):
#         raise ValueError(f"{matches[-1].name} 的 node_output 不是 dict")
#     return output


# def _fallback_transform_params() -> dict:
#     return {
#         "strategy": "plain_embed",
#         "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
#     }


# def _rehydrate_transform_params(classified_chunks: list, rules_dir: str) -> list:
#     store = RulesStore(rules_dir)
#     for cc in classified_chunks:
#         for seg in cc.get("segments", []):
#             if seg.get("transform_params"):
#                 continue
#             semantic_type = seg.get("semantic_type") or seg.get("content_type")
#             if semantic_type:
#                 seg["transform_params"] = store.get_transform_params(semantic_type)
#             else:
#                 seg["transform_params"] = _fallback_transform_params()
#     return classified_chunks


# def _build_resume_initial_state(artifact_dir: Path) -> WorkflowState:
#     index_data = json.loads((artifact_dir / "index.json").read_text(encoding="utf-8"))
#     parse_output = _load_artifact_node_output(artifact_dir, "parse_node")
#     md_content = parse_output.get("md_content")
#     if not isinstance(md_content, str):
#         md_content, _ = load_sample_markdown()
#     return WorkflowState(
#         md_content=md_content,
#         doc_metadata=index_data.get("doc_metadata", {}),
#         config={},
#         rules_dir=index_data.get("rules_dir", str(get_rules_dir())),
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )


# def _load_cached_state_before_node(
#     state: WorkflowState,
#     artifact_dir: Path,
#     resume_from: str,
# ) -> WorkflowState:
#     if resume_from not in _CACHE_NODE_ORDER and resume_from != "transform_node":
#         raise ValueError(
#             "WORKFLOW_RESUME_FROM 仅支持: "
#             "parse_node/structure_node/slice_node/classify_node/enrich_node/transform_node"
#         )

#     print(f"resume_from: {resume_from}")
#     for node in _CACHE_NODE_ORDER:
#         if node == resume_from:
#             break
#         cached_output = _load_artifact_node_output(artifact_dir, node)
#         state.update(cached_output)

#     if state.get("classified_chunks"):
#         state["classified_chunks"] = _rehydrate_transform_params(
#             state["classified_chunks"], state["rules_dir"]
#         )
#     return state


# def _run_from_resume_node(state: WorkflowState, resume_from: str) -> WorkflowState:
#     node_map = {
#         "parse_node": parse_node,
#         "structure_node": structure_node,
#         "slice_node": slice_node,
#         "classify_node": classify_node,
#         "enrich_node": enrich_node,
#         "transform_node": transform_node,
#     }
#     if resume_from not in node_map:
#         raise ValueError(f"不支持的 resume 节点: {resume_from}")

#     print(f"resume_from: {resume_from}")
#     update = node_map[resume_from](state)
#     if isinstance(update, dict):
#         state.update(update)

#     if resume_from in {"parse_node", "structure_node", "slice_node", "classify_node"}:
#         if resume_from != "classify_node":
#             update = classify_node(state)
#             state.update(update)
#         has_unknown = any(
#             c.get("has_unknown") for c in state.get("classified_chunks", [])
#         )
#         if has_unknown:
#             update = escalate_node(state)
#             state.update(update)
#             state["classified_chunks"] = _rehydrate_transform_params(
#                 state["classified_chunks"], state["rules_dir"]
#             )
#         update = enrich_node(state)
#         state.update(update)
#         state["classified_chunks"] = _rehydrate_transform_params(
#             state["classified_chunks"], state["rules_dir"]
#         )
#         update = transform_node(state)
#         state.update(update)
#     elif resume_from == "enrich_node":
#         state["classified_chunks"] = _rehydrate_transform_params(
#             state["classified_chunks"], state["rules_dir"]
#         )
#         update = transform_node(state)
#         state.update(update)
#     return state


# def _dump_resume_run_artifacts(
#     source_artifact_dir: Path,
#     resume_from: str,
#     input_state: dict,
#     output_state: WorkflowState,
# ) -> Path:
#     default_artifacts_dir = Path(__file__).resolve().parents[2] / "artifacts"
#     run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
#     default_run_dir = default_artifacts_dir / f"parser_workflow_resume_{run_id}"
#     run_dir = Path(os.environ.get("WORKFLOW_RESUME_CACHE_DIR", str(default_run_dir)))
#     run_dir.mkdir(parents=True, exist_ok=True)

#     index_data = {
#         "type": "resume_meta",
#         "created_at": datetime.now().isoformat(timespec="seconds"),
#         "test": "test_resume_workflow_from_cached_artifacts",
#         "resume_from": resume_from,
#         "source_artifact_dir": str(source_artifact_dir),
#         "rules_dir": input_state.get("rules_dir", ""),
#         "files": [
#             "00_resume_input_state.json",
#             "01_resume_output_state.json",
#             "index.json",
#         ],
#     }
#     with (run_dir / "index.json").open("w", encoding="utf-8") as f:
#         json.dump(index_data, f, ensure_ascii=False, indent=2)

#     with (run_dir / "00_resume_input_state.json").open("w", encoding="utf-8") as f:
#         json.dump(_to_jsonable(input_state), f, ensure_ascii=False, indent=2)

#     summary = {
#         "raw_chunks_count": len(output_state.get("raw_chunks", []) or []),
#         "classified_chunks_count": len(output_state.get("classified_chunks", []) or []),
#         "final_chunks_count": len(output_state.get("final_chunks", []) or []),
#         "errors_count": len(output_state.get("errors", []) or []),
#     }
#     with (run_dir / "01_resume_output_state.json").open("w", encoding="utf-8") as f:
#         json.dump(
#             {
#                 "summary": summary,
#                 "state": _to_jsonable(output_state),
#             },
#             f,
#             ensure_ascii=False,
#             indent=2,
#         )

#     return run_dir


# def _to_jsonable(value):
#     """尽量把各种对象转成可 JSON 序列化结构（用于测试调试缓存）。"""
#     if value is None or isinstance(value, (str, int, float, bool)):
#         return value
#     if isinstance(value, BaseModel):
#         return value.model_dump(mode="json")
#     if isinstance(value, Path):
#         return str(value)
#     if isinstance(value, dict):
#         # 不缓存 transform_params（内容较长且噪声大，改动频繁），以便专注对比核心产出。
#         return {
#             str(k): _to_jsonable(v)
#             for k, v in value.items()
#             if str(k) != "transform_params"
#         }
#     if isinstance(value, (list, tuple)):
#         return [_to_jsonable(v) for v in value]
#     if isinstance(value, set):
#         return sorted([_to_jsonable(v) for v in value], key=lambda x: str(x))
#     # 兜底：转字符串，避免因不可序列化导致测试中断
#     return str(value)


# def _summarize_node_output(node_name: str, node_output) -> dict:
#     """给每个节点输出附加轻量摘要，便于快速定位变化。"""
#     output_dict: dict | None = None
#     if isinstance(node_output, dict):
#         output_dict = node_output
#     else:
#         # LangGraph 的特殊节点（如 __interrupt__）可能返回 () 或 (k, v) 列表
#         try:
#             output_dict = dict(node_output)
#         except Exception:
#             output_dict = None

#     summary: dict = {
#         "node_name": node_name,
#         "output_type": type(node_output).__name__,
#         "keys": (
#             sorted(list(output_dict.keys())) if isinstance(output_dict, dict) else []
#         ),
#     }
#     if node_name == "slice_node":
#         summary.update(
#             {
#                 "raw_chunks_count": len(
#                     (output_dict or {}).get("raw_chunks", []) or []
#                 ),
#                 "errors_count": len((output_dict or {}).get("errors", []) or []),
#             }
#         )
#     elif node_name == "classify_node":
#         summary.update(
#             {
#                 "classified_chunks_count": len(
#                     (output_dict or {}).get("classified_chunks", []) or []
#                 )
#             }
#         )
#     elif node_name == "transform_node":
#         summary.update(
#             {
#                 "final_chunks_count": len(
#                     (output_dict or {}).get("final_chunks", []) or []
#                 )
#             }
#         )
#     return summary


# @pytest.mark.asyncio
# async def test_full_parser_workflow_with_real_llm_logs_all_steps():
#     """使用真实 LLM 跑到 transform_node 前，缓存结构化中间结果。"""
#     load_env_if_exists()
#     if not os.environ.get("LLM_API_KEY"):
#         pytest.skip("环境变量 LLM_API_KEY 未设置，跳过真实 LLM 端到端测试")

#     md_content, _ = load_sample_markdown()
#     rules_dir = get_rules_dir()

#     initial_state = WorkflowState(
#         md_content=md_content,
#         doc_metadata={
#             "standard_no": "GB1886.169-2016",
#             "title": "《食品安全国家标准 食品添加剂 卡拉胶》（GB 1886.169-2016）第1号修改单",
#         },
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     # 将每个流程节点输出缓存为独立 JSON 文件，文件名包含流程名，便于离线分析。
#     default_cache_dir = Path(__file__).resolve().parents[2] / "artifacts"
#     run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
#     cache_run_dir = Path(
#         os.environ.get(
#             "WORKFLOW_CACHE_DIR",
#             str(default_cache_dir / f"parser_workflow_nodes_{run_id}"),
#         )
#     )
#     cache_run_dir.mkdir(parents=True, exist_ok=True)
#     structure_cache_path = Path(
#         os.environ.get(
#             "WORKFLOW_STRUCTURE_CACHE_PATH",
#             str(
#                 default_cache_dir
#                 / f"parser_workflow_structure_before_transform_{run_id}.json"
#             ),
#         )
#     )
#     structure_cache_path.parent.mkdir(parents=True, exist_ok=True)

#     index_path = cache_run_dir / "index.json"
#     index_data = {
#         "type": "meta",
#         "created_at": datetime.now().isoformat(timespec="seconds"),
#         "test": "test_full_parser_workflow_with_real_llm_logs_all_steps",
#         "rules_dir": str(rules_dir),
#         "doc_metadata": _to_jsonable(initial_state["doc_metadata"]),
#         "md_content_len": len(md_content),
#         "md_content_preview": md_content[:200],
#         "node_files": [],
#     }
#     with index_path.open("w", encoding="utf-8") as f:
#         json.dump(index_data, f, ensure_ascii=False, indent=2)

#     def _write_node_file(step_no: int, node_name: str, node_output: dict) -> None:
#         node_file = cache_run_dir / f"{step_no:02d}_{node_name}.json"
#         payload = {
#             "type": "update",
#             "at": datetime.now().isoformat(timespec="seconds"),
#             "summary": _summarize_node_output(node_name, node_output),
#             "node_output": _to_jsonable(node_output),
#         }
#         with node_file.open("w", encoding="utf-8") as f:
#             json.dump(payload, f, ensure_ascii=False, indent=2)
#         index_data["node_files"].append(node_file.name)
#         with index_path.open("w", encoding="utf-8") as f:
#             json.dump(index_data, f, ensure_ascii=False, indent=2)

#     # 通过 LangGraph streaming 逐节点记录日志，同时积累 transform 前的状态
#     result_state = dict(initial_state)
#     step_no = 0
#     async for chunk in parser_graph.astream(
#         initial_state,
#         stream_mode="updates",
#         interrupt_before=["transform_node"],
#     ):
#         for node_name, node_output in chunk.items():
#             step_no += 1
#             result_state.update(node_output)
#             _write_node_file(step_no, node_name, node_output)
#             if node_name == "parse_node":
#                 logger.info("parse_node result: %s", node_output)
#             elif node_name == "structure_node":
#                 logger.info("structure_node result: %s", node_output)
#             elif node_name == "slice_node":
#                 logger.info(
#                     "slice_node result: raw_chunks=%d, errors=%s",
#                     len(node_output.get("raw_chunks", [])),
#                     node_output.get("errors", []),
#                 )
#             elif node_name == "classify_node":
#                 logger.info(
#                     "classify_node result: classified_chunks=%d",
#                     len(node_output.get("classified_chunks", [])),
#                 )
#             elif node_name == "escalate_node":
#                 logger.info("escalate_node applied: reclassified all unknown segments")
#             elif node_name == "transform_node":
#                 logger.info(
#                     "transform_node result: final_chunks=%d",
#                     len(node_output.get("final_chunks", [])),
#                 )

#     with structure_cache_path.open("w", encoding="utf-8") as f:
#         json.dump(
#             {
#                 "type": "structure_snapshot_before_transform",
#                 "created_at": datetime.now().isoformat(timespec="seconds"),
#                 "test": "test_full_parser_workflow_with_real_llm_logs_all_steps",
#                 "rules_dir": str(rules_dir),
#                 "doc_metadata": _to_jsonable(result_state.get("doc_metadata", {})),
#                 "raw_chunks": _to_jsonable(result_state.get("raw_chunks", [])),
#                 "classified_chunks": _to_jsonable(
#                     result_state.get("classified_chunks", [])
#                 ),
#                 "errors": _to_jsonable(result_state.get("errors", [])),
#             },
#             f,
#             ensure_ascii=False,
#             indent=2,
#         )

#     escalate_count = sum(
#         1
#         for c in result_state["classified_chunks"]
#         if any(s.get("escalated") for s in c["segments"])
#     )
#     stats = {
#         "chunk_count": len(result_state.get("final_chunks", [])),
#         "classified_chunks_count": len(result_state.get("classified_chunks", [])),
#         "escalate_count": escalate_count,
#     }
#     logger.info("final doc_metadata: %s", result_state["doc_metadata"])
#     logger.info("final stats: %s", stats)
#     logger.info("workflow node files cached to: %s", cache_run_dir)
#     logger.info("workflow structure cached to: %s", structure_cache_path)

#     assert len(result_state["classified_chunks"]) > 0
#     assert len(result_state.get("final_chunks", [])) == 0
#     assert not result_state["errors"]


# def test_resume_workflow_from_cached_artifacts():
#     """
#     基于已缓存节点输出做断点续跑，便于按步骤验证后续节点行为。
#     用法示例：
#       WORKFLOW_RESUME_FROM=classify_node uv run pytest tests/core/parser_workflow/test_workflow.py -k resume -v -s
#     """
#     load_env_if_exists()
#     if not os.environ.get("LLM_API_KEY"):
#         pytest.skip("环境变量 LLM_API_KEY 未设置，跳过真实 LLM 断点续跑测试")

#     artifact_dir = _get_artifact_dir()
#     if not artifact_dir.exists():
#         pytest.skip(f"缓存目录不存在：{artifact_dir}")

#     resume_from = os.environ.get("WORKFLOW_RESUME_FROM", "classify_node")
#     state = _build_resume_initial_state(artifact_dir)
#     state = _load_cached_state_before_node(state, artifact_dir, resume_from)
#     input_state = _to_jsonable(state)
#     result_state = _run_from_resume_node(state, resume_from)
#     output_dir = _dump_resume_run_artifacts(
#         source_artifact_dir=artifact_dir,
#         resume_from=resume_from,
#         input_state=input_state,
#         output_state=result_state,
#     )

#     logger.info("resume_from=%s", resume_from)
#     logger.info("artifact_dir=%s", artifact_dir)
#     logger.info("resume artifacts dumped to=%s", output_dir)
#     logger.info("raw_chunks=%d", len(result_state.get("raw_chunks", [])))
#     logger.info("classified_chunks=%d", len(result_state.get("classified_chunks", [])))
#     logger.info("final_chunks=%d", len(result_state.get("final_chunks", [])))

#     assert len(result_state.get("classified_chunks", [])) > 0
#     assert len(result_state.get("final_chunks", [])) > 0
