from __future__ import annotations

import re
import time

import structlog
from opentelemetry import trace

from observability.metrics import (
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)
from parser.models import WorkflowState

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)

# ── 清洗规则列表 ────────────────────────────────────────────────────────────────
# 每条规则为 (pattern, replacement)，按顺序依次应用。
# 新增清洗需求时在此列表追加即可，无需修改函数逻辑。
_CLEAN_RULES: list[tuple[re.Pattern, str]] = [
    # 去除 Markdown 图片引用 ![alt](url)
    (re.compile(r"!\[.*?\]\(.*?\)"), ""),
    # 去除目次/目录章节（含标题及其下全部内容，直到下一个同级顶层标题或文末）
    (re.compile(r"^# (?:目次|目录)\n[\s\S]*?(?=^# |\Z)", re.MULTILINE), ""),
    # 去除电子版免责声明行：(电子版本仅供参考，以标准正式出版物为准)
    (re.compile(r"\(电子版本仅供参考[^)]*\)"), ""),
    # 去除前言章节（含标题及其下全部内容，与目录规则结构对称）
    (re.compile(r"^# 前言\n[\s\S]*?(?=^# |\Z)", re.MULTILINE), ""),
]


def _clean_md_content(md: str) -> str:
    for pattern, replacement in _CLEAN_RULES:
        md = pattern.sub(replacement, md)
    # 清理因删除内容产生的连续空行（超过两个换行压缩为两个）
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def clean_node(state: WorkflowState) -> dict:
    _start = time.perf_counter()
    doc_id = state.get("doc_metadata", {}).get("doc_id", "")
    _logger.info("clean_node_start", node="clean_node", doc_id=doc_id, chunks_in=1)

    with _tracer.start_as_current_span("clean_node") as span:
        span.set_attribute("parser.node", "clean_node")
        span.set_attribute("parser.doc_id", doc_id)
        span.set_attribute("parser.chunk_count.in", 1)

        cleaned = _clean_md_content(state["md_content"])

        span.set_attribute("parser.chunk_count.out", 1)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="clean_node").observe(duration)
    parser_chunks_processed_total.labels(node="clean_node").inc(1)
    _logger.info(
        "clean_node_done",
        node="clean_node",
        doc_id=doc_id,
        duration_ms=round(duration * 1000, 2),
        chunks_in=1,
        chunks_out=1,
    )
    return {"md_content": cleaned}
