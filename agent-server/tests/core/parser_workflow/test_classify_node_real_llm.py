# from typing import List

# import pytest

# from app.core.parser_workflow.models import ClassifiedChunk, RawChunk, WorkflowState
# from app.core.parser_workflow.nodes.classify_node import classify_node
# from app.core.parser_workflow.nodes.parse_node import parse_node
# from app.core.parser_workflow.nodes.slice_node import slice_node
# from .test_utils import ensure_llm_api_key, get_logger, get_rules_dir, load_sample_markdown

# logger = get_logger("classify_node_real_llm")


# @pytest.fixture(autouse=True)
# def _ensure_llm_key():
#     ensure_llm_api_key()


# def _build_state_with_preface_chunk() -> WorkflowState:
#     """构建只包含前言章节 chunk（section_path == ["前言"]）的 WorkflowState"""
#     md_content, _ = load_sample_markdown()
#     rules_dir = get_rules_dir()

#     initial_state = WorkflowState(
#         md_content=md_content,
#         doc_metadata={"standard_no": "GB1886.47-2016"},
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     parsed = parse_node(initial_state)
#     sliced = slice_node(
#         WorkflowState(
#             md_content=md_content,
#             doc_metadata=parsed["doc_metadata"],
#             config={},
#             rules_dir=str(rules_dir),
#             raw_chunks=[],
#             classified_chunks=[],
#             final_chunks=[],
#             errors=parsed["errors"],
#         )
#     )

#     raw_chunks: List[RawChunk] = sliced["raw_chunks"]

#     # "前言"是有标题的正式章节，section_path == ["前言"]
#     # 注意：__preamble__ 指第一个顶级标题前的无标题内容，该文档首行即为一级标题，故不存在
#     preface_chunks = [
#         c for c in raw_chunks if c["section_path"] == ["前言"]
#     ]
#     assert preface_chunks, (
#         "sample markdown 中未找到 section_path == ['前言'] 的 chunk，"
#         f"现有 section_path：{[c['section_path'] for c in raw_chunks]}"
#     )

#     logger.info(
#         "prepared preface chunk; content_preview=%r",
#         preface_chunks[0]["content"][:80],
#     )

#     return WorkflowState(
#         md_content=md_content,
#         doc_metadata=parsed["doc_metadata"],
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=preface_chunks,
#         classified_chunks=[],
#         final_chunks=[],
#         errors=parsed["errors"],
#     )


# def test_classify_node_returns_structured_segments_with_real_llm_and_rules():
#     """
#     通用结构验证：classify_node 能输出结构化 segments，包含必要字段。
#     """
#     state = _build_state_with_preface_chunk()
#     result = classify_node(state)
#     classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

#     assert classified_chunks, "classify_node 应该返回至少一个 ClassifiedChunk"

#     for idx, cc in enumerate(classified_chunks):
#         segments = cc["segments"]
#         logger.info(
#             "classified_chunk[%d]: has_unknown=%s, segments=%d",
#             idx, cc["has_unknown"], len(segments),
#         )
#         assert segments, "每个 ClassifiedChunk 至少应包含一个 segment"
#         for s_idx, seg in enumerate(segments):
#             logger.info(
#                 "segment[%d.%d]: type=%s, confidence=%s, content_preview=%r",
#                 idx, s_idx,
#                 seg.get("content_type"),
#                 seg.get("confidence"),
#                 (seg.get("content") or "")[:60],
#             )
#             assert seg.get("content"), "segment 应该包含 content"
#             assert "content_type" in seg
#             assert "confidence" in seg


# def test_classify_preface_chunk_as_single_preface_segment():
#     """
#     核心验证：前言 chunk 应整体分类为 1 个 preface segment，不拆分内部列表项。
#     """
#     state = _build_state_with_preface_chunk()
#     result = classify_node(state)
#     classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

#     assert len(classified_chunks) == 1
#     cc = classified_chunks[0]
#     segments = cc["segments"]

#     logger.info(
#         "preface chunk: segments=%d, types=%s",
#         len(segments),
#         [s.get("content_type") for s in segments],
#     )

#     assert len(segments) == 1, (
#         f"前言 chunk 应产生 1 个 segment，实际 {len(segments)} 个："
#         f"{[s.get('content_type') for s in segments]}"
#     )
#     assert segments[0]["content_type"] == "preface", (
#         f"前言 segment 的 content_type 应为 'preface'，实际：{segments[0]['content_type']!r}"
#     )
