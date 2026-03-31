# from worflow_parser_kb.models import WorkflowState
# from worflow_parser_kb.nodes.parse_node import parse_node
# from .test_utils import get_logger, load_sample_markdown


# def test_parse_node_fills_title_from_markdown():
#     md_content, _ = load_sample_markdown()
#     logger = get_logger("parse_node_real")
#     state = WorkflowState(
#         md_content=md_content,
#         doc_metadata={"standard_no": "GB1886.47-2016"},
#         config={},
#         rules_dir="",
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     result = parse_node(state)
#     meta = result["doc_metadata"]

#     assert meta.get("title"), "parse_node 应该从 markdown 首行 # 标题中补全 title"


# def test_parse_node_adds_error_when_standard_no_missing():
#     md_content, _ = load_sample_markdown()
#     logger = get_logger("parse_node_real")
#     logger.info(md_content)
#     state = WorkflowState(
#         md_content=md_content,
#         doc_metadata={"title": "示例标准", "standard_no": "GB1886.47-2016"},
#         config={},
#         rules_dir="",
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     result = parse_node(state)
#     logger.info(result)
#     errors = result["errors"]

#     assert any(
#         "doc_metadata missing required field 'standard_no'" in e for e in errors
#     ), "缺少 standard_no 时应在 errors 中追加对应错误信息"
