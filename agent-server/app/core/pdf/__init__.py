"""
PDF 解析模块：通过 MinerU 本地服务将 PDF 转为 Markdown。
"""

from app.core.pdf.mineru_adapter import pdf_to_markdown

__all__ = ["pdf_to_markdown"]
