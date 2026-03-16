from __future__ import annotations

from typing import List
import re
import json
from typing import Optional, Tuple
from pathlib import Path

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.parser_workflow.models import WorkflowState
from app.core.parser_workflow.rules import RulesStore

from app.core.parser_workflow.nodes.output import DocTypeOutput


chat = ChatOpenAI(
    model=settings.DOC_TYPE_LLM_MODEL,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL or None,
    extra_body={"enable_thinking": False},  # 关闭思考模式，避免影响 structured output
).with_structured_output(DocTypeOutput)


def _extract_headings(md: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^## (.+)$", md, re.MULTILINE)]


def match_doc_type_by_rules(md: str, store: RulesStore) -> Optional[Tuple[str, str]]:
    """按规则匹配文档类型。命中返回 (doc_type_id, \"rule\")，否则返回 None。"""
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
    headings: list[str], existing_types: list, config: dict
) -> dict:
    """调用 LLM 推断文档类型并返回新规则条目（在测试中会被 mock）。"""
    from langchain_openai import ChatOpenAI  # type: ignore[import]

    existing_ids = "\n".join(f"- {t['id']}: {t['description']}" for t in existing_types)
    headings_str = "\n".join(headings)
    sample_doc_type = """{
    "id": "...",
    "description": "...",
    "detect_keywords": [],
    "detect_heading_patterns": [],
}"""
    prompt = f"""
    以下是一份国家标准文档的章节标题列表，请推断其文档类型。
    只返回一个 JSON 对象，不要包含任何多余说明。
    现有类型：
    {existing_ids}
    章节标题：
    {headings_str}
    返回格式（json）：
    {sample_doc_type}
    """

    resp = chat.invoke(prompt)
    return resp.model_dump()


def structure_node(state: WorkflowState) -> dict:
    meta = dict(state["doc_metadata"])
    errors = list(state.get("errors", []))
    store = RulesStore(state["rules_dir"])

    match = match_doc_type_by_rules(state["md_content"], store)
    if match:
        meta["doc_type"], meta["doc_type_source"] = match
    else:
        headings = _extract_headings(state["md_content"])
        existing_types = store.get_doc_type_rules().get("doc_types", [])
        new_rule = _infer_doc_type_with_llm(
            headings, existing_types, state.get("config", {})
        )
        store.append_doc_type(new_rule)
        meta["doc_type"] = new_rule["id"]
        meta["doc_type_source"] = "llm"

    return {"doc_metadata": meta, "errors": errors}
