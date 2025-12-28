"""
PDF OCR 识别模块
用于识别扫描版 PDF 中的文字内容
"""

from typing import Optional
from app.core.document_chunk import DocumentChunk
from typing import List


def ocr_step(document: DocumentChunk) -> DocumentChunk:
    """
    对 PDF 文件进行 OCR 识别

    Args:
        document: 待识别的文档

    Returns:
        识别后的文档列表
    """
    if document.meta.get('IMAGE_OCR_RESULT', False):
        return ocr_image(document.content)
    else:
        return document


def ocr_image(image: str) -> str:
    """
    对图片进行 OCR 识别

    Args:
        image: 待识别的图片

    Returns:
        识别后的图片
    """
    return image
