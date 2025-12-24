"""
文档加载和处理模块 - 支持简单或结构化分割

重构后的架构：
1. 阶段1：文件格式转换（在 file_converter.py 中处理）
   - 将 PDF/TXT/MD/DOCX 等转换为 Markdown
   - 处理中英文问题
   - 处理表格转换（PDF表格 -> Markdown表格）

2. 阶段2：Markdown 解析和切片（本模块）
   - 对 Markdown 内容进行切片
   - 支持父子切片或 Simple 切片
   - 表格统一按 Markdown 表格处理
"""

import os
import re
from typing import List, Optional, Dict, Tuple, Any
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.file_converter import file_converter


class DocumentLoader:
    """
    文档加载器 - 支持多种分割策略

    工作流程：
    1. load_file: 调用 file_converter 将文件转换为 Markdown
    2. split_documents: 对 Markdown 内容进行切片
    """

    def __init__(self, split_strategy: Optional[str] = None):
        """
        初始化文档加载器

        Args:
            split_strategy: 分割策略，可选值:
                - "simple": 固定大小分割（适合常规纯文本）
                - "structured": 结构化分割（识别章节、公式等，TODO: 表格统一按 Markdown 处理）
        """
        self.split_strategy = split_strategy or settings.SPLIT_STRATEGY
        self.text_splitter = self._create_text_splitter()

    def _create_text_splitter(self):
        """根据策略创建对应的文本分割器"""
        if self.split_strategy == "simple":
            return RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
            )

        if self.split_strategy == "structured":
            return None

        raise ValueError(
            f"未知的分割策略 '{self.split_strategy}'，仅支持 simple 或 structured"
        )

    def load_file(self, file_path: str) -> List[Document]:
        """
        加载单个文件

        流程：
        1. 调用 file_converter 将文件转换为 Markdown 格式
        2. 返回 Markdown Document（后续由 split_documents 进行切片）
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()

        if file_ext not in settings.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        markdown_doc = file_converter.convert_to_markdown(file_path)
        return [markdown_doc]

    def load_directory(self, directory_path: str) -> List[Document]:
        """加载目录中的所有支持文件"""
        directory = Path(directory_path)
        all_documents = []

        for ext in settings.SUPPORTED_EXTENSIONS:
            for file_path in directory.rglob(f"*{ext}"):
                try:
                    docs = self.load_file(str(file_path))
                    all_documents.extend(docs)
                except Exception as e:
                    print(f"加载文件失败 {file_path}: {e}")
                    continue

        return all_documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        将文档分割成更小的块

        如果启用父子chunk模式，使用分层分割
        """
        if settings.ENABLE_PARENT_CHILD:
            return self._split_with_hierarchical(documents)

        if self.split_strategy == "structured":
            split_docs = self._split_documents_structured(documents)
        else:
            split_docs = self._split_documents_simple(documents)

            for i, doc in enumerate(split_docs):
                doc.metadata["split_strategy"] = self.split_strategy
                doc.metadata["chunk_id"] = i

        for doc in split_docs:
            cleaned_metadata = {}
            for key, value in doc.metadata.items():
                if isinstance(value, (str, int, float, type(None))):
                    cleaned_metadata[key] = value
                else:
                    cleaned_metadata[key] = str(value)
            doc.metadata = cleaned_metadata

        return split_docs

    def _clean_text(self, text: str) -> str:
        """
        清理文本：替换连续的空格、换行符和制表符
        - 连续的空格 -> 单个空格
        - 连续的换行符 -> 单个换行符
        - 连续的制表符 -> 单个空格
        """
        text = re.sub(r"\t+", " ", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    def _split_parent_chunks(self, text: str) -> List[str]:
        """
        按照dify设计切分父层级chunk
        - 按照段落（PARENT_SEPARATOR，默认\n\n）分割
        - 每个chunk最大长度为PARENT_CHUNK_SIZE（默认1024）
        """
        paragraphs = text.split(settings.PARENT_SEPARATOR)

        parent_chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = self._clean_text(paragraph)
            if not paragraph:
                continue

            if not current_chunk:
                current_chunk = paragraph
            elif (
                len(current_chunk) + len(settings.PARENT_SEPARATOR) + len(paragraph)
                <= settings.PARENT_CHUNK_SIZE
            ):
                current_chunk += settings.PARENT_SEPARATOR + paragraph
            else:
                if current_chunk:
                    parent_chunks.append(current_chunk)
                current_chunk = paragraph

                if len(paragraph) > settings.PARENT_CHUNK_SIZE:
                    while len(paragraph) > settings.PARENT_CHUNK_SIZE:
                        parent_chunks.append(paragraph[: settings.PARENT_CHUNK_SIZE])
                        paragraph = paragraph[settings.PARENT_CHUNK_SIZE :]
                    current_chunk = paragraph

        if current_chunk:
            parent_chunks.append(current_chunk)

        return parent_chunks

    def _is_markdown_table_line(self, line: str) -> bool:
        """判断是否是 Markdown 表格行"""
        line = line.strip()
        return line.startswith("|") and line.endswith("|") and "|" in line[1:-1]

    def _is_markdown_table_separator(self, line: str) -> bool:
        """判断是否是 Markdown 表格分隔行（如 | --- | --- |）"""
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            return False
        parts = [p.strip() for p in line[1:-1].split("|")]
        return all(part and all(c in "-:" for c in part) for part in parts)

    def _extract_markdown_table(
        self, lines: List[str], start_idx: int
    ) -> Tuple[Optional[str], int]:
        """
        从指定位置开始提取完整的 Markdown 表格

        Returns:
            (table_content, end_idx): 表格内容（整个表格）和结束位置，如果不是表格则返回 (None, start_idx)
        """
        if start_idx >= len(lines):
            return None, start_idx

        first_line = lines[start_idx].strip()
        if not self._is_markdown_table_line(first_line):
            return None, start_idx

        table_lines = [first_line]
        idx = start_idx + 1

        if idx < len(lines) and self._is_markdown_table_separator(lines[idx]):
            table_lines.append(lines[idx].strip())
            idx += 1

        while idx < len(lines):
            line = lines[idx].strip()
            if self._is_markdown_table_line(line):
                table_lines.append(line)
                idx += 1
            else:
                break

        if len(table_lines) >= 2:
            return "\n".join(table_lines), idx

        return None, start_idx

    def _parse_markdown_table(self, table_content: str) -> Dict[str, Any]:
        """
        解析 Markdown 表格内容

        Returns:
            包含表头、数据行的字典
        """
        lines = [line.strip() for line in table_content.split("\n") if line.strip()]
        if len(lines) < 2:
            return {"header": [], "rows": []}

        header_line = lines[0]
        has_separator = len(lines) > 1 and self._is_markdown_table_separator(lines[1])

        header = [
            cell.strip()
            for cell in header_line[1:-1].split("|")
            if cell.strip() or True
        ]

        data_rows = []
        start_idx = 2 if has_separator else 1
        for line in lines[start_idx:]:
            if self._is_markdown_table_line(line):
                row = [cell.strip() for cell in line[1:-1].split("|")]
                data_rows.append(row)

        return {"header": header, "rows": data_rows}

    def _convert_table_to_natural_language(
        self, table_content: str, table_title: str = None
    ) -> str:
        """
        将 Markdown 表格转换为自然语言格式

        Args:
            table_content: Markdown 表格内容
            table_title: 表格标题（从表格上一行获取）

        Returns:
            自然语言格式的表格描述
        """
        table_data = self._parse_markdown_table(table_content)
        header = table_data["header"]
        rows = table_data["rows"]

        if not header:
            return table_content

        table_name = table_title.strip() if table_title else "未知"
        columns = "、".join(col for col in header if col)

        result = ["【表格-分块】"]
        result.append(f"表名：{table_name}")
        result.append(f"列：{columns}")
        result.append("")
        result.append("本分块包含以下记录：")

        for i, row in enumerate(rows, 1):
            row_values = [str(cell) if cell else "无" for cell in row]
            row_text = "，".join(row_values)
            result.append(f"{i}.{row_text}")

        return "\n".join(result)

    def _split_child_chunks(self, parent_text: str) -> List[str]:
        """
        按照dify设计切分子chunk
        - 优先按照子块分隔符（CHILD_SEPARATOR，默认\n）分割，遇到换行就切分成新的子chunk
        - 每个chunk最大长度为CHILD_CHUNK_SIZE（默认512），如果单行超过最大长度才强制分割
        - 表格整个作为一个子chunk，并转换为自然语言格式
        """
        lines = parent_text.split(settings.CHILD_SEPARATOR)
        child_chunks = []
        i = 0

        while i < len(lines):
            line = lines[i]
            cleaned_line = self._clean_text(line)

            if not cleaned_line:
                i += 1
                continue

            table_content, end_idx = self._extract_markdown_table(lines, i)

            if table_content:
                table_title = None
                for offset in [1, 2]:
                    if i >= offset:
                        prev_line = lines[i - offset].strip()
                        if (
                            prev_line
                            and not self._is_markdown_table_line(prev_line)
                            and not self._is_markdown_table_separator(prev_line)
                        ):
                            table_title = prev_line
                            break

                natural_table = self._convert_table_to_natural_language(
                    table_content, table_title
                )
                child_chunks.append(natural_table)
                i = end_idx
            else:
                if len(cleaned_line) > settings.CHILD_CHUNK_SIZE:
                    while len(cleaned_line) > settings.CHILD_CHUNK_SIZE:
                        child_chunks.append(cleaned_line[: settings.CHILD_CHUNK_SIZE])
                        cleaned_line = cleaned_line[settings.CHILD_CHUNK_SIZE :]
                    if cleaned_line:
                        child_chunks.append(cleaned_line)
                else:
                    child_chunks.append(cleaned_line)
                i += 1

        return child_chunks

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """保留只有简单类型的元数据，删除列表/字典等复杂字段"""
        sanitized: Dict[str, Any] = {}
        for key, value in metadata.items():
            if key.startswith("_"):
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = None
            else:
                continue
        return sanitized

    def split_child_chunks_for_parent(
        self,
        parent_text: str,
        doc_metadata: Optional[Dict[str, Any]],
        parent_index: int,
    ) -> List[Document]:
        """
        根据当前 split_strategy 生成 child chunk 文档（包含 metadata）

        注意：输入已经是 Markdown 格式，表格已经是 Markdown 表格格式
        表格会转换为自然语言格式
        """
        metadata = dict(doc_metadata or {})
        metadata.setdefault("content_type", "text")

        child_texts = self._split_child_chunks(parent_text)
        child_docs: List[Document] = []

        for text in child_texts:
            is_table = text.startswith("【表格-分块】")
            content_type = "table" if is_table else "text"
            chunk_metadata = {
                            **self._sanitize_metadata(metadata),
                "content_type": content_type,
            }
            child_docs.append(Document(page_content=text, metadata=chunk_metadata))

        return child_docs

    def _split_with_hierarchical(self, documents: List[Document]) -> List[Document]:
        """
        使用分层分割生成父子chunk结构（Dify风格）
        - 按照段落（\n\n）切分父层级，最大长度1024
        - 按照行（\n）切分子块，最大长度512
        - 清理连续的空格、换行符和制表符
        """
        split_docs = []

        for doc in documents:
            text = doc.page_content or ""
            parent_texts = self._split_parent_chunks(text)

            for parent_idx, parent_text in enumerate(parent_texts):
                parent_metadata = {
                    **doc.metadata,
                    "chunk_type": "parent",
                    "split_strategy": "hierarchical",
                    "parent_index": parent_idx,
                }
                parent_doc = Document(
                    page_content=parent_text,
                    metadata=self._sanitize_metadata(parent_metadata),
                )
                split_docs.append(parent_doc)

                child_docs = self.split_child_chunks_for_parent(
                    parent_text, doc.metadata, parent_idx
                )
                for child_idx, child_doc in enumerate(child_docs):
                    child_metadata = {
                        **child_doc.metadata,
                        **{
                        "chunk_type": "child",
                        "split_strategy": (
                            self.split_strategy if self.split_strategy else "simple"
                        ),
                        "parent_index": parent_idx,
                        "child_index": child_idx,
                        "chunk_id": len(split_docs),
                        },
                    }
                    child_doc.metadata = self._sanitize_metadata(child_metadata)
                    split_docs.append(child_doc)

        return split_docs

    def _split_documents_simple(self, documents: List[Document]) -> List[Document]:
        """
        简单分割文档：按固定大小分割，同时处理表格

        表格会转换为自然语言格式，整个表格作为一个独立的 chunk
        """
        split_docs = []

        for doc in documents:
            markdown_text = doc.page_content
            lines = markdown_text.split("\n")
            i = 0
            current_chunk_lines = []
            current_chunk_length = 0

            while i < len(lines):
                line = lines[i]
                table_content, end_idx = self._extract_markdown_table(lines, i)

                if table_content:
                    if current_chunk_lines:
                        chunk_text = "\n".join(current_chunk_lines).strip()
                        if chunk_text:
                            split_docs.append(
                                Document(
                                    page_content=chunk_text,
                                    metadata={**doc.metadata, "content_type": "text"},
                                )
                            )
                        current_chunk_lines = []
                        current_chunk_length = 0

                    table_title = None
                    for offset in [1, 2]:
                        if i >= offset:
                            prev_line = lines[i - offset].strip()
                            if (
                                prev_line
                                and not self._is_markdown_table_line(prev_line)
                                and not self._is_markdown_table_separator(prev_line)
                            ):
                                table_title = prev_line
                                break

                    natural_table = self._convert_table_to_natural_language(
                        table_content, table_title
                    )
                    split_docs.append(
                        Document(
                            page_content=natural_table,
                            metadata={**doc.metadata, "content_type": "table"},
                        )
                    )
                    i = end_idx
            else:
                    line_length = len(line) + 1
                    if (
                        current_chunk_length + line_length > settings.CHUNK_SIZE
                        and current_chunk_lines
                    ):
                        chunk_text = "\n".join(current_chunk_lines).strip()
                        if chunk_text:
                            split_docs.append(
                                Document(
                                    page_content=chunk_text,
                                    metadata={**doc.metadata, "content_type": "text"},
                                )
                            )
                        current_chunk_lines = [line]
                        current_chunk_length = line_length
                    else:
                        current_chunk_lines.append(line)
                        current_chunk_length += line_length
                    i += 1

            if current_chunk_lines:
                chunk_text = "\n".join(current_chunk_lines).strip()
                if chunk_text:
                    split_docs.append(
                        Document(
                            page_content=chunk_text,
                            metadata={**doc.metadata, "content_type": "text"},
                        )
                    )

        return split_docs

    def _split_documents_structured(self, documents: List[Document]) -> List[Document]:
        """
        结构化分割文档：按章节、公式进行智能分割

        注意：输入已经是 Markdown 格式，表格已经是 Markdown 表格格式
        TODO: 统一按 Markdown 表格方式处理表格，不再单独处理
        """
        split_docs = []

        for doc in documents:
            markdown_text = doc.page_content
            chunks = self._split_text_structured(markdown_text, doc.metadata)

            for chunk in chunks:
                chunk.metadata.update(
                    {"split_strategy": "structured", "chunk_id": len(split_docs)}
                )
                chunk.metadata = self._sanitize_metadata(chunk.metadata)
                split_docs.append(chunk)

        return split_docs

    def _split_text_structured(self, text: str, base_metadata: Dict) -> List[Document]:
        """
        对 Markdown 文本进行结构化分割（识别章节、公式和表格）

        注意：输入已经是 Markdown 格式，表格已经是 Markdown 表格格式
        表格会转换为自然语言格式
        """
        chunks = []
        sections = self._identify_sections(text)

        if sections:
            for i, (section_title, section_text) in enumerate(sections):
                section_chunks = self._split_section_with_tables(
                    section_text, base_metadata, section_title
                )
                chunks.extend(section_chunks)
        else:
            section_chunks = self._split_section_with_tables(text, base_metadata, None)
            chunks.extend(section_chunks)

        return chunks

    def _split_section_with_tables(
        self, section_text: str, base_metadata: Dict, section_title: Optional[str]
    ) -> List[Document]:
        """
        分割章节，识别并处理表格

        表格会转换为自然语言格式，整个表格作为一个独立的 chunk
        """
        chunks = []
        lines = section_text.split("\n")
        i = 0
        current_text_lines = []

        while i < len(lines):
            line = lines[i]
            table_content, end_idx = self._extract_markdown_table(lines, i)

            if table_content:
                if current_text_lines:
                    text_content = "\n".join(current_text_lines).strip()
                    if text_content:
                        if self._contains_formula(text_content):
                            formula_chunks = self._split_formula_section(
                                text_content,
                                {**base_metadata, "section": section_title},
                                section_title,
                            )
                            chunks.extend(formula_chunks)
                        else:
                            if len(text_content) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                                text_chunks = self._split_large_text(
                                    text_content,
                                    {**base_metadata, "section": section_title},
                                    settings.STRUCTURED_TEXT_CHUNK_SIZE,
                                    settings.STRUCTURED_TEXT_CHUNK_OVERLAP,
                                )
                                chunks.extend(text_chunks)
                            else:
                chunks.append(
                    Document(
                        page_content=text_content,
                        metadata={
                            **base_metadata,
                            "content_type": "text",
                                            "section": section_title,
                        },
                    )
                )
                    current_text_lines = []

                table_title = None
                for offset in [1, 2]:
                    if i >= offset:
                        prev_line = lines[i - offset].strip()
                        if (
                            prev_line
                            and not self._is_markdown_table_line(prev_line)
                            and not self._is_markdown_table_separator(prev_line)
                        ):
                            table_title = prev_line
                            break

                natural_table = self._convert_table_to_natural_language(
                    table_content, table_title
                )
                chunks.append(
                    Document(
                        page_content=natural_table,
                        metadata={
                            **base_metadata,
                            "content_type": "table",
                            "section": section_title,
                        },
                    )
                )
                i = end_idx
            else:
                current_text_lines.append(line)
                i += 1

        if current_text_lines:
            text_content = "\n".join(current_text_lines).strip()
            if text_content:
                if self._contains_formula(text_content):
                    formula_chunks = self._split_formula_section(
                        text_content,
                        {**base_metadata, "section": section_title},
                        section_title,
                    )
                    chunks.extend(formula_chunks)
                else:
                    if len(text_content) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                        text_chunks = self._split_large_text(
                            text_content,
                            {**base_metadata, "section": section_title},
                            settings.STRUCTURED_TEXT_CHUNK_SIZE,
                            settings.STRUCTURED_TEXT_CHUNK_OVERLAP,
                        )
                        chunks.extend(text_chunks)
                    else:
                        chunks.append(
                            Document(
                                page_content=text_content,
                                metadata={
                                    **base_metadata,
                                    "content_type": "text",
                                    "section": section_title,
                                },
                    )
                )

        return chunks

    def _identify_sections(self, text: str) -> List[Tuple[str, str]]:
        """识别文档章节"""
        sections = []
        lines = text.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            match = re.match(settings.STRUCTURED_SECTION_PATTERN, line.strip())
            if match:
                if current_section and current_content:
                    sections.append((current_section, "\n".join(current_content)))
                current_section = line.strip()
                current_content = [line]
            else:
                current_content.append(line)

        if current_section and current_content:
            sections.append((current_section, "\n".join(current_content)))

        if not sections:
            sections.append((None, text))

        return sections

    def _contains_formula(self, text: str) -> bool:
        """检测文本是否包含公式/结构式"""
        formula_patterns = [
            r"[A-Z][a-z]?\d*[A-Z]?[a-z]?\d*",  # 化学式如 C6H12O6
            r"[=+\-*/^∑∫√]",  # 数学符号
            r"\\frac|\\sqrt|\\sum",  # LaTeX公式
            r"[HO]\s*[CN]",  # 化学结构式片段
            r"\([A-Z][a-z]?\d*\)",  # 带括号的化学式
        ]
        for pattern in formula_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _split_formula_section(
        self, text: str, base_metadata: Dict, section: Optional[str]
    ) -> List[Document]:
        """分割包含公式的章节，保持公式+上下文"""
        chunks = []
        sentences = re.split(r"[。！？\n]", text)

        current_chunk = []
        formula_context = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if self._contains_formula(sentence):
                if current_chunk:
                    chunks.append(
                        Document(
                            page_content="\n".join(current_chunk),
                            metadata={
                                **base_metadata,
                                "content_type": "text",
                                "section": section,
                            },
                        )
                    )
                    current_chunk = []

                context_count = min(
                    settings.STRUCTURED_FORMULA_CONTEXT, len(formula_context)
                )
                context_sentences = (
                    formula_context[-context_count:] + [sentence]
                    if formula_context
                    else [sentence]
                )

                chunks.append(
                    Document(
                        page_content="\n".join(context_sentences),
                        metadata={
                            **base_metadata,
                            "content_type": "formula",
                            "section": section,
                        },
                    )
                )
                formula_context = []
            else:
                current_chunk.append(sentence)
                formula_context.append(sentence)

                if len("\n".join(current_chunk)) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                    chunks.append(
                        Document(
                            page_content="\n".join(current_chunk),
                            metadata={
                                **base_metadata,
                                "content_type": "text",
                                "section": section,
                            },
                        )
                    )
                    current_chunk = []

        if current_chunk:
            chunks.append(
                Document(
                    page_content="\n".join(current_chunk),
                    metadata={
                        **base_metadata,
                        "content_type": "text",
                        "section": section,
                    },
                )
            )

        return (
            chunks
            if chunks
            else [
                Document(
                    page_content=text,
                    metadata={
                        **base_metadata,
                        "content_type": "formula",
                        "section": section,
                    },
                )
            ]
        )

    def _split_large_text(
        self, text: str, base_metadata: Dict, chunk_size: int, overlap: int
    ) -> List[Document]:
        """将大文本分割成小块"""
        chunks = []
        sentences = re.split(r"[。！？\n]", text)

        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence)

            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(
                    Document(
                        page_content="\n".join(current_chunk),
                        metadata=base_metadata.copy(),
                    )
                )

                overlap_text = (
                    "\n".join(current_chunk[-overlap // 50 :]) if current_chunk else ""
                )
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_length = len("\n".join(current_chunk))
            else:
                current_chunk.append(sentence)
                current_length += sentence_length + 1

        if current_chunk:
            chunks.append(
                Document(
                    page_content="\n".join(current_chunk), metadata=base_metadata.copy()
                )
            )

        return (
            chunks if chunks else [Document(page_content=text, metadata=base_metadata)]
        )

    def split_documents_with_strategy(
        self, documents: List[Document], strategy: str
    ) -> List[Document]:
        """
        使用指定策略分割文档（临时使用，不改变实例的默认策略）

        Args:
            documents: 要分割的文档列表
            strategy: 分割策略名称（"simple" 或 "structured"）
        """
        original_strategy = self.split_strategy
        self.split_strategy = strategy
        self.text_splitter = self._create_text_splitter()
        result = self.split_documents(documents)
        self.split_strategy = original_strategy
        self.text_splitter = self._create_text_splitter()
        return result


# 全局文档加载器实例
document_loader = DocumentLoader()
