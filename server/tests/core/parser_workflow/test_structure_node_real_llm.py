# import pytest

# from worflow_parser_kb.models import WorkflowState
# from worflow_parser_kb.nodes.parse_node import parse_node
# from worflow_parser_kb.nodes.structure_node import structure_node
# from worflow_parser_kb.rules import RulesStore
# from .test_utils import ensure_llm_api_key, get_logger, get_rules_dir, load_sample_markdown

# logger = get_logger("structure_node_real_llm")


# @pytest.fixture(autouse=True)
# def _ensure_llm_key():
#     ensure_llm_api_key()


# def test_structure_node_infers_doc_type_with_real_llm_and_rules():
#     """
#     使用真实 markdown + 规则目录 + LLM，验证 structure_node 能为文档补全 doc_type，并记录来源。
#     """
#     md_content, _ = load_sample_markdown()
#     rules_dir = get_rules_dir()

#     # 先运行 parse_node 补全基础 meta
#     initial_state = WorkflowState(
#         md_content=md_content,
#         doc_metadata={"standard_no": "GB1886.47-2016", "title": "示例标准"},
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )
#     parsed = parse_node(initial_state)

#     state = WorkflowState(
#         md_content=md_content,
#         doc_metadata=parsed["doc_metadata"],
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=parsed["errors"],
#     )

#     result = structure_node(state)
#     meta = result["doc_metadata"]

#     logger.info("structure_node doc_metadata: %s", meta)

#     assert meta.get("doc_type"), "structure_node 应该为文档推断 doc_type"
#     assert meta.get("doc_type_source") in {
#         "rule",
#         "llm",
#     }, "doc_type_source 应该为 'rule' 或 'llm'"

#     # 若为 llm 推断，可以检查规则是否被追加（非严格断言，只作 sanity check）
#     if meta.get("doc_type_source") == "llm":
#         store = RulesStore(str(rules_dir))
#         doc_type_rules = store.get_doc_type_rules().get("doc_types", [])
#         logger.info("doc_type_rules count after llm inference: %d", len(doc_type_rules))

