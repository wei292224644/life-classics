from __future__ import annotations

from typing import Dict, List

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.rules import RulesStore
from app.core.config import settings
from app.core.parser_workflow.structured_llm import invoke_structured
from app.core.parser_workflow.nodes.output import ClassifyOutput, SegmentItem


def _build_type_desc(types: List[Dict]) -> str:
    lines = []
    for t in types:
        lines.append(f"- {t['id']}: {t['description']}")
        if t.get("examples"):
            examples_str = " / ".join(t["examples"])
            lines.append(f"  示例：{examples_str}")
    return "\n".join(lines)


def _call_classify_llm(
    chunk_content: str,
    structure_types: List[Dict],
    semantic_types: List[Dict],
) -> List[SegmentItem]:
    """
    调用小模型对 chunk 做分段 + 双维度分类（单次调用，prompt 内两步推断）。
    """
    structure_desc = "\n".join(
        f"- {t['id']}: {t['description']}" for t in structure_types
    )
    semantic_desc = _build_type_desc(semantic_types)
    prompt = f"""请将以下文本拆分为语义独立的片段，并对每个片段进行双维度分类。

【结构类型（structure_type）】——描述内容的呈现形式：
{structure_desc}

【语义类型（semantic_type）】——描述内容对读者的用途：
{semantic_desc}

分类规则：
1. 保守切分：只在相邻内容属于明显不同语义单元时才切分；同一逻辑章节保持整体。
2. 对每个片段独立推断两个维度，互不干扰：先判断呈现形式（structure_type），再判断用途（semantic_type）。
3. confidence 反映你对两个判断综合的把握程度（0-1）。
4. 公式识别（强制规则）：文本中出现 $$...$$ 块级公式时，该部分及其紧邻的变量说明（"式中：m1——..."格式）必须作为独立 segment，structure_type=formula，semantic_type=calculation。不得因上下文中存在大量列表或段落而将含公式的内容归为 plain_text。

文本内容：
{_escape_for_json_prompt(chunk_content)}
"""
    result = invoke_structured(
        node_name="classify_node",
        prompt=prompt,
        response_model=ClassifyOutput,
        extra_body={"enable_thinking": False},
        max_tokens=15000,
    )
    return result.segments


def _escape_for_json_prompt(text: str) -> str:
    """转义文本中的 ASCII 双引号，防止 LLM 生成 JSON 时字符串值被提前截断。"""
    return text.replace('"', '\\"')


_MERGE_SHORT_THRESHOLD = 60


def _merge_short_segments(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将相邻且 semantic_type 相同的短 segment 合并，避免生成无独立检索价值的碎片 chunk。

    左向扫描：若当前 segment 长度 < 阈值，且与前一个 segment 的 semantic_type 相同，
    则并入前一个。单次 O(n) 扫描即可处理任意长度的连续短 segment 链。
    """
    result: List[TypedSegment] = []
    for seg in segments:
        if (
            result
            and result[-1]["semantic_type"] == seg["semantic_type"]
            and len(seg["content"]) < _MERGE_SHORT_THRESHOLD
        ):
            result[-1] = TypedSegment(
                **{
                    **result[-1],
                    "content": result[-1]["content"] + "\n\n" + seg["content"],
                }
            )
        else:
            result.append(seg)
    return result


def _merge_formula_with_variables(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将 formula segment 与其后紧邻的变量说明 segment 合并为一个。

    GB 标准中公式块（$$...$$）和变量说明（式中：...）是同一语义单元，
    但 LLM 有时会将两者切分为相邻的两个 segment。此函数在分类后做确定性修正。
    """
    merged = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if (
            seg["structure_type"] == "formula"
            and i + 1 < len(segments)
            and segments[i + 1]["semantic_type"] == "calculation"
            and segments[i + 1]["content"].lstrip().startswith("式中")
        ):
            next_seg = segments[i + 1]
            merged.append(
                TypedSegment(
                    **{
                        **seg,
                        "content": seg["content"] + "\n\n" + next_seg["content"],
                    }
                )
            )
            i += 2
        else:
            merged.append(seg)
            i += 1
    return merged


def classify_raw_chunk(
    raw_chunk: RawChunk,
    store: RulesStore,
) -> ClassifiedChunk:
    threshold = store.get_confidence_threshold(settings.CONFIDENCE_THRESHOLD)
    ct_rules = store.get_content_type_rules()
    structure_types = ct_rules.get("structure_types", [])
    semantic_types = ct_rules.get("semantic_types", [])

    llm_output = _call_classify_llm(
        raw_chunk["content"], structure_types, semantic_types
    )

    segments: List[TypedSegment] = []
    has_unknown = False
    for item in llm_output:
        confidence = item.confidence
        if confidence < threshold:
            seg = TypedSegment(
                content=item.content,
                structure_type="unknown",
                semantic_type="unknown",
                transform_params={
                    "strategy": "plain_embed",
                    "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
                },
                confidence=confidence,
                escalated=False,
                cross_refs=[],
                ref_context="",
                failed_table_refs=[],
            )
            has_unknown = True
        else:
            transform_params = store.get_transform_params(item.semantic_type)
            seg = TypedSegment(
                content=item.content,
                structure_type=item.structure_type,
                semantic_type=item.semantic_type,
                transform_params=transform_params,
                confidence=confidence,
                escalated=False,
                cross_refs=[],
                ref_context="",
                failed_table_refs=[],
            )
        segments.append(seg)

    segments = _merge_formula_with_variables(segments)
    segments = _merge_short_segments(segments)

    return ClassifiedChunk(
        raw_chunk=raw_chunk,
        segments=segments,
        has_unknown=has_unknown,
    )


def classify_node(state: WorkflowState) -> dict:
    store = RulesStore(state["rules_dir"])
    classified: List[ClassifiedChunk] = [
        classify_raw_chunk(chunk, store) for chunk in state["raw_chunks"]
    ]
    return {"classified_chunks": classified}
