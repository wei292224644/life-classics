# from parser.models import WorkflowState
# from parser.nodes.parse_node import parse_node
# from parser.nodes.slice_node import slice_node
# from .test_utils import get_logger, load_sample_markdown

# logger = get_logger("slice_node_real")


# def test_slice_node_produces_raw_chunks_from_real_markdown():
#     """
#     使用真实 markdown，验证 slice_node 能产生若干 RawChunk，且每个 chunk 具备必要字段。
#     """
#     md_content, _ = load_sample_markdown()

#     initial_state = WorkflowState(
#         md_content=md_content,
#         doc_metadata={
#             "standard_no": "GB1886.47-2016",
#             "title": "示例标准",
#         },
#         config={},
#         rules_dir="",
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     # 经过 parse_node 主要是为了保证 doc_metadata 结构完整；slice_node 本身只依赖 md_content 和 errors。
#     parsed = parse_node(initial_state)

#     # 示例 GB 标准 Markdown 全部使用一级标题 "#"，默认配置为 [2,3,4] 会匹配不到任何标题，
#     # 导致整篇被当成一块。此处显式传入 slice_heading_levels=[1,2,3] 以便按 "#" 切出多块。
#     state = WorkflowState(
#         md_content=md_content,
#         doc_metadata=parsed["doc_metadata"],
#         rules_dir="",
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=parsed["errors"],
#     )

#     result = slice_node(state)
#     raw_chunks = result["raw_chunks"]
#     errors = result["errors"]

#     logger.info(
#         "slice_node produced %d raw_chunks, errors=%s",
#         len(raw_chunks),
#         errors,
#     )

#     assert raw_chunks, "slice_node 应该从真实 markdown 中切出至少一个 RawChunk"

#     # 取前若干个 chunk 做结构性检查与日志输出
#     for idx, chunk in enumerate(raw_chunks):
#         logger.info(
#             "chunk[%d]: section_path=%s, char_count=%s, content_preview=%r",
#             idx,
#             chunk.get("section_path"),
#             chunk.get("char_count"),
#             (chunk.get("content") or ""),
#         )
#         assert chunk.get("content"), "RawChunk 应该包含 content"
#         assert isinstance(chunk.get("section_path"), list), "RawChunk.section_path 应该是列表"
#         assert isinstance(chunk.get("char_count"), int), "RawChunk.char_count 应该是整数"

