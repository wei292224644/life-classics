from __future__ import annotations

import time
from typing import Dict, List

import structlog

from parser.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from parser.post_classify_hooks import POST_CLASSIFY_HOOKS
from parser.rules import RulesStore
from config import settings
from parser.structured_llm import invoke_structured
from parser.nodes.output import ClassifyOutput, SegmentItem
from observability.metrics import (
    llm_calls_total,
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)

_logger = structlog.get_logger(__name__)


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

分类规则（按优先级从高到低）：

【强制规则，这些情况下必须合并且不得拆分】
1. 公式块：文本中出现 $$...$$ 公式时，公式及其前导引导句（如"按下式计算："）、变量说明（"式中：X——..."格式）、注释（"注："格式）必须合并为同一个 segment，structure_type=formula，semantic_type=calculation。
2. 步骤链：编号呈递进的相邻步骤（如 A.2.2.1 → A.2.2.2，或 3.1 → 3.2），且后一步引用前一步产物（如"取上一步溶液"、"将前述沉淀..."、"按 A.X.X.1 方法..."），必须合并为单一 procedure segment。
3. 标题行不得单独成段：章节标题（如 ## A.2、### A.2.2）必须与其后的首个内容片段合并；纯标题无内容时则保留。

【切分原则】
4. 极保守切分：只有在以下情况才切分——相邻内容属于截然不同的 semantic_type（如 limit → procedure，或 material → procedure），且各自内容足够独立。满足以下任一条件时禁止切分：同一检测方法的 试剂/步骤/仪器/结果计算、连续步骤之间存在数据或引用传递、"见第X条"等内部引用。
5. 双维度先推断结构再推断用途：structure_type 决定内容呈现形式，semantic_type 决定读者用途，两者非独立——formula 必然是 calculation，header 仅用于 metadata，procedure 可包含 limit 注释（如"注：..."）。
6. confidence 反映综合把握程度（0-1），低于阈值（0.7）的 segment 会进入人工审核。

【输出 content 字段的 LaTeX 处理规则】
在每个 segment 的 content 字段中，将内联 LaTeX（$...$）转化为可读文本，不得在输出中保留任何 LaTeX 语法：
- 数值与单位：$4\\mathrm{{g}}$ → 4 g，$200~\\mathrm{{mL}}$ → 200 mL，$80^{{\\circ}}C$ → 80°C，$15\\mathrm{{min}}$ → 15 min，$1000\\mathrm{{r/min}}$ → 1000 r/min
- 分数/比例：$85 + 15$ → 85+15（保留运算符）
- 希腊字母：$\\lambda$ → λ，$\\alpha$ → α
- 百分比：$0.2\\%$ → 0.2%
- 范围：$1000\\mathrm{{cm}}^{{-1}}\\sim 1100\\mathrm{{cm}}^{{-1}}$ → 1000 cm⁻¹～1100 cm⁻¹
- 块公式（$$...$$）保留原始 LaTeX 不转换（由后续步骤处理）

文本内容：
{_escape_for_json_prompt(chunk_content)}
"""
    result = invoke_structured(
        node_name="classify_node",
        prompt=prompt,
        response_model=ClassifyOutput,
        extra_body={"enable_thinking": False, "reasoning_split": True},
        max_tokens=15000,
    )
    return result.segments


def _escape_for_json_prompt(text: str) -> str:
    """转义文本中的 ASCII 双引号，防止 LLM 生成 JSON 时字符串值被提前截断。"""
    return text.replace('"', '\\"')


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
    llm_calls_total.labels(node="classify_node", model=settings.CLASSIFY_MODEL).inc()

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

    for hook in POST_CLASSIFY_HOOKS:
        segments = hook(segments)

    return ClassifiedChunk(
        raw_chunk=raw_chunk,
        segments=segments,
        has_unknown=has_unknown,
    )


def classify_node(state: WorkflowState) -> dict:
    chunk_count = len(state["raw_chunks"])
    _start = time.perf_counter()
    _logger.info("classify_node_start", chunk_count=chunk_count)

    store = RulesStore(state["rules_dir"])
    classified: List[ClassifiedChunk] = [
        classify_raw_chunk(chunk, store) for chunk in state["raw_chunks"]
    ]

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="classify_node").observe(duration)
    parser_chunks_processed_total.labels(node="classify_node").inc(chunk_count)
    _logger.info(
        "classify_node_done",
        chunk_count=chunk_count,
        duration_ms=round(duration * 1000, 2),
        model=settings.CLASSIFY_MODEL,
    )
    return {"classified_chunks": classified}
