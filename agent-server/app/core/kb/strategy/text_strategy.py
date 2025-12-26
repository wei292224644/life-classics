"""
文本切分策略
按照段落、句子等文本单位进行切分
类似 dify 的通用文本分块模式
"""

import re
from typing import List, Iterator

from app.core.config import settings
from app.core.document_chunk import DocumentChunk


def _clean_text(text: str) -> str:
    """
    清理文本：替换连续的空格、换行符和制表符
    - 连续的空格 -> 单个空格
    - 连续的换行符 -> 单个换行符
    - 连续的制表符 -> 单个空格

    Args:
        text: 待清理的文本

    Returns:
        清理后的文本
    """
    if not text:
        return text

    # 替换连续的制表符为单个空格
    text = re.sub(r"\t+", " ", text)
    # 替换连续的空格为单个空格
    text = re.sub(r" +", " ", text)
    # 替换连续的换行符为单个换行符（保留换行符，因为用于切分）
    text = re.sub(r"\n+", "\n", text)
    # 去除首尾空白字符
    return text.strip()


def split_text_by_separator(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separator: str = "\n\n",
) -> List[str]:
    """
    按照指定分隔符切分文本，考虑 chunk_size 和 chunk_overlap

    Args:
        text: 待切分的文本内容
        chunk_size: 切分大小（字符数）
        chunk_overlap: 切分重叠大小（字符数）
        separator: 切分分隔符

    Returns:
        切分后的文本块列表
    """
    if not text:
        return []

    # 如果文本长度小于等于 chunk_size，直接返回
    if len(text) <= chunk_size:
        return [text]

    # 按照分隔符分割文本
    if separator:
        parts = [p.strip() for p in text.split(separator) if p.strip()]
    else:
        # 如果没有分隔符，按字符切分
        parts = [text]

    if not parts:
        return []

    chunks = []
    current_chunk_parts = []
    current_length = 0

    i = 0
    while i < len(parts):
        part = parts[i]
        part_length = len(part)
        separator_length = len(separator) if separator and current_chunk_parts else 0

        # 如果单个部分就超过 chunk_size，需要强制切分
        if part_length > chunk_size:
            # 先保存当前 chunk
            if current_chunk_parts:
                chunks.append(separator.join(current_chunk_parts))
                current_chunk_parts = []
                current_length = 0

            # 对超长部分进行强制切分（按字符切分）
            remaining_part = part
            while len(remaining_part) > chunk_size:
                chunks.append(remaining_part[:chunk_size])
                # 保留重叠部分
                if chunk_overlap > 0 and len(remaining_part) > chunk_size:
                    overlap_start = max(0, chunk_size - chunk_overlap)
                    remaining_part = remaining_part[overlap_start:]
                else:
                    remaining_part = remaining_part[chunk_size:]
            # 剩余部分作为新的 chunk 开始
            if remaining_part:
                current_chunk_parts = [remaining_part]
                current_length = len(remaining_part)
            i += 1
        # 如果当前 chunk 加上新部分不超过 chunk_size，则合并
        elif current_length + separator_length + part_length <= chunk_size:
            current_chunk_parts.append(part)
            current_length += separator_length + part_length
            i += 1
        # 否则保存当前 chunk，开始新 chunk
        else:
            if current_chunk_parts:
                chunks.append(separator.join(current_chunk_parts))

            # 处理重叠：从当前 chunk 的末尾部分取 overlap 内容
            if chunk_overlap > 0 and current_chunk_parts:
                # 计算需要保留的重叠部分（从后往前取）
                overlap_parts = []
                overlap_length = 0
                # 从最后一个 part 开始，往前取直到达到 overlap 大小
                for j in range(len(current_chunk_parts) - 1, -1, -1):
                    part_to_add = current_chunk_parts[j]
                    part_len = len(part_to_add)
                    sep_len = len(separator) if overlap_parts else 0

                    if overlap_length + sep_len + part_len <= chunk_overlap:
                        overlap_parts.insert(0, part_to_add)
                        overlap_length += sep_len + part_len
                    else:
                        # 如果最后一个 part 太长，需要截取
                        if not overlap_parts:
                            # 只取末尾的 overlap 长度
                            overlap_text = part_to_add[-chunk_overlap:]
                            if overlap_text:
                                overlap_parts.insert(0, overlap_text)
                        break

                # 将重叠部分作为新 chunk 的开始
                if overlap_parts:
                    current_chunk_parts = overlap_parts + [part]
                    current_length = len(separator.join(current_chunk_parts))
                else:
                    current_chunk_parts = [part]
                    current_length = part_length
            else:
                current_chunk_parts = [part]
                current_length = part_length
            i += 1

    # 保存最后一个 chunk
    if current_chunk_parts:
        chunks.append(separator.join(current_chunk_parts))

    return chunks if chunks else [text]


def split_text(documents: List[DocumentChunk], **kwargs) -> List[DocumentChunk]:
    """
    文本切分策略

    Args:
        documents: 待切分的文档列表
        **kwargs: 其他参数
            - chunk_size: 切分大小（默认 1024）
            - chunk_overlap: 切分重叠大小（默认 200）
            - chunk_separator: 切分分隔符（默认 "\n\n"）
            - clean_text_enabled: 是否清理文本（默认 True）

    Yields:
        切分后的 DocumentChunk 对象
    """
    chunk_size = kwargs.get("chunk_size", settings.CHUNK_SIZE)
    chunk_overlap = kwargs.get("chunk_overlap", settings.CHUNK_OVERLAP)
    chunk_separator = kwargs.get("chunk_separator", settings.CHUNK_SEPARATOR)
    clean_text_enabled = kwargs.get("clean_text_enabled", settings.CLEAN_TEXT_ENABLED)
    split_documents = []

    for document in documents:
        content = document.content
        if not content:
            continue

        # 切分文本
        text_chunks = split_text_by_separator(
            content, chunk_size, chunk_overlap, chunk_separator
        )

        # 为每个 chunk 创建 Document 对象
        for chunk_text in text_chunks:

            cleaned_chunk = chunk_text
            if clean_text_enabled:
                cleaned_chunk = _clean_text(chunk_text)
            if not cleaned_chunk:
                continue

            # 创建新的 Document
            split_documents.append(
                DocumentChunk(
                    doc_id=document.doc_id,
                    doc_title=document.doc_title,
                    section_path=document.section_path,
                    content_type=document.content_type,
                    content=cleaned_chunk,
                    meta={
                        **document.meta,
                    },
                )
            )
    return split_documents
