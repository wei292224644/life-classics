"""
JSON 文件导入模块
"""

from typing import List
import json
from app.core.document_chunk import DocumentChunk


def import_json(file_path: str, strategy: str) -> List[DocumentChunk]:
    """
    导入 JSON 文件

    Args:
        file_path: JSON 文件路径

    Returns:
        DocumentChunk 对象，包含 JSON 内容
    """

    return []

    # with open(file_path, "r", encoding="utf-8") as f:
    #     data_list = json.load(f)

    # document_chunks = []
    # for data in data_list:
    #     document_chunks.append(
    #         DocumentChunk(
    #             # doc_id=data["doc_id"],
    #             # doc_title=data["doc_title"],
    #             # section_path=data["section_path"],
    #             # content_type=data["content_type"],
    #             # content=data["content"],
    #             # meta=data["meta"],

    #             content=data,
    #         )
    #     )
    # return document_chunks
