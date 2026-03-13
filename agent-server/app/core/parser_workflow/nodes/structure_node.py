from __future__ import annotations

import re
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
    from typing import List as TList

    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel

    class DocTypeOutput(BaseModel):
        id: str
        description: str
        detect_keywords: TList[str]
        detect_heading_patterns: TList[str]

    existing_ids = "\n".join(f"- {t['id']}: {t['description']}" for t in existing_types)
    headings_str = "\n".join(headings)
    prompt = (
        "以下是一份国家标准文档的章节标题列表，请推断其文档类型。\\n\\n"
        f"现有类型：\\n{existing_ids}\\n\\n"
        f"章节标题：\\n{headings_str}\\n\\n"
        "若与现有类型不符，请定义新的文档类型，提供 id（英文下划线）、描述、"
        "detect_keywords（用于将来规则匹配的关键词）、detect_heading_patterns（标题模式）。"
    )

    model = ChatOpenAI(
        model=config.get("doc_type_llm_model", "gpt-4o-mini"),
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    ).with_structured_output(DocTypeOutput)

    result: DocTypeOutput = model.invoke(prompt)
    data = result.model_dump()
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

