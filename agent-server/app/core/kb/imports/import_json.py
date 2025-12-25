"""
JSON 文件导入模块
"""

from typing import List, Dict, Any
from langchain_core.documents import Document
import json
import os


def import_json(file_path: str, strategy: str) -> List[Document]:
    """
    导入 JSON 文件

    Args:
        file_path: JSON 文件路径

    Returns:
        Document 对象，包含 JSON 内容
    """

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [
        Document(
            page_content=json.dumps(data, ensure_ascii=False),
            metadata={
                "file_name": os.path.basename(file_path),
                "file_path": file_path,
                "file_type": os.path.splitext(file_path)[1],
                "source_format": "json",
                "strategy": strategy,
            },
        )
    ]
