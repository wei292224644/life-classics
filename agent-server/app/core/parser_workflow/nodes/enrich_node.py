from __future__ import annotations

import re
from typing import Dict, List

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)

# 匹配表格标题行，如 "表1 xxx"、"表A.1 xxx"、"表 1 xxx"
# 规范化后 key 去除 "表" 后的空格：表 1 → 表1
_TABLE_TITLE_PATTERN = re.compile(
    r'(?:^|\n)表\s*([\dA-Z]+(?:\.\d+)*)\s+\S',
    re.UNICODE,
)

# 匹配表格引用，如 "见表1"、"参见表A.1"、"条件见表 B.1"
_TABLE_REF_PATTERN = re.compile(
    r'(?:见|参见|参照|应符合|符合|按照?|不[应得]超过|不[应得]低于)'
    r'[^\n，。；]*?表\s*([\dA-Z]+(?:\.\d+)*)',
    re.UNICODE,
)

# 匹配其他引用（图/附录/章节），只记录不内联
_OTHER_REF_PATTERN = re.compile(
    r'(?:见|参见|参照|按照?)\s*((?:图|附录)[^\s，。；]{0,15}'
    r'|第?\s*\d+[\.\d]*\s*[节章条]'
    r'|\d+\.\d+[\.\d]*)',
    re.UNICODE,
)

# 匹配修改单条目标题，如 "### 一、1 范围"、"### 二、2.3 微生物指标"
_AMENDMENT_REF_PATTERN = re.compile(
    r'###\s+[一二三四五六七八九十]+、\s*(\d+(?:\.\d+)*)\s*',
    re.UNICODE,
)


def _filter_table_refs(refs: List[str]) -> List[str]:
    """
    后验过滤：对召回的表格引用标签做二次验证。
    当前直接透传；后期如需排除误报可在此添加规则。

    TODO: 如召回率提高后误报增多，在此添加过滤逻辑，
          例如排除标题行自身（如"表1 感官要求"行首）、
          排除特定 section_path 下的引用等。
          主要误报源：含"表"字的非引用词，如"征求意见表"。
    """
    return refs


def _normalize_label(raw: str) -> str:
    """将标签规范化：去除空格和全角空格，如'A.1' → 'A.1'"""
    return raw.replace(" ", "").replace("\u3000", "")


def build_table_label_index(raw_chunks: List[RawChunk]) -> Dict[str, str]:
    """
    扫描所有 raw_chunks 的完整内容，查找表格标题行，建立 {标准化标签: chunk内容} 索引。
    如 "表1 样品浓缩条件" → {"表1": <chunk content>}
    """
    index: Dict[str, str] = {}
    for rc in raw_chunks:
        for m in _TABLE_TITLE_PATTERN.finditer(rc["content"]):
            label = "表" + _normalize_label(m.group(1))
            index[label] = rc["content"]
    return index


def extract_table_refs(text: str) -> List[str]:
    """
    从文本中提取表格引用标识符列表（已规范化），如 ["表1", "表A.1"]。
    匹配 "见表X"、"参见表X"、"参照表X"、"应符合表X"、"符合表X"、
    "按表X"、"按照表X"、"不[应得]超过表X"、"不[应得]低于表X" 等形式。
    结果经 _filter_table_refs 后验过滤后返回。
    """
    raw = ["表" + _normalize_label(m.group(1)) for m in _TABLE_REF_PATTERN.finditer(text)]
    return _filter_table_refs(raw)


def extract_amendment_refs(text: str) -> List[str]:
    """
    从修改单条目中提取被修改的章节编号。
    如 "### 一、1 范围" → ["1"]
       "### 二、2.3 微生物指标" → ["2.3"]
    """
    return [m.group(1) for m in _AMENDMENT_REF_PATTERN.finditer(text)]


def extract_other_refs(text: str) -> List[str]:
    """
    从文本中提取非表格引用（图/附录/章节），只记录不内联。
    返回原始匹配字符串列表。
    """
    results = []
    for m in _OTHER_REF_PATTERN.finditer(text):
        ref = m.group(1).strip()
        # 排除纯表格引用（TABLE_REF_PATTERN 已覆盖）
        if not ref.startswith("表"):
            results.append(ref)
    return results


def resolve_table_ref(
    label: str,
    label_index: Dict[str, str],
    classified_chunks: List[ClassifiedChunk],
) -> str | None:
    """
    双重匹配：先查正则标签索引，再查 classified_chunks 中 table 段的 section_path。
    找到返回该 raw_chunk 的内容字符串，未找到返回 None。
    """
    # Step 1: 正则标签索引
    if label in label_index:
        return label_index[label]

    # Step 2: section_path 模糊匹配
    label_norm = _normalize_label(label)
    for cc in classified_chunks:
        # 只检查含 table 结构类型的 chunk
        if not any(seg.get("structure_type", seg.get("content_type")) == "table" for seg in cc["segments"]):
            continue
        raw = cc["raw_chunk"]
        for path_seg in raw["section_path"]:
            if label_norm in _normalize_label(path_seg):
                return raw["content"]

    return None


def enrich_node(state: WorkflowState) -> dict:
    """
    扫描所有 classified_chunks 中的 TypedSegment，识别交叉引用：
    - 表格引用（见表X）：双重匹配后将内容写入 ref_context
    - 其他引用（图/附录/章节）：只记录到 cross_refs
    未解析的表格引用追加到 errors（不中断流程）。
    """
    raw_chunks: List[RawChunk] = state["raw_chunks"]
    classified_chunks: List[ClassifiedChunk] = [dict(cc) for cc in state["classified_chunks"]]
    existing_errors: List[str] = list(state.get("errors", []))
    new_errors: List[str] = []

    # Step 1: 建表格标签索引
    label_index = build_table_label_index(raw_chunks)

    # Step 2: 逐段处理
    updated_chunks: List[ClassifiedChunk] = []
    for cc in classified_chunks:
        new_segments: List[TypedSegment] = []
        for seg in cc["segments"]:
            text = seg["content"]

            # 提取引用
            table_refs = extract_table_refs(text)
            other_refs = extract_other_refs(text)
            all_refs = list(dict.fromkeys(table_refs + other_refs))  # 去重保序

            # 修改单专用：提取被修改的章节编号写入 cross_refs
            if seg.get("semantic_type") == "amendment":
                amendment_refs = extract_amendment_refs(text)
                all_refs = list(dict.fromkeys(all_refs + amendment_refs))

            # 解析表格引用
            resolved_parts: List[str] = []
            failed_labels: List[str] = []
            for label in table_refs:
                content = resolve_table_ref(label, label_index, classified_chunks)
                if content is not None:
                    resolved_parts.append(content)
                else:
                    failed_labels.append(label)
                    new_errors.append(
                        f"WARN: unresolved cross_ref \"{label}\" "
                        f"in section_path {cc['raw_chunk']['section_path']} "
                        f"— no matching raw_chunk found"
                    )

            new_segments.append(TypedSegment(
                content=seg["content"],
                structure_type=seg.get("structure_type", seg.get("content_type", "")),
                semantic_type=seg.get("semantic_type", ""),
                transform_params=seg["transform_params"],
                confidence=seg["confidence"],
                escalated=seg["escalated"],
                cross_refs=all_refs,
                ref_context="\n\n".join(resolved_parts),
                failed_table_refs=failed_labels,
            ))

        updated_chunks.append(ClassifiedChunk(
            raw_chunk=cc["raw_chunk"],
            segments=new_segments,
            has_unknown=cc["has_unknown"],
        ))

    return {
        "classified_chunks": updated_chunks,
        "errors": existing_errors + new_errors,
    }
