"""
PDF结构单元提取器

直接从PDF文档中提取结构单元（Structural Unit）：
- 表格中的一行
- 章节中的一句或一段
- 注释（如"注：……"）
"""

import re
from typing import List, Optional, Dict, Any
from pathlib import Path
import pdfplumber
from app.core.regulatory_semantic_analyzer import StructuralUnit


class PDFStructureExtractor:
    """PDF结构单元提取器"""
    
    def __init__(self):
        """初始化提取器"""
        pass
    
    def extract_structure(self, file_path: str) -> List[StructuralUnit]:
        """
        直接从PDF文件中提取结构单元
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            结构单元列表
        """
        units = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 先提取表格（需要排除表格区域的文本）
                    tables = page.extract_tables()
                    table_bboxes = []
                    if tables:
                        # 获取表格位置信息（用于排除表格区域的文本）
                        try:
                            found_tables = page.find_tables()
                            table_bboxes = [table.bbox for table in found_tables]
                        except Exception:
                            pass
                        
                        # 提取表格单元
                        for table_idx, table in enumerate(tables):
                            units.extend(self._extract_table_units_from_pdf(table, page_num, table_idx))
                    
                    # 提取文本内容（排除表格区域）
                    if table_bboxes:
                        # 过滤掉表格区域的文本
                        filtered_page = page.filter(
                            lambda obj: self._not_within_bboxes(obj, table_bboxes)
                        )
                        text = filtered_page.extract_text() or ""
                    else:
                        text = page.extract_text() or ""
                    
                    if text:
                        # 提取句子、段落和注释
                        units.extend(self._extract_text_units(text, page_num))
        
        except Exception as e:
            print(f"PDF解析失败: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        return units
    
    def _extract_text_units(self, text: str, page_num: int) -> List[StructuralUnit]:
        """
        从PDF文本中提取句子、段落和注释单元
        
        Args:
            text: PDF文本内容
            page_num: 页码
            
        Returns:
            结构单元列表
        """
        units = []
        
        if not text or not text.strip():
            return units
        
        # 规范化文本（清理多余空白）
        text = self._normalize_text(text)
        
        # 先提取注释（注：...）
        notes = self._extract_notes_from_text(text, page_num)
        units.extend(notes)
        
        # 移除已提取的注释，避免重复
        for note in notes:
            note_text = note.content
            text = text.replace(note_text, "", 1)  # 只替换第一次出现
        
        # 按段落分割（双换行）
        paragraphs = re.split(r'\n\s*\n', text)
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 按句号、问号、感叹号分割句子
            sentences = re.split(r'[。！？\n]', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 5:  # 过滤太短的句子
                    unit = StructuralUnit(
                        content=sentence,
                        unit_type="sentence",
                        page_num=page_num,
                        metadata={"source": "pdf_text"}
                    )
                    units.append(unit)
        
        return units
    
    def _extract_table_units_from_pdf(self, table: List[List], page_num: int, table_idx: int) -> List[StructuralUnit]:
        """
        从PDF表格中提取结构单元（每行作为一个单元）
        
        Args:
            table: pdfplumber提取的表格数据（二维列表）
            page_num: 页码
            table_idx: 表格索引
            
        Returns:
            结构单元列表
        """
        units = []
        
        if not table or len(table) == 0:
            return units
        
        # 第一行作为表头
        header = table[0] if table else []
        header = [str(cell).strip() if cell else "" for cell in header]
        
        # 提取数据行
        for row_idx, row in enumerate(table[1:], start=1):
            if not row:
                continue
            
            # 清理单元格内容
            cells = [str(cell).strip() if cell else "" for cell in row]
            
            # 跳过空行
            if not any(cells):
                continue
            
            # 将表格行转换为文本描述
            row_content = self._table_row_to_text(header, cells)
            
            unit = StructuralUnit(
                content=row_content,
                unit_type="table_row",
                page_num=page_num,
                metadata={
                    "header": header,
                    "cells": cells,
                    "table_index": table_idx,
                    "row_index": row_idx,
                    "source": "pdf_table"
                }
            )
            units.append(unit)
        
        return units
    
    def _extract_notes_from_text(self, text: str, page_num: int) -> List[StructuralUnit]:
        """
        从文本中提取注释（注：...）
        
        Args:
            text: PDF文本内容
            page_num: 页码
            
        Returns:
            结构单元列表
        """
        units = []
        
        # 查找所有注释
        note_patterns = [
            r'注[：:]\s*[^\n。！？]+[。！？]?',  # 注：...（到句号或换行）
            r'注[：:]\s*[^\n]+',  # 注：...（到换行）
        ]
        
        for pattern in note_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                note_text = match.group(0).strip()
                if len(note_text) > 3:  # 过滤太短的注释
                    unit = StructuralUnit(
                        content=note_text,
                        unit_type="note",
                        page_num=page_num,
                        metadata={
                            "source": "pdf_text",
                            "position": match.start()
                        }
                    )
                    units.append(unit)
        
        return units
    
    def _normalize_text(self, text: str) -> str:
        """规范化文本（清理多余空白）"""
        # 替换多个连续空白为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 替换多个连续换行为单个换行
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()
    
    def _not_within_bboxes(self, obj: Dict[str, Any], bboxes: List) -> bool:
        """
        判断对象是否不在任何bbox内
        
        Args:
            obj: pdfplumber对象（字符、文本等）
            bboxes: bbox列表，每个bbox为(x0, top, x1, bottom)
            
        Returns:
            如果对象不在任何bbox内返回True，否则返回False
        """
        if not bboxes:
            return True
        
        # 获取对象的bbox
        obj_bbox = None
        if isinstance(obj, dict):
            obj_bbox = (obj.get("x0", 0), obj.get("top", 0), obj.get("x1", 0), obj.get("bottom", 0))
        elif hasattr(obj, "bbox"):
            obj_bbox = obj.bbox
        
        if not obj_bbox:
            return True
        
        obj_x0, obj_top, obj_x1, obj_bottom = obj_bbox
        
        # 检查是否在任何表格bbox内
        for bbox in bboxes:
            if len(bbox) >= 4:
                x0, top, x1, bottom = bbox[:4]
                # 如果对象完全在表格bbox内，返回False
                if (obj_x0 >= x0 and obj_x1 <= x1 and 
                    obj_top >= top and obj_bottom <= bottom):
                    return False
        
        return True
    
    def _extract_from_markdown(self, markdown_text: str, page_num: int = 0) -> List[StructuralUnit]:
        """
        从Markdown文本中提取结构单元
        
        Args:
            markdown_text: Markdown文本
            page_num: 页码
            
        Returns:
            结构单元列表
        """
        units = []
        lines = markdown_text.split("\n")
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # 1. 提取表格行
            if self._is_table_line(line):
                table_units = self._extract_table_units(lines, i, page_num)
                units.extend(table_units)
                # 跳过已处理的表格行
                i = self._find_table_end(lines, i)
                continue
            
            # 2. 提取注释（注：...）
            if line.startswith("注：") or line.startswith("注:"):
                unit = StructuralUnit(
                    content=line,
                    unit_type="note",
                    page_num=page_num,
                    metadata={"line_number": i}
                )
                units.append(unit)
                i += 1
                continue
            
            # 3. 提取句子或段落
            # 合并连续的非空行作为段落
            paragraph_lines = []
            while i < len(lines) and lines[i].strip():
                current_line = lines[i].strip()
                # 跳过表格行和注释
                if not self._is_table_line(current_line) and not current_line.startswith("注"):
                    paragraph_lines.append(current_line)
                else:
                    break
                i += 1
            
            if paragraph_lines:
                paragraph_text = " ".join(paragraph_lines)
                # 按句号、问号、感叹号分割句子
                sentences = re.split(r'[。！？\n]', paragraph_text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 5:  # 过滤太短的句子
                        unit = StructuralUnit(
                            content=sentence,
                            unit_type="sentence",
                            page_num=page_num,
                            metadata={"line_number": i}
                        )
                        units.append(unit)
            else:
                i += 1
        
        return units
    
    def _is_table_line(self, line: str) -> bool:
        """判断是否是表格行"""
        # Markdown表格行：以|开头和结尾，中间包含|
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            return False
        
        # 检查是否是表格分隔行（如 | --- | --- |）
        parts = [p.strip() for p in line[1:-1].split("|")]
        if all(part and all(c in "-:" for c in part) for part in parts):
            return False  # 这是分隔行，不是数据行
        
        # 检查是否包含至少一个|分隔符
        return "|" in line[1:-1]
    
    def _extract_table_units(self, lines: List[str], start_idx: int, page_num: int) -> List[StructuralUnit]:
        """提取表格单元（每行作为一个结构单元）"""
        units = []
        header = None
        
        # 找到表格开始
        i = start_idx
        if i < len(lines):
            # 第一行可能是表头
            first_line = lines[i].strip()
            if self._is_table_line(first_line):
                header = [cell.strip() for cell in first_line[1:-1].split("|")]
                i += 1
        
        # 跳过分隔行
        if i < len(lines) and self._is_table_separator(lines[i]):
            i += 1
        
        # 提取数据行
        while i < len(lines):
            line = lines[i].strip()
            if not self._is_table_line(line):
                break
            
            # 解析表格行
            cells = [cell.strip() for cell in line[1:-1].split("|")]
            
            # 将表格行转换为文本描述
            row_content = self._table_row_to_text(header, cells)
            
            unit = StructuralUnit(
                content=row_content,
                unit_type="table_row",
                page_num=page_num,
                metadata={
                    "header": header,
                    "cells": cells,
                    "row_index": i - start_idx
                }
            )
            units.append(unit)
            i += 1
        
        return units
    
    def _table_row_to_text(self, header: Optional[List[str]], cells: List[str]) -> str:
        """将表格行转换为文本描述"""
        if header and len(header) == len(cells):
            # 使用表头作为字段名
            pairs = []
            for h, c in zip(header, cells):
                if h and c:
                    pairs.append(f"{h}: {c}")
            return "，".join(pairs)
        else:
            # 直接连接单元格
            return "，".join(c for c in cells if c)
    
    def _is_table_separator(self, line: str) -> bool:
        """判断是否是表格分隔行"""
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            return False
        parts = [p.strip() for p in line[1:-1].split("|")]
        return all(part and all(c in "-:" for c in part) for part in parts)
    
    def _find_table_end(self, lines: List[str], start_idx: int) -> int:
        """找到表格结束位置"""
        i = start_idx
        # 跳过表头
        if i < len(lines) and self._is_table_line(lines[i]):
            i += 1
        # 跳过分隔行
        if i < len(lines) and self._is_table_separator(lines[i]):
            i += 1
        # 跳过数据行
        while i < len(lines):
            if not self._is_table_line(lines[i]):
                break
            i += 1
        return i
    
    def extract_from_markdown_file(self, markdown_file_path: str) -> List[StructuralUnit]:
        """
        从Markdown文件中提取结构单元
        
        Args:
            markdown_file_path: Markdown文件路径
            
        Returns:
            结构单元列表
        """
        with open(markdown_file_path, "r", encoding="utf-8") as f:
            markdown_text = f.read()
        
        return self._extract_from_markdown(markdown_text, page_num=0)


# 全局提取器实例
pdf_structure_extractor = PDFStructureExtractor()
