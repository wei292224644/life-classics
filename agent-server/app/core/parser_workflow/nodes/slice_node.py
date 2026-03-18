from __future__ import annotations

import re
from typing import List, Tuple

from app.core.parser_workflow.config import (
    CHUNK_SOFT_MAX_DEFAULT,
    CHUNK_HARD_MAX_DEFAULT,
    SLICE_HEADING_LEVELS_DEFAULT,
    get_config_value,
)
from app.core.parser_workflow.models import RawChunk, WorkflowState


def _clean_section_path_text(title: str) -> str:
    """
    将 heading 标题中常见的 LaTeX inline 语法转化为可读 Unicode，
    避免 section_path 中出现原始 LaTeX 字符串。
    仅处理 GB 标准文档中实际出现的模式，不追求完整覆盖。
    """
    # $\mathrm{X_Y}$ / $\mathrm{XY}$ → XY（下标转数字，花括号内下标）
    title = re.sub(r'\$\\mathrm\{([^}]+)\}\$', lambda m: m.group(1).replace('_', ''), title)
    # $\mathrm{X}_{Y}$ / $\mathrm{X}_Y$ → XY（下标在花括号外）
    title = re.sub(r'\$\\mathrm\{([^}]+)\}_\{?([^$}\s]+)\}?\$', lambda m: m.group(1) + m.group(2), title)
    # $\mathbf{X}$ → X
    title = re.sub(r'\$\\mathbf\{([^}]+)\}\$', r'\1', title)
    # $\lambda$ → λ
    title = title.replace(r'$\lambda$', 'λ').replace(r'$\\lambda$', 'λ')
    # 兜底：去除残余 $...$ inline LaTeX
    title = re.sub(r'\$[^$\n]{1,60}\$', '', title)
    # 清理多余空格
    title = re.sub(r' {2,}', ' ', title).strip()
    return title


def _heading_pattern(level: int) -> re.Pattern:
    prefix = "#" * level
    return re.compile(rf"^{re.escape(prefix)} (.+)$", re.MULTILINE)


def _split_by_heading(text: str, level: int) -> List[Tuple[str, str]]:
    """
    按指定级别标题切分。
    返回 [(heading_title, block_content), ...]
    - heading_title 为空字符串时表示标题前的内容（前言）
    - block_content 包含标题行本身
    """
    pattern = _heading_pattern(level)
    parts: List[Tuple[str, str]] = []
    last_end = 0
    last_title = ""

    for m in pattern.finditer(text):
        segment = text[last_end:m.start()]
        if segment.strip() or last_title == "":
            parts.append((last_title, segment))
        last_title = m.group(1).strip()
        last_end = m.start()

    parts.append((last_title, text[last_end:]))
    return parts


def _has_body_content(block: str) -> bool:
    """
    判断 block 是否有标题行以外的实质内容。
    去除所有以 # 开头的行后，检查剩余内容是否非空。
    """
    lines = block.splitlines()
    body = "\n".join(line for line in lines if not line.startswith("#"))
    return bool(body.strip())


def recursive_slice(
    content: str,
    heading_levels: List[int],
    parent_path: List[str],
    soft_max: int,
    hard_max: int,
    errors: List[str],
) -> List[RawChunk]:
    if not heading_levels:
        chunk = RawChunk(
            content=content, section_path=parent_path[:], char_count=len(content)
        )
        if len(content) > hard_max:
            errors.append(
                f"WARN: chunk exceeds HARD_MAX ({len(content)} chars) at {parent_path}"
            )
        return [chunk]

    level = heading_levels[0]
    parts = _split_by_heading(content, level)

    if len(parts) == 1 and parts[0][0] == "":
        return recursive_slice(content, heading_levels[1:], parent_path, soft_max, hard_max, errors)

    result: List[RawChunk] = []
    for title, block in parts:
        if not block.strip() and not title:
            continue
        path = parent_path + ([_clean_section_path_text(title)] if title else [])
        char_count = len(block)
        if char_count <= soft_max or len(heading_levels) <= 1:
            if _has_body_content(block):
                if len(block) > hard_max:
                    errors.append(
                        f"WARN: chunk exceeds HARD_MAX ({len(block)} chars) at {path}"
                    )
                result.append(RawChunk(content=block, section_path=path, char_count=len(block)))
        else:
            # soft_max 超限时，检查直接子节是否真的需要拆分
            # 仅检查一层（heading_levels[1]），孙节超限由下层递归处理（有意设计）
            sub_parts = _split_by_heading(block, heading_levels[1])
            # 过滤纯标题行子节，避免影响 hard_max 判断
            any_sub_exceeds_hard = any(
                len(p[1]) > hard_max for p in sub_parts if p[1].strip()
            )
            if not any_sub_exceeds_hard and char_count <= hard_max:
                # 所有直接子节均在 hard_max 以内，且整体也在 hard_max 以内，整体保留
                # 注：不需要 _has_body_content 检查——block > soft_max > 1500，不可能是纯标题行
                errors.append(f"INFO: soft_max exceeded but kept as single chunk at {path}")
                result.append(RawChunk(content=block, section_path=path, char_count=len(block)))
            else:
                result.extend(
                    recursive_slice(block, heading_levels[1:], path, soft_max, hard_max, errors)
                )
    return result


def slice_node(state: WorkflowState) -> dict:
    cfg = state.get("config", {})
    soft_max = get_config_value(cfg, "chunk_soft_max", CHUNK_SOFT_MAX_DEFAULT)
    hard_max = get_config_value(cfg, "chunk_hard_max", CHUNK_HARD_MAX_DEFAULT)
    levels = get_config_value(
        cfg, "slice_heading_levels", SLICE_HEADING_LEVELS_DEFAULT
    )

    md = state["md_content"]
    errors = list(state.get("errors", []))
    raw_chunks: List[RawChunk] = []

    # 如果文档中存在一级标题但配置未包含，则将 1 级标题提升为最高优先级。
    # 这样可以兼容 GB 标准这类以 "#" 作为章节标题的文档，避免将 "# 2 技术要求" 等错算进前言块。
    if 1 not in levels and _heading_pattern(1).search(md):
        levels = [1] + [lvl for lvl in levels if lvl != 1]

    # 前言处理：提取第一个顶级标题前的内容
    first_heading_level = levels[0]
    pattern = _heading_pattern(first_heading_level)
    first_match = pattern.search(md)
    if first_match and first_match.start() > 0:
        preamble = md[: first_match.start()].strip()
        if preamble:
            raw_chunks.append(
                RawChunk(
                    content=preamble,
                    section_path=["__preamble__"],
                    char_count=len(preamble),
                )
            )
        md = md[first_match.start():]

    raw_chunks.extend(recursive_slice(md, levels, [], soft_max, hard_max, errors))
    return {"raw_chunks": raw_chunks, "errors": errors}

