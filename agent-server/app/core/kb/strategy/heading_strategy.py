"""
标题切分策略：从 Markdown 字符串按标题粗粒度切分为 DocumentChunk。
"""

import re
from typing import List, Optional

from app.core.document_chunk import DocumentChunk, ContentType


def split_heading(documents: List[DocumentChunk], **kwargs) -> List[DocumentChunk]:
    """
    标题切分策略（接收已有 DocumentChunk 列表，暂不二次切分）。

    Args:
        documents: 待切分的文档列表
        **kwargs: 其他参数

    Returns:
        切分后的知识库通用数据结构列表
    """
    return documents


def split_heading_from_markdown(
    markdown_content: str,
    doc_id: str,
    doc_title: str,
    source: str,
    markdown_id: Optional[str] = None,
) -> List[DocumentChunk]:
    """
    按 Markdown 标题（^#{1,6}\\s+.+）粗粒度切分，每个「当前标题到下一同级或更高级标题之前」为一块。

    Args:
        markdown_content: 整份 Markdown 字符串
        doc_id: 文档 ID
        doc_title: 文档标题
        source: 来源标识（如文件名）
        markdown_id: 可选，Markdown 唯一标识，默认用 doc_id

    Returns:
        DocumentChunk 列表；section_path 为当前标题层级，content 为段落文本，content_type 为 GENERAL_RULE。
    """
    chunks: List[DocumentChunk] = []
    lines = markdown_content.splitlines()
    heading_re = re.compile(r"^(#{1,6})\s+(.+)$")
    path_by_level: List[str] = []  # path_by_level[i] 为 level i+1 的标题

    i = 0
    current_section_path: List[str] = []
    current_content_lines: List[str] = []

    def flush_chunk(content: str) -> None:
        if not content.strip():
            return
        chunks.append(
            DocumentChunk(
                doc_id=doc_id,
                doc_title=doc_title,
                section_path=current_section_path.copy(),
                content_type=ContentType.GENERAL_RULE,
                content=content.strip(),
                meta={"source": source},
                markdown_id=markdown_id or doc_id,
            )
        )

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        match = heading_re.match(stripped)

        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            # 先写出上一块
            if current_content_lines:
                flush_chunk("\n".join(current_content_lines))
                current_content_lines = []

            # 更新层级路径：保留 level 及以下，设置当前 level 的标题
            while len(path_by_level) > level:
                path_by_level.pop()
            if len(path_by_level) < level:
                path_by_level.extend([""] * (level - len(path_by_level)))
            path_by_level[level - 1] = title
            current_section_path = [t for t in path_by_level if t]

            # 当前标题行可视为该块的开始，把标题也放进内容里以保留上下文
            current_content_lines = [line]
            i += 1
            continue

        current_content_lines.append(line)
        i += 1

    if current_content_lines:
        flush_chunk("\n".join(current_content_lines))

    return chunks
