# import json
# from pathlib import Path
# from typing import List

# import pytest

# from parser.models import ClassifiedChunk, RawChunk, WorkflowState
# from parser.nodes.classify_node import classify_node, classify_raw_chunk
# from parser.nodes.parse_node import parse_node
# from parser.nodes.output import ClassifyOutput
# from parser.nodes.slice_node import slice_node
# from parser.structured_llm import invoke_structured
# from parser.structured_llm.errors import StructuredOutputError
# from parser.rules import RulesStore
# from .test_utils import (
#     ensure_llm_api_key,
#     get_logger,
#     get_rules_dir,
#     load_sample_markdown,
# )

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
#     preface_chunks = [c for c in raw_chunks if c["section_path"] == ["前言"]]
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


# def _load_a6_raw_chunk_from_slice_artifact() -> RawChunk:
#     artifact_path = (
#         Path(__file__).resolve().parents[2]
#         / "artifacts"
#         / "parser_workflow_nodes_20260318_150146"
#         / "03_slice_node.json"
#     )
#     payload = json.loads(artifact_path.read_text(encoding="utf-8"))
#     raw_chunks = payload.get("node_output", {}).get("raw_chunks", [])
#     for chunk in raw_chunks:
#         section_path = chunk.get("section_path", [])
#         if section_path and section_path[-1] == "A.6 酸不溶灰分的测定":
#             return RawChunk(
#                 content=chunk["content"],
#                 section_path=chunk["section_path"],
#                 char_count=chunk["char_count"],
#             )
#     raise AssertionError("未在 03_slice_node.json 中找到 A.6 酸不溶灰分的测定 raw_chunk")


# # def test_classify_node_returns_structured_segments_with_real_llm_and_rules():
# #     """
# #     通用结构验证：classify_node 能输出结构化 segments，包含必要字段。
# #     """
# #     state = _build_state_with_preface_chunk()
# #     result = classify_node(state)
# #     classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

# #     assert classified_chunks, "classify_node 应该返回至少一个 ClassifiedChunk"

# #     for idx, cc in enumerate(classified_chunks):
# #         segments = cc["segments"]
# #         logger.info(
# #             "classified_chunk[%d]: has_unknown=%s, segments=%d",
# #             idx, cc["has_unknown"], len(segments),
# #         )
# #         assert segments, "每个 ClassifiedChunk 至少应包含一个 segment"
# #         for s_idx, seg in enumerate(segments):
# #             logger.info(
# #                 "segment[%d.%d]: structure=%s semantic=%s confidence=%s content_preview=%r",
# #                 idx, s_idx,
# #                 seg.get("structure_type"),
# #                 seg.get("semantic_type"),
# #                 seg.get("confidence"),
# #                 (seg.get("content") or "")[:60],
# #             )
# #             assert seg.get("content"), "segment 应该包含 content"
# #             assert "structure_type" in seg, "segment 应包含 structure_type"
# #             assert "semantic_type" in seg, "segment 应包含 semantic_type"
# #             assert seg["structure_type"] in {
# #                 "paragraph", "list", "table", "formula", "header", "unknown"
# #             }, f"非法 structure_type：{seg['structure_type']!r}"
# #             assert seg["semantic_type"] in {
# #                 "metadata", "scope", "limit", "procedure",
# #                 "material", "calculation", "definition", "amendment", "unknown"
# #             }, f"非法 semantic_type：{seg['semantic_type']!r}"
# #             assert "confidence" in seg


# # def test_classify_node_handles_mixed_quotes_revision_chunk():
# #     """
# #     专项回归用例：复现"修改单 + 混合引号"片段在真实 LLM 下的结构化输出问题。
# #     该用例用于跟踪修复进度，当前预期可能抛 StructuredOutputError。
# #     """
# #     rules_dir = get_rules_dir()
# #     content = """# GB 1886.169—2016《食品安全国家标准 食品添加剂 卡拉胶》第 1 号修改单

# # 本修改单经中华人民共和国国家卫生健康委员会和国家市场监督管理总局于 2021 年 2 月 22 日第 3 号公告批准，自 2021 年 2 月 22 日起实施。

# # ## （修改事项）

# # ### 一、1 范围

# # 将"本标准适用于以红藻 (Rhodophyceae) 类植物为原料，经水或碱液等提取并加工而成的食品添加剂卡拉胶。产品为 K(Kappa)、I(Iota)、 $\\lambda$ (Lambda) 三种基本型号的混合物。"修改为"本标准适用于以红藻 (Rhodophyceae) 类植物为原料，经水或碱液等提取并加工而成的食品添加剂卡拉胶。卡拉胶中常见的多糖为 K(Kappa)、I(Iota)、 $\\lambda$ (Lambda) 三种。"

# # ### 二、2.3 微生物指标

# # 将表 3"大肠埃希氏菌 $\\mathrm{CFU / g}$ "指标 $<  10$ "修改为 $<  100$ "；将项目名称"沙门氏菌 (25g)"修改为"沙门氏菌 (1g)"。
# # """

# #     state: WorkflowState = WorkflowState(
# #         md_content=content,
# #         doc_metadata={"standard_no": "GB1886.169-2016", "title": "修改单片段"},
# #         config={},
# #         rules_dir=str(rules_dir),
# #         raw_chunks=[
# #             RawChunk(
# #                 content=content,
# #                 section_path=["修改事项"],
# #                 char_count=len(content),
# #             )
# #         ],
# #         classified_chunks=[],
# #         final_chunks=[],
# #         errors=[],
# #     )

# #     result = classify_node(state)

# #     classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]
# #     assert classified_chunks, "classify_node 应返回至少一个 ClassifiedChunk"
# #     assert classified_chunks[0]["segments"], "该 chunk 至少应返回一个 segment"
# #     for cc in classified_chunks:
# #         for seg in cc["segments"]:
# #             assert "structure_type" in seg
# #             assert "semantic_type" in seg


# def test_classify_prompt_regression_with_mixed_quotes_sample():
#     """
#     使用线上报错同款提示词 + 修改单片段，单独验证 classify 结构化输出。
#     用于复现/跟踪 mixed quotes 导致的 JSON 结构破坏问题。
#     """
#     rules_dir = get_rules_dir()
#     store = RulesStore(str(rules_dir))
#     ct_rules = store.get_content_type_rules()
#     structure_types = ct_rules.get("structure_types", [])
#     semantic_types = ct_rules.get("semantic_types", [])
#     assert (
#         structure_types and semantic_types
#     ), "规则中 structure_types/semantic_types 不应为空"

#     structure_desc = "\n".join(
#         f"- {t['id']}: {t['description']}" for t in structure_types
#     )
#     semantic_desc = "\n".join(
#         f"- {t['id']}: {t['description']}" for t in semantic_types
#     )

#     content = """# GB 1886.169—2016《食品安全国家标准 食品添加剂 卡拉胶》第 1 号修改单

# 本修改单经中华人民共和国国家卫生健康委员会和国家市场监督管理总局于 2021 年 2 月 22 日第 3 号公告批准，自 2021 年 2 月 22 日起实施。

# ## （修改事项）

# ### 一、1 范围

# 将“本标准适用于以红藻 (Rhodophyceae) 类植物为原料，经水或碱液等提取并加工而成的食品添加剂卡拉胶。产品为 K(Kappa)、I(Iota)、 $\\lambda$ (Lambda) 三种基本型号的混合物。”修改为“本标准适用于以红藻 (Rhodophyceae) 类植物为原料，经水或碱液等提取并加工而成的食品添加剂卡拉胶。卡拉胶中常见的多糖为 K(Kappa)、I(Iota)、 $\\lambda$ (Lambda) 三种。”

# ### 二、2.3 微生物指标

# 将表 3“大肠埃希氏菌 $\\mathrm{CFU / g}$ "指标 $<  10$ "修改为 $<  100$ "；将项目名称“沙门氏菌 (25g)"修改为“沙门氏菌 (1g)"。
# """

#     prompt = f"""请将以下文本拆分为语义独立的片段，并对每个片段进行双维度分类。

# 【结构类型（structure_type）】——描述内容的呈现形式：
# {structure_desc}

# 【语义类型（semantic_type）】——描述内容对读者的用途：
# {semantic_desc}

# 分类规则（强约束，必须满足）：
# 1. 保守切分：只在相邻内容属于明显不同语义单元时才切分；同一逻辑章节保持整体。
# 2. 对每个片段独立推断两个维度，互不干扰：先判断呈现形式（structure_type），再判断用途（semantic_type）。
# 3. confidence 反映你对两个判断综合的把握程度（0-1）。
# 4. 仅返回合法 JSON 对象，顶层必须是 `{{"segments": [...]}}`，禁止任何额外文本、注释、Markdown。
# 5. segments 中每个元素必须是对象，且必须包含：content、structure_type、semantic_type、confidence。
# 6. 禁止无意义片段：不得输出仅由标点/空白组成的 content（如 "。", "；", ",", "..."）。
# 7. content 不能为空，去除首尾空白后长度必须 >= 2；且应为可独立理解的完整语义单元。
# 8. 不得把字段名或字段值拆成数组元素（禁止出现 `"structure_type", "paragraph"` 这类断裂形式）。
# 9. 如果某句过短但有明确语义（如“不得检出”），可与相邻上下文合并后再输出，避免孤立噪声片段。
# 10. 如果有公式，请保持为可解析的完整片段，不要截断或拆坏 JSON 结构。

# 文本内容：
# {content}
# """

#     result = invoke_structured(
#         node_name="classify_node",
#         prompt=prompt,
#         max_retries=0,
#         response_model=ClassifyOutput,
#         extra_body={"enable_thinking": False},
#     )
#     print(result)
#     assert result.segments, "应至少返回一个 segment"
#     for seg in result.segments:
#         content_text = (seg.content or "").strip()
#         assert content_text, "segment.content 不能为空"
#         assert len(content_text) >= 2, f"segment.content 过短：{content_text!r}"
#         assert content_text not in {"。", "，", "；", "：", ".", ",", ";", ":"}
#         assert seg.structure_type
#         assert seg.semantic_type
#         assert 0 <= seg.confidence <= 1


# def test_header_semantic_type_is_metadata_for_method_sections():
#     """附录方法节标题 header 的 semantic_type 应一律为 metadata"""
#     store = RulesStore(str(get_rules_dir()))
#     content = "## A.5 总灰分的测定"
#     chunk = RawChunk(content=content, section_path=["A.5"], char_count=len(content))
#     result = classify_raw_chunk(chunk, store)
#     seg = result.segments[0]
#     assert seg.structure_type == "header"
#     assert seg.semantic_type == "metadata"


# def test_header_semantic_type_a6():
#     store = RulesStore(str(get_rules_dir()))
#     content = "## A.6 酸不溶灰分的测定"
#     chunk = RawChunk(content=content, section_path=["A.6"], char_count=len(content))
#     result = classify_raw_chunk(chunk, store)
#     assert result.segments[0].semantic_type == "metadata"


# def test_document_identity_metadata_not_degraded():
#     """文档身份信息 semantic_type 不退化"""
#     store = RulesStore(str(get_rules_dir()))
#     content = "GB 1886.169—2016\n2016-08-31 发布  2017-01-01 实施"
#     chunk = RawChunk(content=content, section_path=[], char_count=len(content))
#     result = classify_raw_chunk(chunk, store)
#     assert any(seg.semantic_type == "metadata" for seg in result.segments)


# def test_definition_body_not_misclassified_as_metadata():
#     """含实质术语正文的段落仍分类为 definition，不被误归为 metadata"""
#     store = RulesStore(str(get_rules_dir()))
#     content = "3 术语和定义\n3.1 卡拉胶\n卡拉胶是指以红藻类植物为原料..."
#     chunk = RawChunk(content=content, section_path=["3"], char_count=len(content))
#     result = classify_raw_chunk(chunk, store)
#     assert any(seg.semantic_type == "definition" for seg in result.segments)


# def test_classify_node_html_table_attribute_content_preserved_with_real_llm():
#     """
#     回归测试（ISSUE-02）：含 rowspan 属性的 HTML 表格 chunk 经 classify 后，
#     所有 segment content 拼合仍应包含 rowspan="2"，属性不得被 LLM 篡改。
#     """
#     rules_dir = get_rules_dir()
#     html_content = (
#         "<table>\n"
#         '<tr><td rowspan="2">取适量试样置于清洁、干燥的白瓷盘中，'
#         "在自然光线下观察其色泽和状态</td><td>符合要求</td></tr>\n"
#         "<tr><td>无异味</td></tr>\n"
#         "</table>"
#     )

#     state = WorkflowState(
#         md_content=html_content,
#         doc_metadata={"standard_no": "TEST-HTML-ATTR"},
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[
#             RawChunk(
#                 content=html_content,
#                 section_path=["感官要求"],
#                 char_count=len(html_content),
#             )
#         ],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     result = classify_node(state)
#     classified_chunks = result["classified_chunks"]

#     assert classified_chunks, "classify_node 应返回至少一个 ClassifiedChunk"

#     all_content = "".join(
#         seg.get("content", "")
#         for cc in classified_chunks
#         for seg in cc.get("segments", [])
#     )

#     logger.info("all_content from segments: %r", all_content)

#     assert 'rowspan="2"' in all_content, (
#         f'HTML 属性 rowspan="2" 在 segment content 中丢失或被篡改。\n'
#         f"拼合内容：{all_content!r}"
#     )

#     store = RulesStore(str(rules_dir))
#     ct_rules = store.get_content_type_rules()
#     valid_structure_types = {t["id"] for t in ct_rules.get("structure_types", [])} | {"unknown"}
#     valid_semantic_types = {t["id"] for t in ct_rules.get("semantic_types", [])} | {"unknown"}
#     for cc in classified_chunks:
#         for seg in cc.get("segments", []):
#             assert seg.get("structure_type") in valid_structure_types, (
#                 f"非法 structure_type：{seg.get('structure_type')!r}"
#             )
#             assert seg.get("semantic_type") in valid_semantic_types, (
#                 f"非法 semantic_type：{seg.get('semantic_type')!r}"
#             )
#             assert 0 <= seg.get("confidence", -1) <= 1, (
#                 f"confidence 超出范围：{seg.get('confidence')!r}"
#             )
#             assert seg.get("content"), "segment content 不能为空"


# def test_classify_node_a6_chunk_from_slice_artifact_with_real_llm():
#     """
#     定向回归：使用 03_slice_node.json 中 A.6 原始 chunk，验证 classify 分段与语义覆盖。
#     """
#     rules_dir = get_rules_dir()
#     a6_raw_chunk = _load_a6_raw_chunk_from_slice_artifact()
#     state = WorkflowState(
#         md_content=a6_raw_chunk["content"],
#         doc_metadata={"standard_no": "GB1886.169-2016"},
#         config={},
#         rules_dir=str(rules_dir),
#         raw_chunks=[a6_raw_chunk],
#         classified_chunks=[],
#         final_chunks=[],
#         errors=[],
#     )

#     result = classify_node(state)
#     print(result)
#     classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]
#     assert len(classified_chunks) == 1, "A.6 定向输入应仅返回一个 ClassifiedChunk"

#     segments = classified_chunks[0]["segments"]
#     assert segments, "A.6 chunk 应至少被切分出一个 segment"
#     logger.info("A.6 classify segment_count=%d", len(segments))
#     for idx, seg in enumerate(segments, 1):
#         logger.info(
#             "A.6 seg[%d] structure=%s semantic=%s confidence=%.3f content=%r",
#             idx,
#             seg.get("structure_type"),
#             seg.get("semantic_type"),
#             seg.get("confidence"),
#             (seg.get("content") or "")[:120],
#         )

#     semantic_types = [seg["semantic_type"] for seg in segments]
#     assert "metadata" in semantic_types
#     assert semantic_types.count("material") >= 1
#     assert "procedure" in semantic_types
#     assert semantic_types.count("calculation") >= 1
#     assert "limit" in semantic_types

#     has_formula = any(
#         seg["structure_type"] == "formula" and "A.2" in (seg.get("content") or "")
#         for seg in segments
#     )
#     assert has_formula, "A.6 应包含式 (A.2) 的公式 segment"
