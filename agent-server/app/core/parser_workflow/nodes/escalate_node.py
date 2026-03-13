from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from app.core.parser_workflow.models import ClassifiedChunk, TypedSegment, WorkflowState
from app.core.parser_workflow.rules import RulesStore


def _call_escalate_llm(
    segment_content: str,
    existing_types: List[Dict],
    config: dict,
) -> Dict[str, Any]:
    """
    大模型两步判断：
    1. 语义匹配：unknown 片段是否符合已有 content_type？
       → action="use_existing", content_type=<existing_id>
    2. 不符合则创建新类型（含 strategy + prompt_template）
       → action="create_new", content_type=<new_id>, description=..., transform={...}
    """
    from langchain_openai import ChatOpenAI  # type: ignore[import]
    from pydantic import BaseModel

    class TransformParams(BaseModel):
        strategy: str
        prompt_template: Optional[str] = None

    class EscalateOutput(BaseModel):
        action: Literal["use_existing", "create_new"]
        content_type: str
        description: Optional[str] = None
        transform: Optional[TransformParams] = None

    type_list = "\n".join(f"- {t['id']}: {t['description']}" for t in existing_types)
    prompt = (
        "以下文本片段置信度过低，无法被自动分类。\n\n"
        f"现有内容类型：\n{type_list}\n\n"
        f"文本内容：\n{segment_content}\n\n"
        "请先判断该文本是否语义上符合某个已有类型（action=use_existing）。"
        "若符合，返回对应 content_type id 即可。\n"
        "若不符合任何已有类型，请创建新类型（action=create_new），提供：\n"
        "- content_type：英文下划线命名的新 id\n"
        "- description：类型说明\n"
        "- transform.strategy：转化策略\n"
        "- transform.prompt_template：转化提示词\n"
    )

    model = ChatOpenAI(
        model=config.get("escalate_model", "gpt-4o"),  # type: ignore[arg-type]
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    ).with_structured_output(EscalateOutput)

    result: EscalateOutput = model.invoke(prompt)
    return result.model_dump()


def escalate_node(state: WorkflowState) -> dict:
    store = RulesStore(state["rules_dir"])
    config = state.get("config", {})
    classified_chunks: List[ClassifiedChunk] = [dict(c) for c in state["classified_chunks"]]

    for i, cc in enumerate(classified_chunks):
        if not cc["has_unknown"]:
            continue

        existing_types = store.get_content_type_rules().get("content_types", [])
        new_segments = list(cc["segments"])

        for j, seg in enumerate(new_segments):
            if seg["content_type"] != "unknown":
                continue

            llm_result = _call_escalate_llm(seg["content"], existing_types, config)
            new_ct_id = llm_result["content_type"]

            if llm_result["action"] == "create_new":
                known_ids = {t["id"] for t in existing_types}
                if new_ct_id not in known_ids:
                    transform = llm_result.get("transform") or {}
                    store.append_content_type(
                        {
                            "id": new_ct_id,
                            "description": llm_result.get("description", ""),
                            "transform": transform,
                        }
                    )
                    existing_types = store.get_content_type_rules().get("content_types", [])

            transform_params = store.get_transform_params(new_ct_id)
            new_segments[j] = TypedSegment(
                content=seg["content"],
                content_type=new_ct_id,
                transform_params=transform_params,
                confidence=1.0,
                escalated=True,
            )

        classified_chunks[i] = ClassifiedChunk(
            raw_chunk=cc["raw_chunk"],
            segments=new_segments,
            has_unknown=False,
        )

    return {"classified_chunks": classified_chunks}

