"""
文档加载和处理模块 - 支持简单或结构化分割，优化表格和公式处理
"""

import os
import re
from typing import List, Optional, Dict, Tuple, Any
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
)
import pdfplumber
from app.core.config import settings
from app.core.embeddings import get_embedding_model


class DocumentLoader:
    """文档加载器 - 支持多种分割策略"""

    def __init__(self, split_strategy: Optional[str] = None):
        """
        初始化文档加载器

        Args:
            split_strategy: 分割策略，可选值:
                - "simple": 固定大小分割（适合常规纯文本）
                - "structured": 结构化分割（优先处理PDF表格和公式）
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
            # 结构化策略通过自定义流程处理，text_splitter不参与
            return None

        raise ValueError(
            f"未知的分割策略 '{self.split_strategy}'，仅支持 simple 或 structured"
        )

    def load_file(self, file_path: str) -> List[Document]:
        """加载单个文件"""
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()

        if file_ext not in settings.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        # 根据文件类型选择对应的加载器
        if file_ext == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
            documents = loader.load()
        elif file_ext == ".pdf":
            documents = self._load_pdf_structured(file_path, file_path_obj)
        elif file_ext == ".md":
            loader = UnstructuredMarkdownLoader(file_path)
            documents = loader.load()
        elif file_ext == ".docx":
            loader = UnstructuredWordDocumentLoader(file_path)
            documents = loader.load()
        else:
            raise ValueError(f"未实现的文件类型加载器: {file_ext}")

        # 添加文件元数据
        for doc in documents:
            doc.metadata["file_name"] = file_path_obj.name
            doc.metadata["file_path"] = str(file_path_obj)
            doc.metadata["file_type"] = file_ext

        return documents

    def _load_pdf_structured(
        self, file_path: str, file_path_obj: Path
    ) -> List[Document]:
        """
        使用pdfplumber结构化加载PDF，提取表格、识别章节和公式
        """
        documents = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # 提取文本
                text = page.extract_text() or ""

                # 提取表格
                tables = (
                    page.extract_tables(
                        table_settings={
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                            "edge_min_length": 50,
                            "snap_tolerance": 3,
                            "join_tolerance": 2,
                        }
                    )
                    or []
                )

                if not text and not tables:
                    continue

                # 创建页面文档，包含表格信息
                page_doc = Document(
                    page_content=text,
                    metadata={
                        "file_name": file_path_obj.name,
                        "file_path": str(file_path_obj),
                        "file_type": ".pdf",
                        "page_number": page_num,
                        "table_count": len(tables),
                        "_tables": tables,  # 内部使用，用于后续分割
                        "_raw_text": text,  # 保留原始文本
                    },
                )
                documents.append(page_doc)

        return documents

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
            if self.text_splitter is None:
                raise RuntimeError("simple 策略需要 text_splitter，但未创建")

            split_docs = self.text_splitter.split_documents(documents)

            for i, doc in enumerate(split_docs):
                doc.metadata["split_strategy"] = self.split_strategy
                doc.metadata["chunk_id"] = i

        # 清理所有内部使用的元数据字段
        for doc in split_docs:
            doc.metadata.pop("_tables", None)
            doc.metadata.pop("_raw_text", None)
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
        # 替换连续的制表符为单个空格
        text = re.sub(r"\t+", " ", text)
        # 替换连续的空格为单个空格
        text = re.sub(r" +", " ", text)
        # 替换连续的换行符为单个换行符（保留换行符，因为用于切分）
        text = re.sub(r"\n+", "\n", text)
        # 去除首尾空白字符
        return text.strip()

    def _split_parent_chunks(self, text: str) -> List[str]:
        """
        按照dify设计切分父层级chunk
        - 按照段落（PARENT_SEPARATOR，默认\n\n）分割
        - 每个chunk最大长度为PARENT_CHUNK_SIZE（默认1024）
        """
        # 先按照父层级分隔符分割段落（在清理之前，保留分隔符）
        paragraphs = text.split(settings.PARENT_SEPARATOR)

        parent_chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # 清理段落文本
            paragraph = self._clean_text(paragraph)
            if not paragraph:
                continue

            # 如果当前chunk加上新段落不超过最大长度，则合并
            if not current_chunk:
                current_chunk = paragraph
            elif (
                len(current_chunk) + len(settings.PARENT_SEPARATOR) + len(paragraph)
                <= settings.PARENT_CHUNK_SIZE
            ):
                current_chunk += settings.PARENT_SEPARATOR + paragraph
            else:
                # 保存当前chunk，开始新chunk
                if current_chunk:
                    parent_chunks.append(current_chunk)
                current_chunk = paragraph

                # 如果单个段落就超过最大长度，需要强制分割
                if len(paragraph) > settings.PARENT_CHUNK_SIZE:
                    # 按字符强制分割
                    while len(paragraph) > settings.PARENT_CHUNK_SIZE:
                        parent_chunks.append(paragraph[: settings.PARENT_CHUNK_SIZE])
                        paragraph = paragraph[settings.PARENT_CHUNK_SIZE :]
                    current_chunk = paragraph

        # 保存最后一个chunk
        if current_chunk:
            parent_chunks.append(current_chunk)

        return parent_chunks

    def _split_child_chunks(self, parent_text: str) -> List[str]:
        """
        按照dify设计切分子chunk
        - 优先按照子块分隔符（CHILD_SEPARATOR，默认\n）分割，遇到换行就切分成新的子chunk
        - 每个chunk最大长度为CHILD_CHUNK_SIZE（默认512），如果单行超过最大长度才强制分割
        """
        # 按照子块分隔符分割（在清理之前，保留分隔符）
        lines = parent_text.split(settings.CHILD_SEPARATOR)

        child_chunks = []

        for line in lines:
            # 清理行文本
            line = self._clean_text(line)
            if not line:
                continue

            # 优先按照换行切分：每一行作为一个独立的子chunk
            # 如果单行超过最大长度，才需要强制分割
            if len(line) > settings.CHILD_CHUNK_SIZE:
                # 按字符强制分割
                while len(line) > settings.CHILD_CHUNK_SIZE:
                    child_chunks.append(line[: settings.CHILD_CHUNK_SIZE])
                    line = line[settings.CHILD_CHUNK_SIZE :]
                # 保存剩余部分
                if line:
                    child_chunks.append(line)
            else:
                # 单行不超过最大长度，直接作为一个子chunk
                child_chunks.append(line)

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
                # skip complex structures (list/dict) to avoid Chroma 报错
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
        """
        metadata = dict(doc_metadata or {})
        metadata.setdefault("content_type", "text")

        tables = metadata.get("_tables")

        child_texts = self._split_child_chunks(parent_text)
        child_docs: List[Document] = [
            Document(
                page_content=text,
                metadata={**self._sanitize_metadata(metadata), "content_type": "text"},
            )
            for text in child_texts
        ]

        if self.split_strategy == "structured" and tables:
            for table_idx, table in enumerate(tables):
                table_md = self._table_to_markdown(table)
                child_docs.append(
                    Document(
                        page_content=table_md,
                        metadata={
                            **self._sanitize_metadata(metadata),
                            "content_type": "table",
                            "table_id": table_idx + 1,
                            "parent_index": parent_index,
                        },
                    )
                )

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

            # 切分父chunk
            parent_texts = self._split_parent_chunks(text)

            for parent_idx, parent_text in enumerate(parent_texts):
                # 创建父chunk文档
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

                # 为父chunk创建子chunk
                child_docs = self.split_child_chunks_for_parent(
                    parent_text, doc.metadata, parent_idx
                )
                for child_idx, child_doc in enumerate(child_docs):
                    child_metadata = {**child_doc.metadata, **{
                        "chunk_type": "child",
                        "split_strategy": (
                            self.split_strategy if self.split_strategy else "simple"
                        ),
                        "parent_index": parent_idx,
                        "child_index": child_idx,
                        "chunk_id": len(split_docs),
                    }}
                    child_doc.metadata = self._sanitize_metadata(child_metadata)
                    split_docs.append(child_doc)

        return split_docs

    def _split_documents_structured(self, documents: List[Document]) -> List[Document]:
        """
        结构化分割文档：按表格、公式、章节进行智能分割
        """
        split_docs = []

        for doc in documents:
            # 检查是否有表格信息（来自结构化加载）
            tables = doc.metadata.get("_tables", [])
            raw_text = doc.metadata.get("_raw_text", doc.page_content)

            if tables:
                # 有表格，使用结构化分割
                chunks = self._split_with_tables(raw_text, tables, doc.metadata)
            else:
                # 无表格，使用基于章节和公式的分割
                chunks = self._split_text_structured(raw_text, doc.metadata)

            # 添加到结果列表
            for chunk in chunks:
                chunk.metadata.update(
                    {"split_strategy": "structured", "chunk_id": len(split_docs)}
                )
                chunk.metadata = self._sanitize_metadata(chunk.metadata)
                split_docs.append(chunk)

        return split_docs

    def _split_with_tables(
        self, text: str, tables: List, base_metadata: Dict
    ) -> List[Document]:
        """
        处理包含表格的文档分割
        """
        chunks = []
        text_parts = []

        # 识别章节
        sections = self._identify_sections(text)

        # 将表格转换为Markdown格式
        table_texts = []
        for i, table in enumerate(tables):
            if table:
                table_md = self._table_to_markdown(table)
                table_texts.append(
                    {
                        "index": i,
                        "text": table_md,
                        "marker": f"表{i+1}",  # 用于在文本中定位
                    }
                )

        # 按章节和表格位置分割文本
        current_section = None
        current_text = []
        table_index = 0

        lines = text.split("\n")
        for line in lines:
            # 检查是否是章节标题
            section_match = re.match(settings.STRUCTURED_SECTION_PATTERN, line.strip())
            if section_match:
                # 保存当前部分
                if current_text:
                    text_content = "\n".join(current_text)
                    if text_content.strip():
                        chunks.append(
                            Document(
                                page_content=text_content,
                                metadata={
                                    **base_metadata,
                                    "content_type": "text",
                                    "section": current_section,
                                },
                            )
                        )
                current_section = line.strip()
                current_text = [line]
                continue

            # 检查是否包含表格标记
            table_found = False
            for table_info in table_texts:
                if table_info["marker"] in line or f"表{table_info['index']+1}" in line:
                    # 保存当前文本
                    if current_text:
                        text_content = "\n".join(current_text)
                        if text_content.strip():
                            chunks.append(
                                Document(
                                    page_content=text_content,
                                    metadata={
                                        **base_metadata,
                                        "content_type": "text",
                                        "section": current_section,
                                    },
                                )
                            )

                    # 添加表格标题行
                    table_title = line.strip()

                    # 添加表格块
                    table_content = f"{table_title}\n{table_info['text']}"
                    chunks.append(
                        Document(
                            page_content=table_content,
                            metadata={
                                **base_metadata,
                                "content_type": "table",
                                "table_id": table_info["index"] + 1,
                                "section": current_section,
                            },
                        )
                    )

                    current_text = []
                    table_found = True
                    break

            if not table_found:
                current_text.append(line)

        # 保存最后一部分
        if current_text:
            text_content = "\n".join(current_text)
            if text_content.strip():
                chunks.append(
                    Document(
                        page_content=text_content,
                        metadata={
                            **base_metadata,
                            "content_type": "text",
                            "section": current_section,
                        },
                    )
                )

        # 如果表格没有被插入，单独添加所有表格
        if not any(chunk.metadata.get("content_type") == "table" for chunk in chunks):
            for table_info in table_texts:
                chunks.append(
                    Document(
                        page_content=table_info["text"],
                        metadata={
                            **base_metadata,
                            "content_type": "table",
                            "table_id": table_info["index"] + 1,
                        },
                    )
                )

        # 对文本块进行进一步分割（如果太大）
        final_chunks = []
        for chunk in chunks:
            if chunk.metadata.get("content_type") == "table":
                # 表格保持完整
                final_chunks.append(chunk)
            else:
                # 文本块如果太大，进行分割
                text = chunk.page_content
                if len(text) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                    # 使用句子分割
                    text_chunks = self._split_large_text(
                        text,
                        chunk.metadata,
                        settings.STRUCTURED_TEXT_CHUNK_SIZE,
                        settings.STRUCTURED_TEXT_CHUNK_OVERLAP,
                    )
                    final_chunks.extend(text_chunks)
                else:
                    final_chunks.append(chunk)

        return final_chunks

    def _split_text_structured(self, text: str, base_metadata: Dict) -> List[Document]:
        """
        对不包含表格的文本进行结构化分割（识别章节和公式）
        """
        chunks = []
        sections = self._identify_sections(text)

        # 按章节分割
        if sections:
            for i, (section_title, section_text) in enumerate(sections):
                # 检查是否包含公式
                if self._contains_formula(section_text):
                    # 公式区域：保持公式+上下文
                    formula_chunks = self._split_formula_section(
                        section_text, base_metadata, section_title
                    )
                    chunks.extend(formula_chunks)
                else:
                    # 普通文本：按大小分割
                    if len(section_text) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                        text_chunks = self._split_large_text(
                            section_text,
                            {**base_metadata, "section": section_title},
                            settings.STRUCTURED_TEXT_CHUNK_SIZE,
                            settings.STRUCTURED_TEXT_CHUNK_OVERLAP,
                        )
                        chunks.extend(text_chunks)
                    else:
                        chunks.append(
                            Document(
                                page_content=section_text,
                                metadata={
                                    **base_metadata,
                                    "content_type": "text",
                                    "section": section_title,
                                },
                            )
                        )
        else:
            # 没有章节，整体处理
            if len(text) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                text_chunks = self._split_large_text(
                    text,
                    base_metadata,
                    settings.STRUCTURED_TEXT_CHUNK_SIZE,
                    settings.STRUCTURED_TEXT_CHUNK_OVERLAP,
                )
                chunks.extend(text_chunks)
            else:
                chunks.append(
                    Document(
                        page_content=text,
                        metadata={**base_metadata, "content_type": "text"},
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
            # 匹配章节标题（如 "1 范围"、"2 化学名称"）
            match = re.match(settings.STRUCTURED_SECTION_PATTERN, line.strip())
            if match:
                # 保存上一章节
                if current_section and current_content:
                    sections.append((current_section, "\n".join(current_content)))
                # 开始新章节
                current_section = line.strip()
                current_content = [line]
            else:
                current_content.append(line)

        # 保存最后一章
        if current_section and current_content:
            sections.append((current_section, "\n".join(current_content)))

        # 如果没有找到章节，返回整个文本作为一个章节
        if not sections:
            sections.append((None, text))

        return sections

    def _contains_formula(self, text: str) -> bool:
        """检测文本是否包含公式/结构式"""
        # 检测化学结构式特征
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
                # 遇到公式，保存之前的上下文
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

                # 公式+上下文
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

                # 如果当前块太大，保存它
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

        # 保存最后一部分
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
                # 保存当前块
                chunks.append(
                    Document(
                        page_content="\n".join(current_chunk),
                        metadata=base_metadata.copy(),
                    )
                )

                # 开始新块，保留重叠部分
                overlap_text = (
                    "\n".join(current_chunk[-overlap // 50 :]) if current_chunk else ""
                )
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_length = len("\n".join(current_chunk))
            else:
                current_chunk.append(sentence)
                current_length += sentence_length + 1  # +1 for newline

        # 保存最后一块
        if current_chunk:
            chunks.append(
                Document(
                    page_content="\n".join(current_chunk), metadata=base_metadata.copy()
                )
            )

        return (
            chunks if chunks else [Document(page_content=text, metadata=base_metadata)]
        )

    def _table_to_markdown(self, table: List[List]) -> str:
        """将表格转换为Markdown格式"""
        if not table or not table[0]:
            return ""

        md_lines = []

        # 表头
        header = table[0]
        md_lines.append(
            "| " + " | ".join(str(cell) if cell else "" for cell in header) + " |"
        )
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")

        # 数据行
        for row in table[1:]:
            md_lines.append(
                "| " + " | ".join(str(cell) if cell else "" for cell in row) + " |"
            )

        return "\n".join(md_lines)

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
