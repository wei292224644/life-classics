"""Post-classify segment merge hooks.

每个 hook 是一个纯函数，签名为：
    (list[TypedSegment]) -> list[TypedSegment]

在 classify_raw_chunk() 完成 LLM 分类后，按 POST_CLASSIFY_HOOKS 的顺序
依次执行，对 segments 做确定性修正。

添加新 hook：
  1. 在本文件末尾定义函数，写清触发条件和合并逻辑
  2. 将函数名追加到 POST_CLASSIFY_HOOKS 列表（注意顺序）
"""

from __future__ import annotations

from typing import Callable, List

from workflow_parser_kb.models import TypedSegment

PostClassifyHook = Callable[[List[TypedSegment]], List[TypedSegment]]


def merge_formula_preamble(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将计算导言段落与其后紧邻的公式 segment 合并。

    触发条件（同时满足）：
    - 当前 segment：structure_type=paragraph, semantic_type=calculation
    - 下一 segment：structure_type=formula,   semantic_type=calculation

    GB 标准中"按下式计算："这类导言句和公式体是同一语义单元，
    LLM 有时会将两者切分为相邻的两个 segment。
    合并后 structure_type 取 formula，保留计算类语义。
    """
    result: List[TypedSegment] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if (
            seg["structure_type"] == "paragraph"
            and seg["semantic_type"] == "calculation"
            and i + 1 < len(segments)
            and segments[i + 1]["structure_type"] == "formula"
            and segments[i + 1]["semantic_type"] == "calculation"
        ):
            next_seg = segments[i + 1]
            result.append(
                TypedSegment(
                    **{
                        **next_seg,  # formula segment 的 transform_params 为主
                        "content": seg["content"] + "\n\n" + next_seg["content"],
                    }
                )
            )
            i += 2
        else:
            result.append(seg)
            i += 1
    return result


def merge_formula_with_variables(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将 formula segment 与其后紧邻的变量说明 segment 合并。

    触发条件（同时满足）：
    - 当前 segment：structure_type=formula
    - 下一 segment：semantic_type=calculation，content 以"式中"开头

    GB 标准中公式块（$$...$$）和变量说明（式中：m1——...）是同一语义单元，
    但 LLM 有时会将两者切分为相邻的两个 segment。
    """
    result: List[TypedSegment] = []
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
            result.append(
                TypedSegment(
                    **{
                        **seg,
                        "content": seg["content"] + "\n\n" + next_seg["content"],
                    }
                )
            )
            i += 2
        else:
            result.append(seg)
            i += 1
    return result


def merge_procedure_list(segments: List[TypedSegment]) -> List[TypedSegment]:
    """将步骤介绍段落与其后紧邻的步骤列表 segment 合并。

    触发条件（同时满足）：
    - 当前 segment：structure_type=paragraph, semantic_type=procedure
    - 下一 segment：structure_type=list,      semantic_type=procedure

    GB 标准中"取适量...混合均匀。"这类总说明句和其后的——列表项
    是同一步骤的整体，LLM 有时将两者分为相邻 segment。
    合并后 structure_type 取 list（列表项更具体，检索价值更高）。
    """
    result: List[TypedSegment] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if (
            seg["structure_type"] == "paragraph"
            and seg["semantic_type"] == "procedure"
            and i + 1 < len(segments)
            and segments[i + 1]["structure_type"] == "list"
            and segments[i + 1]["semantic_type"] == "procedure"
        ):
            next_seg = segments[i + 1]
            result.append(
                TypedSegment(
                    **{
                        **next_seg,  # list segment 的 transform_params 为主
                        "content": seg["content"] + "\n\n" + next_seg["content"],
                    }
                )
            )
            i += 2
        else:
            result.append(seg)
            i += 1
    return result


_MERGE_SHORT_THRESHOLD = 60


def merge_short_segments(segments: List[TypedSegment]) -> List[TypedSegment]:
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


# Hook 注册表 —— 顺序执行，先合并结构性单元，最后处理碎片
POST_CLASSIFY_HOOKS: List[PostClassifyHook] = [
    merge_formula_preamble,        # 1. 导言+公式合并（避免产生孤立导言碎片）
    merge_formula_with_variables,  # 2. 公式+变量说明合并
    merge_procedure_list,          # 3. 步骤说明+步骤列表合并
    merge_short_segments,          # 4. 最后清理剩余短碎片
]
