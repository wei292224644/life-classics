# import pytest

# from app.core.parser_workflow.models import (
#     ClassifiedChunk,
#     RawChunk,
#     TypedSegment,
#     WorkflowState,
# )
# from app.core.parser_workflow.nodes.transform_node import transform_node
# from app.core.parser_workflow.rules import RulesStore
# from .test_utils import (
#     ensure_llm_api_key,
#     get_logger,
#     get_rules_dir,
# )

# logger = get_logger("transform_node_real_llm")
# pytestmark = pytest.mark.real_llm


# @pytest.fixture(autouse=True)
# def _ensure_llm_key():
#     ensure_llm_api_key()


# def test_transform_node_generates_document_chunks_with_real_llm_and_rules():
#     """
#     使用真实规则 + LLM，验证 transform_node 能将 TypedSegment 转写为 DocumentChunk：
#     - 生成非空 final_chunks
#     - 每个 chunk 字段齐全，meta 中包含 transform_strategy 和 segment_raw_content
#     """

#     rules_dir = get_rules_dir()
#     store = RulesStore(str(rules_dir))
#     semantic_types = store.get_content_type_rules().get("semantic_types", [])
#     assert semantic_types, "规则中应至少定义一个 semantic_type"
#     semantic_type = semantic_types[0]["id"]

#     state = WorkflowState(
#         md_content="食品安全国家标准 食品添加剂 卡拉胶",
#         doc_metadata={
#             "standard_no": "TEST001",
#         },
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[],
#         classified_chunks=[
#             ClassifiedChunk(
#                 raw_chunk=RawChunk(
#                     content="食品安全国家标准 食品添加剂 卡拉胶",
#                     section_path=["0"],
#                     char_count=17,
#                 ),
#                 segments=[
#                     TypedSegment(
#                         content="# 前言\n",
#                         structure_type="paragraph",
#                         semantic_type=semantic_type,
#                         transform_params=store.get_transform_params(semantic_type),
#                         confidence=0.9,
#                         escalated=False,
#                         cross_refs=[],
#                         ref_context="",
#                         failed_table_refs=[],
#                     ),
#                 ],
#                 has_unknown=False,
#             ),
#         ],
#         final_chunks=[],
#         errors=[],
#     )
#     result = transform_node(state)
#     assert result["final_chunks"], "transform_node 应该生成至少一个 DocumentChunk"
#     for chunk in result["final_chunks"]:
#         assert chunk["chunk_id"], "DocumentChunk 应该包含 chunk_id"
#         assert chunk["semantic_type"], "DocumentChunk 应该包含 semantic_type"
#         assert chunk["structure_type"], "DocumentChunk 应该包含 structure_type"
#         assert chunk["content"], "DocumentChunk 应该包含 content"
#         assert chunk["raw_content"], "DocumentChunk 应该保留原始 raw_content"
#         assert "transform_strategy" in chunk["meta"], "meta 中应包含 transform_strategy"
#         assert (
#             "segment_raw_content" in chunk["meta"]
#         ), "meta 中应包含 segment_raw_content"
