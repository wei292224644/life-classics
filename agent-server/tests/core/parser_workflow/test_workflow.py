import pytest
from unittest.mock import patch
import logging
import os
from pathlib import Path

from app.core.parser_workflow import run_parser_workflow
from app.core.parser_workflow.models import WorkflowState
from app.core.parser_workflow.nodes.parse_node import parse_node
from app.core.parser_workflow.nodes.structure_node import structure_node
from app.core.parser_workflow.nodes.slice_node import slice_node
from app.core.parser_workflow.nodes.classify_node import classify_node
from app.core.parser_workflow.nodes.escalate_node import escalate_node
from app.core.parser_workflow.nodes.transform_node import transform_node

# 一份模拟的 GB 单品标准 MD 文件内容
SAMPLE_MD = """# GB 8821-2011 食品安全国家标准 食品添加剂 β-胡萝卜素

## 范围

本标准适用于以β-胡萝卜素为主要成分的食品添加剂。

## 技术要求

本品应符合以下理化指标要求。含量不低于 96%。

### 理化指标

| 项目 | 指标 |
|---|---|
| 含量（以干基计）% | ≥96.0 |
| 干燥减量 % | ≤0.2 |
| 灼烧残渣 % | ≤0.2 |

## 检验规则

按批次检验。每批次应提供检验报告。
"""

CLASSIFY_MOCK = {
    "segments": [
        {"content": SAMPLE_MD, "content_type": "plain_text", "confidence": 0.88},
    ],
}

TABLE_CLASSIFY_MOCK = {
    "segments": [
        {
            "content": "| 项目 | 指标 |\n|---|---|\n| 含量（以干基计）% | ≥96.0 |\n| 干燥减量 % | ≤0.2 |\n| 灼烧残渣 % | ≤0.2 |",
            "content_type": "table",
            "confidence": 0.95,
        },
    ],
}


def _mock_classify(chunk_content, content_types, config):
    if "|" in chunk_content and "---" in chunk_content:
        return TABLE_CLASSIFY_MOCK
    return CLASSIFY_MOCK


@pytest.mark.asyncio
async def test_end_to_end_produces_document_chunks(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        side_effect=_mock_classify,
    ), patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="转写后内容",
    ):
        result = await run_parser_workflow(
            md_content=SAMPLE_MD,
            doc_metadata={"standard_no": "GB8821", "title": "β-胡萝卜素"},
            rules_dir=str(tmp_path),
            config={},
        )
    assert len(result["chunks"]) > 0
    assert result["doc_metadata"]["standard_no"] == "GB8821"
    assert result["stats"]["chunk_count"] == len(result["chunks"])


@pytest.mark.asyncio
async def test_end_to_end_table_produces_split_row_chunks(tmp_path):
    table_md = """# GB 8821-2011

## 技术要求

### 理化指标

| 项目 | 指标 |
|---|---|
| 含量 | ≥96% |
| 水分 | ≤0.5% |
"""
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=TABLE_CLASSIFY_MOCK,
    ), patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        side_effect=["行1 转写", "行2 转写"],
    ):
        result = await run_parser_workflow(
            md_content=table_md,
            doc_metadata={"standard_no": "GB8821", "title": "t"},
            rules_dir=str(tmp_path),
            config={},
        )
    table_chunks = [c for c in result["chunks"] if c["content_type"] == "table"]
    assert len(table_chunks) == 2  # 2 data rows


@pytest.mark.asyncio
async def test_end_to_end_no_llm_key_still_works_with_mocked_classify(tmp_path):
    """验证在没有真实 LLM 密钥时，通过 mock 可以完整运行。
    使用含 '技术要求' 关键词的 MD，确保 structure_node 规则命中，无需 LLM 兜底。"""
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=CLASSIFY_MOCK,
    ), patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="转写后内容",
    ):
        result = await run_parser_workflow(
            md_content="## 技术要求\n\n含量不低于 96%。\n\n## 检验规则\n\n按批次检验。",
            doc_metadata={"standard_no": "GB0000", "title": "测试标准"},
            rules_dir=str(tmp_path),
            config={},
        )
    assert len(result["errors"]) == 0 or all(
        "standard_no" not in e for e in result["errors"]
    )
    assert result["stats"]["chunk_count"] >= 1


@pytest.mark.asyncio
async def test_end_to_end_records_error_when_standard_no_missing(tmp_path):
    """使用含规则关键词的 MD，确保 structure_node 规则命中，不触发 LLM 兜底。"""
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=CLASSIFY_MOCK,
    ), patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="转写后内容",
    ):
        result = await run_parser_workflow(
            md_content="## 技术要求\n\n含量不低于 96%。",
            doc_metadata={"title": "无编号标准"},
            rules_dir=str(tmp_path),
            config={},
        )
    assert any("standard_no" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_end_to_end_escalate_path_and_stats(tmp_path):
    """验证含 unknown 片段时，escalate 路径被触发，stats.escalate_count 正确。
    使用含规则关键词的 MD，确保 structure_node 规则命中。"""
    low_conf_classify = {
        "segments": [
            {"content": "奇怪内容", "content_type": "plain_text", "confidence": 0.2}
        ],
    }
    escalate_response = {
        "action": "create_new",
        "content_type": "new_type",
        "description": "新类型描述",
        "transform": {
            "strategy": "llm_transform",
            "prompt_template": "请转化：{content}",
        },
    }
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=low_conf_classify,
    ), patch(
        "app.core.parser_workflow.nodes.escalate_node._call_escalate_llm",
        return_value=escalate_response,
    ), patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="转化后内容",
    ):
        result = await run_parser_workflow(
            md_content="## 技术要求\n\n奇怪内容。\n\n## 检验规则\n\n按批次检验。",
            doc_metadata={"standard_no": "GB0000", "title": "t"},
            rules_dir=str(tmp_path),
            config={"confidence_threshold": 0.7},
        )
    assert result["stats"]["escalate_count"] >= 1
    assert all(c["content_type"] != "unknown" for c in result["chunks"])


@pytest.mark.asyncio
async def test_full_parser_workflow_with_real_llm_logs_all_steps():
    """使用真实 LLM + 实际规则目录，跑完整个 parser_workflow，并将每个阶段的结果打日志。"""
    logger = logging.getLogger("parser_workflow_real_llm")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

    asset_path = (
        Path(__file__)
        .resolve()
        .parents[2]
        / "assets"
        / "《食品安全国家标准 食品添加剂 天门冬酰苯丙氨酸甲酯（又名阿斯巴甜）》（GB 1886.47-2016）第1号修改单.md"
    )
    md_content = asset_path.read_text(encoding="utf-8")

    # project_root 指向 agent-server 根目录
    project_root = Path(__file__).resolve().parents[3]
    rules_dir = project_root / "app" / "core" / "parser_workflow" / "rules"

    env_path = project_root / ".env"
    if not os.environ.get("LLM_API_KEY") and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

    config = {
        "classify_model": os.environ.get("CLASSIFY_MODEL", "gpt-4o-mini"),
        "escalate_model": os.environ.get("ESCALATE_MODEL", "gpt-4o"),
        "transform_model": os.environ.get("TRANSFORM_MODEL", "gpt-4o-mini"),
        "doc_type_llm_model": os.environ.get("DOC_TYPE_LLM_MODEL", "gpt-4o-mini"),
        "llm_api_key": os.environ.get("LLM_API_KEY", ""),
        "llm_base_url": os.environ.get("LLM_BASE_URL", ""),
        "confidence_threshold": 0.7,
    }

    if not config["llm_api_key"]:
        pytest.skip("环境变量 LLM_API_KEY 未设置，跳过真实 LLM 端到端测试")

    state: WorkflowState = {
        "md_content": md_content,
        "doc_metadata": {
            "standard_no": "GB1886.47-2016",
            "title": "食品添加剂 天门冬酰苯丙氨酸甲酯（又名阿斯巴甜） 第1号修改单",
        },
        "config": config,
        "rules_dir": str(rules_dir),
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": [],
        "errors": [],
    }

    step = parse_node(state)
    state.update(step)
    logger.info("parse_node result: %s", step)

    step = structure_node(state)
    state.update(step)
    logger.info("structure_node result: %s", step)

    step = slice_node(state)
    state.update(step)
    logger.info("slice_node result: raw_chunks=%d, errors=%s", len(state["raw_chunks"]), state["errors"])

    step = classify_node(state)
    state.update(step)
    logger.info(
        "classify_node result: classified_chunks=%d",
        len(state["classified_chunks"]),
    )

    if any(c["has_unknown"] for c in state["classified_chunks"]):
        step = escalate_node(state)
        state.update(step)
        logger.info("escalate_node applied: reclassified all unknown segments")
    else:
        logger.info("escalate_node skipped: no unknown segments")

    step = transform_node(state)
    state.update(step)
    logger.info(
        "transform_node result: final_chunks=%d",
        len(state["final_chunks"]),
    )

    escalate_count = sum(
        1
        for c in state["classified_chunks"]
        if any(s.get("escalated") for s in c["segments"])
    )
    stats = {
        "chunk_count": len(state["final_chunks"]),
        "escalate_count": escalate_count,
    }
    logger.info("final doc_metadata: %s", state["doc_metadata"])
    logger.info("final stats: %s", stats)
    logger.info("first 3 chunks: %s", state["final_chunks"][:3])

    assert len(state["final_chunks"]) > 0
    assert not state["errors"]

