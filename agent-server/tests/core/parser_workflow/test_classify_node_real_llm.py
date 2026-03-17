# from typing import List

# import pytest

# from app.core.parser_workflow.models import ClassifiedChunk, RawChunk, WorkflowState
# from app.core.parser_workflow.nodes.classify_node import classify_node
# from app.core.parser_workflow.nodes.parse_node import parse_node
# from app.core.parser_workflow.nodes.slice_node import slice_node
# from app.core.parser_workflow.structured_llm.errors import StructuredOutputError
# from .test_utils import ensure_llm_api_key, get_logger, get_rules_dir, load_sample_markdown

# logger = get_logger("classify_node_real_llm")
# pytestmark = pytest.mark.real_llm


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
#                 "segment[%d.%d]: structure=%s semantic=%s confidence=%s content_preview=%r",
#                 idx, s_idx,
#                 seg.get("structure_type"),
#                 seg.get("semantic_type"),
#                 seg.get("confidence"),
#                 (seg.get("content") or "")[:60],
#             )
#             assert seg.get("content"), "segment 应该包含 content"
#             assert "structure_type" in seg, "segment 应包含 structure_type"
#             assert "semantic_type" in seg, "segment 应包含 semantic_type"
#             assert seg["structure_type"] in {
#                 "paragraph", "list", "table", "formula", "header", "unknown"
#             }, f"非法 structure_type：{seg['structure_type']!r}"
#             assert seg["semantic_type"] in {
#                 "metadata", "scope", "limit", "procedure",
#                 "material", "calculation", "definition", "amendment", "unknown"
#             }, f"非法 semantic_type：{seg['semantic_type']!r}"
#             assert "confidence" in seg


# # def test_classify_preface_chunk_as_single_preface_segment():
# #     """
# #     核心验证：前言 chunk 应整体分类为 1 个 preface segment，不拆分内部列表项。
# #     """
# #     state = _build_state_with_preface_chunk()
# #     result = classify_node(state)
# #     classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

# #     assert len(classified_chunks) == 1
# #     cc = classified_chunks[0]
# #     segments = cc["segments"]

# #     logger.info(
# #         "preface chunk: segments=%d, types=%s",
# #         len(segments),
# #         [s.get("content_type") for s in segments],
# #     )

# #     assert len(segments) == 1, (
# #         f"前言 chunk 应产生 1 个 segment，实际 {len(segments)} 个："
# #         f"{[s.get('content_type') for s in segments]}"
# #     )
# #     assert segments[0]["content_type"] == "preface", (
# #         f"前言 segment 的 content_type 应为 'preface'，实际：{segments[0]['content_type']!r}"
# #     )



# def test_classify_node_handles_mixed_quotes_revision_chunk():
#     """
#     专项回归用例：复现"修改单 + 混合引号"片段在真实 LLM 下的结构化输出问题。
#     该用例用于跟踪修复进度，当前预期可能抛 StructuredOutputError。
#     """
#     rules_dir = get_rules_dir()
#     content = """# GB 1886.169—2016《食品安全国家标准 食品添加剂 卡拉胶》第 1 号修改单

# 本修改单经中华人民共和国国家卫生健康委员会和国家市场监督管理总局于 2021 年 2 月 22 日第 3 号公告批准，自 2021 年 2 月 22 日起实施。

# ## （修改事项）

# ### 一、1 范围

# 将"本标准适用于以红藻 (Rhodophyceae) 类植物为原料，经水或碱液等提取并加工而成的食品添加剂卡拉胶。产品为 K(Kappa)、I(Iota)、 $\\lambda$ (Lambda) 三种基本型号的混合物。"修改为"本标准适用于以红藻 (Rhodophyceae) 类植物为原料，经水或碱液等提取并加工而成的食品添加剂卡拉胶。卡拉胶中常见的多糖为 K(Kappa)、I(Iota)、 $\\lambda$ (Lambda) 三种。"

# ### 二、2.3 微生物指标

# 将表 3"大肠埃希氏菌 $\\mathrm{CFU / g}$ "指标 $<  10$ "修改为 $<  100$ "；将项目名称"沙门氏菌 (25g)"修改为"沙门氏菌 (1g)"。
# """

#     state: WorkflowState = WorkflowState(
#         md_content=content,
#         doc_metadata={"standard_no": "GB1886.169-2016", "title": "修改单片段"},
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[
#             RawChunk(
#                 content=content,
#                 section_path=["修改事项"],
#                 char_count=len(content),
#             )
#         ],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     result = classify_node(state)

#     classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]
#     assert classified_chunks, "classify_node 应返回至少一个 ClassifiedChunk"
#     assert classified_chunks[0]["segments"], "该 chunk 至少应返回一个 segment"
#     for cc in classified_chunks:
#         for seg in cc["segments"]:
#             assert "structure_type" in seg
#             assert "semantic_type" in seg
