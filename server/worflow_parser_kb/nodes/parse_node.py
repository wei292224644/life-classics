from __future__ import annotations

import re
import time
import uuid

import structlog
from opentelemetry import trace

from observability.metrics import (
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)
from worflow_parser_kb.models import WorkflowState

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


def parse_node(state: WorkflowState) -> dict:
    _start = time.perf_counter()
    doc_id = state.get("doc_metadata", {}).get("doc_id", "")
    _logger.info("parse_node_start", node="parse_node", doc_id=doc_id, chunks_in=1)

    with _tracer.start_as_current_span("parse_node") as span:
        span.set_attribute("worflow_parser_kb.node", "parse_node")
        span.set_attribute("worflow_parser_kb.doc_id", doc_id)
        span.set_attribute("worflow_parser_kb.chunk_count.in", 1)

        meta = dict(state["doc_metadata"])
        errors = list(state.get("errors", []))

        # 若未提供 title，尝试从第一个 # 标题提取
        if not meta.get("title"):
            for line in state["md_content"].splitlines():
                if line.startswith("# "):
                    meta["title"] = line[2:].strip()
                    break

        # 若未提供 doc_id，自动生成 UUID
        if not meta.get("doc_id"):
            meta["doc_id"] = str(uuid.uuid4())

        # standard_no 缺失时，尝试从 Markdown 内容中提取
        if not meta.get("standard_no"):
            pattern = r"GB[\s_]?\d+(?:[.\d]*)?(?:\.\d+)?-\d{4}"
            match = re.search(pattern, state["md_content"])
            if match:
                meta["standard_no"] = match.group(0)
            elif meta.get("doc_id"):
                # fallback：使用 doc_id（通常为文件名去扩展名）
                meta["standard_no"] = meta["doc_id"]
            else:
                errors.append("WARNING: doc_metadata missing 'standard_no'")

        span.set_attribute("worflow_parser_kb.chunk_count.out", 1)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="parse_node").observe(duration)
    parser_chunks_processed_total.labels(node="parse_node").inc(1)
    _logger.info(
        "parse_node_done",
        node="parse_node",
        doc_id=doc_id,
        duration_ms=round(duration * 1000, 2),
        chunks_in=1,
        chunks_out=1,
    )
    return {"doc_metadata": meta, "errors": errors, "md_content": state["md_content"]}

