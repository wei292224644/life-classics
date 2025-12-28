"""
PDF 文件导入模块
"""

import os
import re
from typing import List, Optional
from pathlib import Path

import pdfplumber
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.document_chunk import DocumentChunk, ContentType
from app.core.llm import get_llm


def extract_pdf_text(pdf_path: str) -> str:
    """
    从PDF中提取所有文本（基于 pdfplumber）

    Args:
        pdf_path: PDF文件路径

    Returns:
        提取的文本内容
    """
    text_parts = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"PDF总页数: {len(pdf.pages)}")

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    text_parts.append(f"=== 第 {page_num} 页 ===\n{text}\n")
                    print(f"  第 {page_num} 页: 提取了 {len(text)} 个字符")

            full_text = "\n".join(text_parts)
            print(f"\n总共提取了 {len(full_text)} 个字符")
            return full_text

    except Exception as e:
        print(f"PDF解析失败: {e}")
        import traceback

        traceback.print_exc()
        return ""


def import_pdf(file_path: str, original_filename: str = None) -> List[DocumentChunk]:
    """
    导入 PDF 文件，基于 pdfplumber 提取文本

    Args:
        file_path: PDF 文件路径
        original_filename: 原始文件名（如果提供，将使用此文件名作为 doc_id 和 doc_title）

    Returns:
        知识库通用数据结构列表
    """
    file_path_obj = Path(file_path)
    
    # 使用原始文件名或文件路径中的文件名
    if original_filename:
        file_name = original_filename
        # 从原始文件名中提取 doc_id（不含扩展名）
        doc_id = Path(original_filename).stem
        doc_title = Path(original_filename).stem
    else:
        file_name = os.path.basename(file_path)
        doc_id = file_path_obj.stem
        doc_title = file_path_obj.stem

    # 使用 pdfplumber 提取文本
    text_content = extract_pdf_text(file_path)

    if not text_content or not text_content.strip():
        print(f"警告: 未能从PDF中提取到文本: {file_name}")
        return []

    # 创建 DocumentChunk
    return [
        DocumentChunk(
            doc_id=doc_id,
            doc_title=doc_title,
            section_path=[],
            content_type=ContentType.NOTE,
            content=text_content,
            meta={
                "file_name": file_name,
                "file_path": file_path,
                "source_format": "pdf",
            },
        )
    ]
