"""
文件格式转换器 - 将各种格式文件统一转换为 Markdown

设计理念：
1. 阶段1：文件格式转换（PDF/TXT/MD/DOCX等 -> Markdown）
   - 处理中英文问题（统一文本格式）
   - 处理 OCR（如果需要）
   - 提取表格并转换为 Markdown 表格格式
   - 输出统一的 Markdown 格式

2. 阶段2：Markdown 解析和切片（在 document_loader.py 中处理）
   - 沿用现有的父子切片或 Simple 切片逻辑
   - 表格统一按 Markdown 表格处理
"""

import os
import re
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
)
import pdfplumber
from app.core.config import settings

# OCR 相关导入（可选）
try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    from pdf2image.exceptions import PDFInfoNotInstalledError

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    Image = None
    convert_from_path = None
    PDFInfoNotInstalledError = None


class FileConverter:
    """文件格式转换器 - 将各种格式转换为 Markdown"""

    def __init__(self):
        os.makedirs(settings.MARKDOWN_CACHE_DIR, exist_ok=True)

    def convert_to_markdown(self, file_path: str) -> Document:
        """
        将文件转换为 Markdown 格式的 Document

        Args:
            file_path: 文件路径

        Returns:
            Document 对象，page_content 为 Markdown 格式的文本
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()

        if file_ext not in settings.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        # 根据文件类型选择对应的转换器
        if file_ext == ".txt":
            doc = self._convert_txt_to_markdown(file_path, file_path_obj)
        elif file_ext == ".pdf":
            doc = self._convert_pdf_to_markdown(file_path, file_path_obj)
        elif file_ext == ".md":
            doc = self._convert_markdown_to_markdown(file_path, file_path_obj)
        elif file_ext == ".docx":
            doc = self._convert_docx_to_markdown(file_path, file_path_obj)
        else:
            raise ValueError(f"未实现的文件类型转换器: {file_ext}")

        # 保存 Markdown 到 cache 文件夹
        self._save_markdown_to_cache(doc, file_path_obj)

        return doc

    def _save_markdown_to_cache(self, doc: Document, file_path_obj: Path):
        """
        将 Markdown 内容保存到 cache 文件夹

        Args:
            doc: Document 对象，包含 Markdown 内容
            file_path_obj: 原始文件路径对象
        """
        cache_file_name = file_path_obj.stem + ".md"
        cache_file_path = Path(settings.MARKDOWN_CACHE_DIR) / cache_file_name

        try:
            with open(cache_file_path, "w", encoding="utf-8") as f:
                f.write(doc.page_content)
            print(f"  ✓ Markdown 已保存到: {cache_file_path}")
        except Exception as e:
            print(f"  ⚠ 保存 Markdown 到 cache 失败: {e}")

    def _convert_txt_to_markdown(self, file_path: str, file_path_obj: Path) -> Document:
        """将 TXT 文件转换为 Markdown"""
        loader = TextLoader(file_path, encoding="utf-8")
        documents = loader.load()

        if not documents:
            text = ""
        else:
            text = documents[0].page_content

        text = self._normalize_text(text)
        markdown_content = text

        return Document(
            page_content=markdown_content,
            metadata={
                "file_name": file_path_obj.name,
                "file_path": str(file_path_obj),
                "file_type": ".txt",
                "source_format": "txt",
            },
        )

    def _convert_markdown_to_markdown(
        self, file_path: str, file_path_obj: Path
    ) -> Document:
        """将 Markdown 文件转换为 Markdown（标准化处理）"""
        loader = UnstructuredMarkdownLoader(file_path)
        documents = loader.load()

        if not documents:
            text = ""
        else:
            text = documents[0].page_content

        # 处理中英文问题（统一文本格式）
        text = self._normalize_text(text)

        return Document(
            page_content=text,
            metadata={
                "file_name": file_path_obj.name,
                "file_path": str(file_path_obj),
                "file_type": ".md",
                "source_format": "markdown",
            },
        )

    def _convert_docx_to_markdown(
        self, file_path: str, file_path_obj: Path
    ) -> Document:
        """将 DOCX 文件转换为 Markdown"""
        loader = UnstructuredWordDocumentLoader(file_path)
        documents = loader.load()

        if not documents:
            text = ""
        else:
            text = documents[0].page_content

        # 处理中英文问题（统一文本格式）
        text = self._normalize_text(text)

        # TODO: 处理 DOCX 中的表格，转换为 Markdown 表格格式
        # 需要从 DOCX 中提取表格数据，然后使用 _table_to_markdown 方法转换
        # 目前先直接使用文本内容

        return Document(
            page_content=text,
            metadata={
                "file_name": file_path_obj.name,
                "file_path": str(file_path_obj),
                "file_type": ".docx",
                "source_format": "docx",
            },
        )

    def _convert_pdf_to_markdown(self, file_path: str, file_path_obj: Path) -> Document:
        """
        将 PDF 文件转换为 Markdown

        处理流程：
        1. 提取文本（如果失败则使用 OCR）
        2. 提取表格并转换为 Markdown 表格
        3. 处理中英文问题
        4. 合并文本和表格为 Markdown 格式
        """
        markdown_parts = []

        if settings.ENABLE_OCR:
            if OCR_AVAILABLE:
                print(f"OCR 功能已启用，语言: {settings.OCR_LANG}")
            else:
                print("警告: OCR 功能已启用但依赖未安装")

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"PDF 总页数: {total_pages}")

            for page_num, page in enumerate(pdf.pages, 1):
                tables = []
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    tables = []

                table_bboxes = []
                found_tables = []
                if tables:
                    try:
                        found_tables = page.find_tables()
                        table_bboxes = [table.bbox for table in found_tables]
                    except Exception:
                        pass

                if table_bboxes:
                    filtered_page = page.filter(
                        lambda obj: self._not_within_bboxes(obj, table_bboxes)
                    )
                    text = filtered_page.extract_text() or ""
                else:
                    text = page.extract_text() or ""

                original_text_length = len(text.strip())

                if (
                    settings.ENABLE_OCR
                    and OCR_AVAILABLE
                    and original_text_length < settings.OCR_MIN_TEXT_LENGTH
                ):
                    print(
                        f"页面 {page_num}/{total_pages}: 文本长度 {original_text_length} < {settings.OCR_MIN_TEXT_LENGTH}，尝试使用 OCR..."
                    )
                    ocr_text = self._extract_text_with_ocr(file_path, page_num)
                    if ocr_text:
                        text = ocr_text
                        print(f"  ✓ OCR 成功: 提取了 {len(text)} 个字符")
                    else:
                        print(f"  ✗ OCR 失败: 未能提取文本")

                page_content = self._merge_text_and_tables_by_position(
                    page, text, tables, found_tables
                )
                if page_content:
                    markdown_parts.append(page_content)

        markdown_content = "\n".join(markdown_parts)

        if not markdown_content.strip():
            markdown_content = ""

        return Document(
            page_content=markdown_content,
            metadata={
                "file_name": file_path_obj.name,
                "file_path": str(file_path_obj),
                "file_type": ".pdf",
                "source_format": "pdf",
            },
        )

    def _extract_text_with_ocr(self, pdf_path: str, page_num: int) -> str:
        """
        使用OCR提取PDF页面中的文本（适用于图片型PDF）

        Args:
            pdf_path: PDF文件路径
            page_num: 页码（从1开始）

        Returns:
            提取的文本内容
        """
        if not OCR_AVAILABLE or not settings.ENABLE_OCR:
            return ""

        try:
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=300,
            )

            if not images:
                print(f"  警告: 无法将页面 {page_num} 转换为图片")
                return ""

            image = images[0]
            text = pytesseract.image_to_string(
                image,
                lang=settings.OCR_LANG,
            )

            result = text.strip() if text else ""
            if not result:
                print(f"  警告: OCR 未能识别出文本（可能是空白页或图片质量问题）")
            return result
        except PDFInfoNotInstalledError:
            print(f"  错误: Poppler 未安装，无法将 PDF 转换为图片")
            return ""
        except FileNotFoundError as e:
            if "tesseract" in str(e).lower() or "pdfinfo" in str(e).lower():
                print(f"  错误: 系统依赖未找到")
            else:
                print(f"  错误: {e}")
            return ""
        except Exception as e:
            print(f"  错误: OCR提取失败 (页面 {page_num}): {type(e).__name__}: {e}")
            return ""

    def _merge_text_and_tables_by_position(
        self,
        page: Any,
        text: str,
        tables: List[List],
        found_tables: List[Any],
    ) -> str:
        """
        按照位置信息合并文本和表格，使表格出现在正确的位置
        
        策略：
        1. 获取所有文本字符的位置信息（排除表格区域）
        2. 获取表格的位置信息
        3. 按照 Y 坐标（从上到下）排序
        4. 按顺序输出文本和表格
        
        Args:
            page: pdfplumber 页面对象
            text: 已排除表格的文本内容
            tables: 提取的表格数据列表
            found_tables: pdfplumber 找到的表格对象列表（包含位置信息）
            
        Returns:
            合并后的 Markdown 内容
        """
        if not tables or not found_tables:
            if text:
                text = self._normalize_text(text)
                return f"{text}\n" if text.strip() else ""
            return ""

        text = self._normalize_text(text) if text else ""
        
        table_info_list = []
        for i, (table, found_table) in enumerate(zip(tables, found_tables)):
            if table and found_table:
                table_md = self._table_to_markdown(table)
                x0, top, x1, bottom = found_table.bbox
                table_info_list.append({
                    "type": "table",
                    "content": table_md,
                    "position": bottom,
                    "table_top": top,
                })

        if not table_info_list:
            return f"{text}\n" if text.strip() else ""

        if not text.strip():
            parts = [info["content"] for info in sorted(table_info_list, key=lambda x: x["position"], reverse=True)]
            return "\n\n".join(parts) + "\n\n" if parts else ""

        try:
            text_chars = page.chars
            if not text_chars:
                parts = []
                if text.strip():
                    parts.append(text)
                for info in sorted(table_info_list, key=lambda x: x["position"], reverse=True):
                    parts.append(info["content"])
                return "\n\n".join(parts) + "\n\n" if parts else ""

            text_lines = []
            current_line = []
            current_line_top = None
            
            for char in text_chars:
                if not self._not_within_bboxes(char, [t.bbox for t in found_tables]):
                    continue
                
                char_top = char.get("top", 0)
                if current_line_top is None or abs(char_top - current_line_top) < 2:
                    current_line.append(char.get("text", ""))
                    current_line_top = char_top
                else:
                    if current_line:
                        text_lines.append({
                            "text": "".join(current_line),
                            "top": current_line_top,
                        })
                    current_line = [char.get("text", "")]
                    current_line_top = char_top
            
            if current_line:
                text_lines.append({
                    "text": "".join(current_line),
                    "top": current_line_top,
                })

            all_items = []
            for line in text_lines:
                all_items.append({
                    "type": "text",
                    "content": line["text"],
                    "top": line["top"],
                })
            
            for info in table_info_list:
                all_items.append({
                    "type": "table",
                    "content": info["content"],
                    "top": info["position"],
                })

            all_items.sort(key=lambda x: x["top"])

            result_parts = []
            for item in all_items:
                if item["type"] == "table":
                    result_parts.append(item["content"])
                else:
                    content = item["content"].strip()
                    if content:
                        result_parts.append(content)

            result = "\n\n".join(part for part in result_parts if part.strip())
            return f"{result}\n" if result else ""
        except Exception as e:
            print(f"  警告: 按位置合并文本和表格失败: {e}")
            parts = []
            if text.strip():
                parts.append(text)
            for info in sorted(table_info_list, key=lambda x: x["position"], reverse=True):
                parts.append(info["content"])
            return "\n\n".join(parts) + "\n\n" if parts else ""

    def _not_within_bboxes(self, obj: Dict[str, Any], bboxes: List[Tuple[float, float, float, float]]) -> bool:
        """
        检查对象是否在所有表格边界框之外
        
        Args:
            obj: pdfplumber 对象（字符、文本等）
            bboxes: 表格边界框列表，每个 bbox 为 (x0, top, x1, bottom)
            
        Returns:
            True 如果对象在表格边界框外，False 如果在表格内
        """
        if not bboxes:
            return True
        
        def obj_in_bbox(_bbox):
            """判断对象的中心点是否在边界框内"""
            x0, top, x1, bottom = _bbox
            v_mid = (obj.get("top", 0) + obj.get("bottom", 0)) / 2
            h_mid = (obj.get("x0", 0) + obj.get("x1", 0)) / 2
            return (h_mid >= x0) and (h_mid < x1) and (v_mid >= top) and (v_mid < bottom)
        
        return not any(obj_in_bbox(bbox) for bbox in bboxes)

    def _escape_table_cell(self, cell: Any) -> str:
        """
        转义表格单元格内容，处理特殊字符和换行符

        严格按照单元格内容处理，单元格内的换行符会保留在单元格内（使用 <br> 标签）。

        Args:
            cell: 单元格内容（可能是任何类型）

        Returns:
            转义后的字符串
        """
        if cell is None:
            return ""

        cell_str = str(cell)

        # 处理换行符：保留在单元格内，使用 <br> 标签
        # 这样单元格内的换行会被保留在单元格内，不会分割成新的单元格
        cell_str = cell_str.replace("\r\n", "").replace("\n", "").replace("\r", "")

        # 转义管道符（|），这是 Markdown 表格的分隔符
        cell_str = cell_str.replace("|", "\\|")

        # 清理多余的空格（但保留单个空格，不影响 <br> 标签）
        cell_str = re.sub(r" +", " ", cell_str)

        return cell_str.strip()

    def _table_to_markdown(self, table: List[List]) -> str:
        """
        将表格转换为Markdown格式

        严格按照 table 传入的结构来构建表格，保持单元格的完整性。
        单元格内的换行符会被转换为空格，特殊字符会被转义。

        Args:
            table: 表格数据，二维列表，每个元素代表一行，每行是一个列表代表单元格

        Returns:
            Markdown 格式的表格字符串
        """
        if not table or not table[0]:
            return ""

        md_lines = []

        # 确保所有行的列数一致（以第一行为准）
        max_cols = len(table[0])

        # 处理表头
        header = table[0]
        # 确保表头列数正确
        header = list(header) + [""] * (max_cols - len(header))
        escaped_header = [self._escape_table_cell(cell) for cell in header]
        md_lines.append("| " + " | ".join(escaped_header) + " |")

        # 添加分隔行（默认左对齐）
        md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

        # 处理数据行
        for row in table[1:]:
            # 确保行列数正确，不足的用空字符串填充
            row = list(row) + [""] * (max_cols - len(row))
            escaped_row = [self._escape_table_cell(cell) for cell in row]
            md_lines.append("| " + " | ".join(escaped_row) + " |")

        return "\n".join(md_lines)

    def _normalize_text(self, text: str) -> str:
        """
        标准化文本，处理中英文问题

        当前实现：
        - 清理连续的空格、换行符和制表符
        - 统一换行符格式

        TODO: 根据需求添加更多中英文处理逻辑
        - 全角半角转换
        - 中英文标点符号统一
        - 其他文本标准化需求
        """
        text = re.sub(r"\t+", " ", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()


# 全局文件转换器实例
file_converter = FileConverter()
