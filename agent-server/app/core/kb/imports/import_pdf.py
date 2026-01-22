"""
PDF 文件导入模块
支持文本提取和图片型PDF的OCR识别（使用 pymupdf4llm 内置的 OCR 能力）
"""

import os
from typing import List
from pathlib import Path

import pymupdf.layout  # 必须先导入这个来激活布局功能
import pymupdf4llm  # PyMuPDF for LLM
import pymupdf  # PyMuPDF
from app.core.document_chunk import DocumentChunk, ContentType
from app.core.config import settings


def extract_pdf_text(
    pdf_path: str, use_ocr: bool = None, ocr_language: str = None
) -> str:
    """
    从PDF中提取所有文本（基于 pymupdf4llm，支持自动OCR）

    Args:
        pdf_path: PDF文件路径
        use_ocr: 是否启用OCR（None时使用配置中的ENABLE_OCR）
        ocr_language: OCR语言（None时使用配置中的OCR_LANG）

    Returns:
        提取的文本内容（Markdown格式）
    """
    try:
        doc = pymupdf.open(pdf_path)
        try:
            total_pages = len(doc)
            print(f"PDF总页数: {total_pages}")

            # 确定OCR参数
            if use_ocr is None:
                use_ocr = settings.ENABLE_OCR
            if ocr_language is None:
                ocr_language = settings.OCR_LANG

            # 使用 pymupdf4llm.to_markdown 提取所有页面并转换为 markdown
            # 当导入 pymupdf.layout 后，会自动使用启发式方法检测需要OCR的页面
            # pages=None 表示提取所有页面
            markdown_text = pymupdf4llm.to_markdown(
                doc,
                pages=None,  # 提取所有页面
                header=False,
                footer=False,
                use_ocr=use_ocr,  # 启用OCR（如果启用，会自动检测需要OCR的页面）
                ocr_language=ocr_language,  # OCR语言
                ocr_dpi=400,  # OCR分辨率
            )

            print(f"总共提取了 {len(markdown_text)} 个字符")
            if use_ocr:
                print(f"OCR已启用（语言: {ocr_language}）")
            return markdown_text

        finally:
            doc.close()

    except Exception as e:
        print(f"PDF解析失败: {e}")
        import traceback

        traceback.print_exc()
        return ""


def import_pdf(file_path: str, original_filename: str = None) -> List[DocumentChunk]:
    """
    导入 PDF 文件，支持文本提取和图片型PDF的OCR识别

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
        doc_id = Path(original_filename).stem
        doc_title = Path(original_filename).stem
    else:
        file_name = os.path.basename(file_path)
        doc_id = file_path_obj.stem
        doc_title = file_path_obj.stem

    # 步骤1: 提取文本（使用 pymupdf4llm.to_markdown，自动处理OCR）
    print(f"\n处理PDF文件: {file_name}")

    # 直接使用 pymupdf4llm.to_markdown 提取文本
    # 当导入 pymupdf.layout 后，会自动使用启发式方法检测需要OCR的页面
    # 如果启用OCR，会自动对需要OCR的页面进行OCR处理
    final_content = extract_pdf_text(
        file_path,
        use_ocr=settings.ENABLE_OCR,
        ocr_language=settings.OCR_LANG,
    )

    # 步骤4: 创建 DocumentChunk
    if not final_content or not final_content.strip():
        print(f"警告: 未能从PDF中提取到内容: {file_name}")
        return []

    return [
        DocumentChunk(
            doc_id=doc_id,
            doc_title=doc_title,
            section_path=[],
            content_type=ContentType.NOTE,
            content=final_content,
            meta={
                "file_name": file_name,
                "file_path": file_path,
                "source_format": "pdf",
            },
        )
    ]
