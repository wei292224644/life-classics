from __future__ import annotations

import re

from parser.models import WorkflowState

# ── 清洗规则列表 ────────────────────────────────────────────────────────────────
# 每条规则为 (pattern, replacement)，按顺序依次应用。
# 新增清洗需求时在此列表追加即可，无需修改函数逻辑。
_CLEAN_RULES: list[tuple[re.Pattern, str]] = [
    # 去除 Markdown 图片引用 ![alt](url)
    (re.compile(r"!\[.*?\]\(.*?\)"), ""),
    # 去除目次/目录章节（含标题及其下全部内容，直到下一个同级顶层标题或文末）
    (re.compile(r"^# (?:目次|目录)\n[\s\S]*?(?=^# |\Z)", re.MULTILINE), ""),
    # 去除电子版免责声明行：(电子版本仅供参考，以标准正式出版物为准)
    (re.compile(r"\(电子版本仅供参考[^)]*\)"), ""),
    # 去除前言章节（含标题及其下全部内容，与目录规则结构对称）
    (re.compile(r"^# 前言\n[\s\S]*?(?=^# |\Z)", re.MULTILINE), ""),
]


def _clean_md_content(md: str) -> str:
    for pattern, replacement in _CLEAN_RULES:
        md = pattern.sub(replacement, md)
    # 清理因删除内容产生的连续空行（超过两个换行压缩为两个）
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def clean_node(state: WorkflowState) -> dict:
    """
    对 md_content 做纯文本清洗，去除对后续流水线无价值的内容。
    当前规则：
      - 去除 Markdown 图片引用（示意图、色谱图等不携带可检索信息）
      - 去除目次/目录章节（页码索引，对检索无价值）
    在此节点扩展新规则，不影响其他节点。
    """
    cleaned = _clean_md_content(state["md_content"])
    return {"md_content": cleaned}
