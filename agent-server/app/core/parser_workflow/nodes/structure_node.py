from __future__ import annotations

import re
import json
from typing import Optional, Tuple

from app.core.parser_workflow.models import WorkflowState
from app.core.parser_workflow.rules import RulesStore


def _extract_headings(md: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^## (.+)$", md, re.MULTILINE)]


def match_doc_type_by_rules(
    md: str, store: RulesStore
) -> Optional[Tuple[str, str]]:
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


def _infer_doc_type_with_llm(headings: list[str], existing_types: list, config: dict) -> dict:
    """调用 LLM 推断文档类型并返回新规则条目（在测试中会被 mock）。"""
    from langchain_openai import ChatOpenAI  # type: ignore[import]

    existing_ids = "\n".join(f"- {t['id']}: {t['description']}" for t in existing_types)
    headings_str = "\n".join(headings)
    prompt = (
        "你是一个 JSON（json）结构生成助手。\n"
        "以下是一份国家标准文档的章节标题列表，请推断其文档类型。\n"
        "只返回一个 JSON 对象，不要包含任何多余说明。\n"
        '推荐字段：{\"id\": \"...\",\"description\": \"...\",\"detect_keywords\": [],\"detect_heading_patterns\": []}\n\n'
        f"现有类型：\n{existing_ids}\n\n"
        f"章节标题：\n{headings_str}\n\n"
        "若与现有类型不符，请定义新的文档类型，提供 id（英文下划线）、描述、"
        "detect_keywords（用于将来规则匹配的关键词）、detect_heading_patterns（标题模式）。"
    )

    chat = ChatOpenAI(
        model=config.get("doc_type_llm_model", "gpt-4o-mini"),
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    )
    resp = chat.invoke(prompt)
    text = getattr(resp, "content", str(resp))

    try:
        data = json.loads(text)
    except Exception as e:  # pragma: no cover - 仅用于真实 LLM 调试
        raise ValueError(f"doc_type LLM 输出非 JSON：{text}") from e

    if not isinstance(data, dict):
        raise ValueError(f"doc_type LLM JSON 结构不符合预期：{data!r}")

    data.setdefault("id", "unknown_type")
    data.setdefault("description", "")
    data.setdefault("detect_keywords", [])
    data.setdefault("detect_heading_patterns", [])
    data["source"] = "llm"
    return data


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
        new_rule = _infer_doc_type_with_llm(headings, existing_types, state.get("config", {}))
        store.append_doc_type(new_rule)
        meta["doc_type"] = new_rule["id"]
        meta["doc_type_source"] = "llm"

    return {"doc_metadata": meta, "errors": errors}

