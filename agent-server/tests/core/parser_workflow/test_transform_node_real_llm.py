import json
from pathlib import Path

import pytest

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.nodes.transform_node import transform_node
from app.core.parser_workflow.rules import RulesStore
from .test_utils import (
    ensure_llm_api_key,
    get_logger,
    get_rules_dir,
)

logger = get_logger("transform_node_real_llm")
pytestmark = pytest.mark.real_llm


@pytest.fixture(autouse=True)
def _ensure_llm_key():
    ensure_llm_api_key()


def _load_classified_chunk_from_resume_artifact(section_title: str) -> ClassifiedChunk:
    artifact_path = (
        Path(__file__).resolve().parents[2]
        / "artifacts"
        / "parser_workflow_resume_20260318_152626"
        / "00_resume_input_state.json"
    )
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    for item in payload.get("classified_chunks", []):
        section_path = item.get("raw_chunk", {}).get("section_path", [])
        if section_path and section_path[-1] == section_title:
            return item
    raise AssertionError(f"未在缓存中找到 section={section_title} 的 classified_chunk")


def test_transform_node_generates_document_chunks_with_real_llm_and_rules():
    """
    使用真实规则 + LLM，验证 transform_node 能将 TypedSegment 转写为 DocumentChunk：
    - 生成非空 final_chunks
    - 每个 chunk 字段齐全，meta 中包含 transform_strategy 和 segment_raw_content
    """

    rules_dir = get_rules_dir()
    store = RulesStore(str(rules_dir))
    semantic_types = store.get_content_type_rules().get("semantic_types", [])
    assert semantic_types, "规则中应至少定义一个 semantic_type"
    semantic_type = semantic_types[0]["id"]

    state = WorkflowState(
        md_content="食品安全国家标准 食品添加剂 卡拉胶",
        doc_metadata={
            "standard_no": "TEST001",
        },
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[
            ClassifiedChunk(
                raw_chunk=RawChunk(
                    content="食品安全国家标准 食品添加剂 卡拉胶",
                    section_path=["0"],
                    char_count=17,
                ),
                segments=[
                    TypedSegment(
                        content="# 前言\n",
                        structure_type="paragraph",
                        semantic_type=semantic_type,
                        transform_params=store.get_transform_params(semantic_type),
                        confidence=0.9,
                        escalated=False,
                        cross_refs=[],
                        ref_context="",
                        failed_table_refs=[],
                    ),
                ],
                has_unknown=False,
            ),
        ],
        final_chunks=[],
        errors=[],
    )
    result = transform_node(state)
    assert result["final_chunks"], "transform_node 应该生成至少一个 DocumentChunk"
    for chunk in result["final_chunks"]:
        assert chunk["chunk_id"], "DocumentChunk 应该包含 chunk_id"
        assert chunk["semantic_type"], "DocumentChunk 应该包含 semantic_type"
        assert chunk["structure_type"], "DocumentChunk 应该包含 structure_type"
        assert chunk["content"], "DocumentChunk 应该包含 content"
        assert chunk["raw_content"], "DocumentChunk 应该保留原始 raw_content"
        assert "transform_strategy" in chunk["meta"], "meta 中应包含 transform_strategy"
        assert (
            "segment_raw_content" in chunk["meta"]
        ), "meta 中应包含 segment_raw_content"


def test_transform_node_amendment_paragraph_from_resume_artifact():
    """
    针对真实缓存中的 amendment 片段做定向测试，观察 transform_node 的实际转写结果。
    样本来源：tests/artifacts/parser_workflow_resume_20260318_152626/00_resume_input_state.json
    """
    rules_dir = get_rules_dir()
    store = RulesStore(str(rules_dir))

    amendment_content = (
        "### 二、2.3 微生物指标\n\n"
        "将表 3“大肠埃希氏菌 $\\mathrm{CFU / g}$ \"指标 $<  10$ \"修改为 $<  100$ \"；"
        "将项目名称“沙门氏菌 (25g)\"修改为“沙门氏菌 (1g)\"。"
    )

    state = WorkflowState(
        md_content="",
        doc_metadata={
            "standard_no": "GB1886.169-2016",
            "title": "《食品安全国家标准 食品添加剂 卡拉胶》（GB 1886.169-2016）第1号修改单",
        },
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[
            ClassifiedChunk(
                raw_chunk=RawChunk(
                    content=amendment_content,
                    section_path=["二、2.3 微生物指标"],
                    char_count=len(amendment_content),
                ),
                segments=[
                    TypedSegment(
                        content=amendment_content,
                        structure_type="paragraph",
                        semantic_type="amendment",
                        transform_params=store.get_transform_params("amendment"),
                        confidence=0.96,
                        escalated=False,
                        cross_refs=["2.3"],
                        ref_context="",
                        failed_table_refs=[],
                    )
                ],
                has_unknown=False,
            )
        ],
        final_chunks=[],
        errors=[],
    )

    result = transform_node(state)
    print(result)
    assert result["final_chunks"], "应至少生成一个 transformed chunk"
    assert len(result["final_chunks"]) == 1, "该定向输入预期仅产生一个 chunk"

    chunk = result["final_chunks"][0]
    logger.info("amendment transformed content: %s", chunk["content"])

    assert chunk["semantic_type"] == "amendment"
    assert chunk["structure_type"] == "paragraph"
    assert chunk["meta"]["transform_strategy"] == "list_to_text"
    assert chunk["meta"]["cross_refs"] == ["2.3"]
    assert chunk["meta"]["failed_table_refs"] == []
    assert chunk["meta"]["segment_raw_content"] == amendment_content

    transformed = chunk["content"]
    assert "大肠埃希氏菌" in transformed
    assert "100" in transformed
    assert "沙门氏菌" in transformed
    assert "(1g)" in transformed


def test_transform_node_a6_chunk_from_resume_artifact():
    """
    针对 A.6 酸不溶灰分整块内容做定向测试，验证 transform_node 的分段转写产物。
    样本来源：tests/artifacts/parser_workflow_resume_20260318_152626/00_resume_input_state.json
    """
    rules_dir = get_rules_dir()
    store = RulesStore(str(rules_dir))
    classified_chunk = _load_classified_chunk_from_resume_artifact("A.6 酸不溶灰分的测定")

    # 该缓存由 classify_node 输出，不含 transform_params；这里按 semantic_type 补齐。
    for seg in classified_chunk.get("segments", []):
        semantic_type = seg["semantic_type"]
        seg["transform_params"] = store.get_transform_params(semantic_type)

    state = WorkflowState(
        md_content="",
        doc_metadata={
            "standard_no": "GB1886.169-2016",
            "title": "《食品安全国家标准 食品添加剂 卡拉胶》（GB 1886.169-2016）第1号修改单",
        },
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[classified_chunk],
        final_chunks=[],
        errors=[],
    )

    result = transform_node(state)
    print(result)
    assert result["final_chunks"], "A.6 场景应生成 transformed chunks"
    assert len(result["final_chunks"]) == 7, "A.6 classified_segments 预期对应 7 个输出 chunk"

    chunks = result["final_chunks"]
    logger.info("A.6 transformed chunk count: %d", len(chunks))
    for idx, chunk in enumerate(chunks, 1):
        logger.info(
            "A.6 chunk[%d] semantic=%s structure=%s content=%s",
            idx,
            chunk["semantic_type"],
            chunk["structure_type"],
            chunk["content"],
        )

    assert chunks[0]["semantic_type"] == "metadata"
    assert chunks[1]["semantic_type"] == "material"
    assert chunks[2]["semantic_type"] == "material"
    assert chunks[3]["semantic_type"] == "procedure"
    assert chunks[4]["semantic_type"] == "calculation"
    assert chunks[5]["semantic_type"] == "calculation"
    assert chunks[6]["semantic_type"] == "limit"

    joined_content = "\n".join(chunk["content"] for chunk in chunks)
    assert "酸不溶灰分" in joined_content
    assert "A.6.3" in joined_content or "分析步骤" in joined_content
    assert "A.2" in joined_content or "w" in joined_content
    assert "10%" in joined_content or "10 %" in joined_content
