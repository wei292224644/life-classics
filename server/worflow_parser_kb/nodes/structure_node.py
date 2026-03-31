from __future__ import annotations

import asyncio
import re
import time

import structlog
from opentelemetry import trace

from config import settings
from observability.metrics import (
    llm_calls_total,
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)
from worflow_parser_kb.models import WorkflowState
from worflow_parser_kb.nodes.output import DocTypeOutput
from worflow_parser_kb.rules import RulesStore
from worflow_parser_kb.structured_llm import invoke_structured

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


def _extract_headings(md: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^#{1,2} (.+)$", md, re.MULTILINE)]


def match_doc_type_by_rules(md: str, store: RulesStore) -> tuple[str, str] | None:
    """按规则匹配文档类型。命中返回 (doc_type_id, "rule")，否则返回 None。"""
    rules = store.get_doc_type_rules()
    threshold = rules.get("match_threshold", 2)
    headings = _extract_headings(md)

    best_id = None
    best_score = 0
    for dt in rules.get("doc_types", []):
        score = 0
        for kw in dt.get("detect_keywords", []):
            if kw in md:
                score += 1
        for hp in dt.get("detect_heading_patterns", []):
            if any(hp in h for h in headings):
                score += 1
        if score >= threshold and score > best_score:
            best_score = score
            best_id = dt["id"]

    if best_id:
        return best_id, "rule"
    return None


def _infer_doc_type_with_llm(
    headings: list[str], existing_types: list, config: dict  # config 预留，暂未使用
) -> dict:
    """调用 LLM 推断文档类型并返回新规则条目（在测试中会被 mock）。"""
    existing_ids = "\n".join(f"- {t['id']}: {t['description']}" for t in existing_types)
    headings_str = "\n".join(headings)
    sample_doc_type = """{
    "id": "...",
    "description": "...",
    "detect_keywords": [],
    "detect_heading_patterns": []
}"""
    prompt = f"""
    以下是一份国家标准文档的章节标题列表，请推断其文档类型。
    只返回一个 JSON 对象，不要包含任何多余说明。
    现有类型：
    {existing_ids}
    
    如果推断的文档类型不在现有类型中，也请返回一个 JSON 对象，不要包含任何多余说明。
    id 设置为你认为最合适的 id，description 设置为你认为最合适的描述，detect_keywords 和 detect_heading_patterns 设置为你认为最合适的检测关键词和检测章节标题模式。
    
    章节标题：
    {headings_str}
    
    返回格式（json）：
    {sample_doc_type}
    """

    print(prompt)
    resp = invoke_structured(
        node_name="structure_node",
        prompt=prompt,
        response_model=DocTypeOutput,
        extra_body={"enable_thinking": False, "reasoning_split": True},
    )
    print(resp)
    llm_calls_total.labels(
        node="structure_node", model=settings.DOC_TYPE_LLM_MODEL or "unknown"
    ).inc()
    return resp.model_dump()


async def structure_node(state: WorkflowState) -> dict:
    _start = time.perf_counter()
    doc_id = state.get("doc_metadata", {}).get("doc_id", "")
    _logger.info(
        "structure_node_start", node="structure_node", doc_id=doc_id, chunks_in=1
    )

    with _tracer.start_as_current_span("structure_node") as span:
        span.set_attribute("worflow_parser_kb.node", "structure_node")
        span.set_attribute("worflow_parser_kb.doc_id", doc_id)
        span.set_attribute("worflow_parser_kb.chunk_count.in", 1)

        meta = dict(state["doc_metadata"])
        errors = list(state.get("errors", []))
        store = RulesStore(state["rules_dir"])

        match = match_doc_type_by_rules(state["md_content"], store)
        if match:
            meta["doc_type"], meta["doc_type_source"] = match
        else:
            semaphore = asyncio.Semaphore(settings.STRUCTURE_MAX_CONCURRENCY)

            async def limited_infer():
                async with semaphore:
                    headings = _extract_headings(state["md_content"])
                    existing_types = store.get_doc_type_rules().get("doc_types", [])
                    return await asyncio.to_thread(
                        _infer_doc_type_with_llm,
                        headings,
                        existing_types,
                        state.get("config", {}),
                    )

            new_rule = await limited_infer()
            store.append_doc_type(new_rule)
            meta["doc_type"] = new_rule["id"]
            meta["doc_type_source"] = "llm"

        span.set_attribute("worflow_parser_kb.chunk_count.out", 1)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="structure_node").observe(duration)
    parser_chunks_processed_total.labels(node="structure_node").inc(1)
    _logger.info(
        "structure_node_done",
        node="structure_node",
        doc_id=doc_id,
        duration_ms=round(duration * 1000, 2),
        chunks_in=1,
        chunks_out=1,
    )
    return {"doc_metadata": meta, "errors": errors}
