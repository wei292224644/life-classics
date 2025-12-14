"""
文档加载和处理模块 - 支持多种分割策略，特别优化表格和公式处理
"""
import os
import re
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from llama_index.core import Document
from llama_index.core.node_parser import (
    SimpleNodeParser,
    SentenceSplitter,
    MarkdownNodeParser,
    HierarchicalNodeParser,
)
try:
    from llama_index.core.node_parser import SemanticSplitterNodeParser
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
try:
    from llama_index.readers.file import PDFReader, MarkdownReader
    from llama_index.readers.file.docs_reader import DocxReader
except ImportError:
    # 兼容不同版本的导入路径
    try:
        from llama_index.core.readers import SimpleDirectoryReader
        PDFReader = None
        MarkdownReader = None
        DocxReader = None
    except ImportError:
        SimpleDirectoryReader = None
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
from app.core.config import settings
from app.core.embeddings import get_embedding_model


class DocumentLoader:
    """文档加载器 - 支持多种分割策略"""
    
    def __init__(self, split_strategy: Optional[str] = None):
        """
        初始化文档加载器
        
        Args:
            split_strategy: 分割策略，可选值:
                - "simple": 固定大小分割（默认，适合一般文档）
                - "semantic": 语义分割（推荐用于包含表格和公式的PDF）
                - "sentence": 按句子分割（保持句子完整性）
                - "markdown": Markdown格式分割（按标题分割）
                - "hybrid": 混合策略（结合多种方法）
                - "structured": 结构化分割（推荐用于包含表格和公式的PDF，使用pdfplumber）
        """
        self.split_strategy = split_strategy or settings.SPLIT_STRATEGY
        self.node_parser = self._create_node_parser()
    
    def _create_node_parser(self):
        """根据策略创建对应的节点解析器"""
        if self.split_strategy == "simple":
            return SimpleNodeParser.from_defaults(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )
        
        elif self.split_strategy == "semantic":
            # 语义分割：基于语义相似度，能更好地保持表格和公式的完整性
            if not SEMANTIC_AVAILABLE:
                print("警告: SemanticSplitterNodeParser 不可用，回退到 SimpleNodeParser")
                return SimpleNodeParser.from_defaults(
                    chunk_size=settings.SEMANTIC_CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP
                )
            try:
                embedding_model = get_embedding_model()
                return SemanticSplitterNodeParser(
                    buffer_size=1,
                    similarity_cutoff=settings.SEMANTIC_SIMILARITY_THRESHOLD,
                    embed_model=embedding_model
                )
            except Exception as e:
                print(f"警告: 无法创建语义分割器 ({e})，回退到 SimpleNodeParser")
                return SimpleNodeParser.from_defaults(
                    chunk_size=settings.SEMANTIC_CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP
                )
        
        elif self.split_strategy == "sentence":
            # 按句子分割：保持句子完整性，适合包含公式的文档
            return SentenceSplitter(
                chunk_size=settings.SENTENCE_CHUNK_SIZE,
                chunk_overlap=settings.SENTENCE_CHUNK_OVERLAP,
                separator=" "  # 空格分隔，保持句子结构
            )
        
        elif self.split_strategy == "markdown":
            # Markdown分割：按标题层级分割
            return MarkdownNodeParser.from_defaults()
        
        elif self.split_strategy == "hybrid":
            # 混合策略：优先使用语义分割，失败时回退到句子分割
            if SEMANTIC_AVAILABLE:
                try:
                    embedding_model = get_embedding_model()
                    return SemanticSplitterNodeParser(
                        buffer_size=1,
                        similarity_cutoff=settings.SEMANTIC_SIMILARITY_THRESHOLD,
                        embed_model=embedding_model
                    )
                except Exception:
                    pass
            return SentenceSplitter(
                chunk_size=settings.SENTENCE_CHUNK_SIZE,
                chunk_overlap=settings.SENTENCE_CHUNK_OVERLAP
            )
        
        elif self.split_strategy == "structured":
            # 结构化分割：不使用node_parser，在split_documents中特殊处理
            # 这里返回None，split_documents会检测并使用结构化分割
            return None
        
        else:
            print(f"警告: 未知的分割策略 '{self.split_strategy}'，使用默认 SimpleNodeParser")
            return SimpleNodeParser.from_defaults(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )
    
    def load_file(self, file_path: str) -> List[Document]:
        """加载单个文件"""
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        if file_ext not in settings.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
        # 对于PDF且使用structured策略，使用结构化加载
        if file_ext == ".pdf" and self.split_strategy == "structured":
            if not PDFPLUMBER_AVAILABLE:
                print("警告: pdfplumber 未安装，无法使用结构化加载，回退到普通PDF加载")
                return self._load_pdf_fallback(file_path, file_path_obj)
            return self._load_pdf_structured(file_path, file_path_obj)
        
        # 根据文件类型选择对应的加载器
        if file_ext == ".txt":
            # 文本文件直接读取
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return [Document(text=content, metadata={"file_name": file_path_obj.name})]
        elif PDFReader and file_ext == ".pdf":
            loader = PDFReader()
            documents = loader.load_data(file=file_path)
        elif MarkdownReader and file_ext == ".md":
            loader = MarkdownReader()
            documents = loader.load_data(file=file_path)
        elif DocxReader and file_ext == ".docx":
            loader = DocxReader()
            documents = loader.load_data(file=file_path)
        elif SimpleDirectoryReader:
            # 使用SimpleDirectoryReader作为后备方案
            loader = SimpleDirectoryReader(input_files=[file_path])
            documents = loader.load_data()
        else:
            raise ValueError(f"未实现的文件类型加载器: {file_ext}，请安装相应的读取器包")
        
        # 添加文件元数据
        for doc in documents:
            doc.metadata["file_name"] = file_path_obj.name
            doc.metadata["file_path"] = str(file_path_obj)
            doc.metadata["file_type"] = file_ext
        
        return documents
    
    def _load_pdf_fallback(self, file_path: str, file_path_obj: Path) -> List[Document]:
        """PDF加载的后备方案"""
        if PDFReader:
            loader = PDFReader()
            documents = loader.load_data(file=file_path)
        elif SimpleDirectoryReader:
            loader = SimpleDirectoryReader(input_files=[file_path])
            documents = loader.load_data()
        else:
            raise ValueError("无法加载PDF文件，请安装相应的读取器包")
        
        for doc in documents:
            doc.metadata["file_name"] = file_path_obj.name
            doc.metadata["file_path"] = str(file_path_obj)
            doc.metadata["file_type"] = ".pdf"
        
        return documents
    
    def _load_pdf_structured(self, file_path: str, file_path_obj: Path) -> List[Document]:
        """
        使用pdfplumber结构化加载PDF，提取表格、识别章节和公式
        """
        documents = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取文本
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # 提取表格
                    tables = page.extract_tables()
                    
                    # 创建页面文档，包含表格信息
                    page_doc = Document(
                        text=text,
                        metadata={
                            "file_name": file_path_obj.name,
                            "file_path": str(file_path_obj),
                            "file_type": ".pdf",
                            "page_number": page_num,
                            "table_count": len(tables),
                            "_tables": tables,  # 内部使用，用于后续分割
                            "_raw_text": text  # 保留原始文本
                        }
                    )
                    documents.append(page_doc)
        except Exception as e:
            print(f"结构化加载PDF失败 {file_path}: {e}")
            return self._load_pdf_fallback(file_path, file_path_obj)
        
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
        
        如果启用父子chunk模式，使用HierarchicalNodeParser生成父子节点结构
        """
        # 如果启用父子chunk模式，使用HierarchicalNodeParser
        if settings.ENABLE_PARENT_CHILD:
            return self._split_with_hierarchical(documents)
        
        # 原有逻辑
        if self.split_strategy == "structured":
            split_docs = self._split_documents_structured(documents)
        else:
            if self.node_parser is None:
                raise ValueError(f"分割策略 '{self.split_strategy}' 需要node_parser，但未创建")
            
            nodes = self.node_parser.get_nodes_from_documents(documents)
            split_docs = []
            for node in nodes:
                doc = Document(
                    text=node.text,
                    metadata={
                        **node.metadata,
                        "split_strategy": self.split_strategy,
                        "chunk_id": len(split_docs)
                    }
                )
                split_docs.append(doc)
        
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
    
    def _split_with_hierarchical(self, documents: List[Document]) -> List[Document]:
        """
        使用HierarchicalNodeParser生成父子节点结构
        
        注意：这里返回的是Document格式，但实际存储时会在vector_store中
        重新解析为Node以建立父子关系
        """
        # 在解析前清理文档的metadata，避免metadata过大
        cleaned_documents = []
        for doc in documents:
            # 只保留必要的metadata
            essential_metadata = {}
            for key in ['file_name', 'file_path', 'file_type', 'page_number']:
                if key in doc.metadata:
                    value = doc.metadata[key]
                    if isinstance(value, (str, int, float, type(None))):
                        essential_metadata[key] = value
            
            # 创建清理后的文档
            cleaned_doc = Document(
                text=doc.text,
                metadata=essential_metadata
            )
            cleaned_documents.append(cleaned_doc)
        
        # 创建HierarchicalNodeParser
        hierarchical_parser = HierarchicalNodeParser.from_defaults(
            chunk_sizes=[
                settings.PARENT_CHUNK_SIZE,  # 父chunk大小
                settings.CHILD_CHUNK_SIZE,    # 子chunk大小
            ]
        )
        
        # 生成节点（包含父子关系）
        nodes = hierarchical_parser.get_nodes_from_documents(cleaned_documents)
        
        # 转换为Document格式，只保留必要的metadata
        split_docs = []
        for node in nodes:
            # 只保留必要的metadata，避免metadata过大
            essential_metadata = {}
            
            # 保留文件基本信息
            for key in ['file_name', 'file_path', 'file_type', 'page_number']:
                if key in node.metadata:
                    value = node.metadata[key]
                    if isinstance(value, (str, int, float, type(None))):
                        essential_metadata[key] = value
            
            # 保留内容类型信息（如果有）
            if 'content_type' in node.metadata:
                essential_metadata['content_type'] = node.metadata['content_type']
            if 'section' in node.metadata:
                section = node.metadata['section']
                # 限制section长度
                if isinstance(section, str) and len(section) > 100:
                    essential_metadata['section'] = section[:100]
                else:
                    essential_metadata['section'] = section
            
            doc = Document(
                text=node.text,
                metadata={
                    **essential_metadata,
                    "split_strategy": "hierarchical",
                    "chunk_id": len(split_docs)
                }
            )
            split_docs.append(doc)
        
        return split_docs
    
    def _split_documents_structured(self, documents: List[Document]) -> List[Document]:
        """
        结构化分割文档：按表格、公式、章节进行智能分割
        """
        split_docs = []
        
        for doc in documents:
            # 检查是否有表格信息（来自结构化加载）
            tables = doc.metadata.get("_tables", [])
            raw_text = doc.metadata.get("_raw_text", doc.text)
            
            if tables:
                # 有表格，使用结构化分割
                chunks = self._split_with_tables(raw_text, tables, doc.metadata)
            else:
                # 无表格，使用基于章节和公式的分割
                chunks = self._split_text_structured(raw_text, doc.metadata)
            
            # 添加到结果列表
            for chunk in chunks:
                chunk.metadata.update({
                    "split_strategy": "structured",
                    "chunk_id": len(split_docs)
                })
                split_docs.append(chunk)
        
        return split_docs
    
    def _split_with_tables(self, text: str, tables: List, base_metadata: Dict) -> List[Document]:
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
                table_texts.append({
                    "index": i,
                    "text": table_md,
                    "marker": f"表{i+1}"  # 用于在文本中定位
                })
        
        # 按章节和表格位置分割文本
        current_section = None
        current_text = []
        table_index = 0
        
        lines = text.split('\n')
        for line in lines:
            # 检查是否是章节标题
            section_match = re.match(settings.STRUCTURED_SECTION_PATTERN, line.strip())
            if section_match:
                # 保存当前部分
                if current_text:
                    text_content = '\n'.join(current_text)
                    if text_content.strip():
                        chunks.append(Document(
                            text=text_content,
                            metadata={
                                **base_metadata,
                                "content_type": "text",
                                "section": current_section
                            }
                        ))
                current_section = line.strip()
                current_text = [line]
                continue
            
            # 检查是否包含表格标记（简化处理，实际可能需要更复杂的定位）
            # 这里我们假设表格在文本中会有"表1"、"表2"等标记
            table_found = False
            for table_info in table_texts:
                if table_info["marker"] in line or f"表{table_info['index']+1}" in line:
                    # 保存当前文本
                    if current_text:
                        text_content = '\n'.join(current_text)
                        if text_content.strip():
                            chunks.append(Document(
                                text=text_content,
                                metadata={
                                    **base_metadata,
                                    "content_type": "text",
                                    "section": current_section
                                }
                            ))
                    
                    # 添加表格标题行
                    table_title = line.strip()
                    
                    # 添加表格块
                    table_content = f"{table_title}\n{table_info['text']}"
                    chunks.append(Document(
                        text=table_content,
                        metadata={
                            **base_metadata,
                            "content_type": "table",
                            "table_id": table_info['index'] + 1,
                            "section": current_section
                        }
                    ))
                    
                    current_text = []
                    table_found = True
                    break
            
            if not table_found:
                current_text.append(line)
        
        # 保存最后一部分
        if current_text:
            text_content = '\n'.join(current_text)
            if text_content.strip():
                chunks.append(Document(
                    text=text_content,
                    metadata={
                        **base_metadata,
                        "content_type": "text",
                        "section": current_section
                    }
                ))
        
        # 如果表格没有被插入（可能文本中没有表格标记），单独添加所有表格
        if not any(chunk.metadata.get("content_type") == "table" for chunk in chunks):
            for table_info in table_texts:
                chunks.append(Document(
                    text=table_info['text'],
                    metadata={
                        **base_metadata,
                        "content_type": "table",
                        "table_id": table_info['index'] + 1
                    }
                ))
        
        # 对文本块进行进一步分割（如果太大）
        final_chunks = []
        for chunk in chunks:
            if chunk.metadata.get("content_type") == "table":
                # 表格保持完整
                final_chunks.append(chunk)
            else:
                # 文本块如果太大，进行分割
                text = chunk.text
                if len(text) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                    # 使用句子分割
                    text_chunks = self._split_large_text(
                        text,
                        chunk.metadata,
                        settings.STRUCTURED_TEXT_CHUNK_SIZE,
                        settings.STRUCTURED_TEXT_CHUNK_OVERLAP
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
                        section_text,
                        base_metadata,
                        section_title
                    )
                    chunks.extend(formula_chunks)
                else:
                    # 普通文本：按大小分割
                    if len(section_text) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                        text_chunks = self._split_large_text(
                            section_text,
                            {**base_metadata, "section": section_title},
                            settings.STRUCTURED_TEXT_CHUNK_SIZE,
                            settings.STRUCTURED_TEXT_CHUNK_OVERLAP
                        )
                        chunks.extend(text_chunks)
                    else:
                        chunks.append(Document(
                            text=section_text,
                            metadata={
                                **base_metadata,
                                "content_type": "text",
                                "section": section_title
                            }
                        ))
        else:
            # 没有章节，整体处理
            if len(text) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                text_chunks = self._split_large_text(
                    text,
                    base_metadata,
                    settings.STRUCTURED_TEXT_CHUNK_SIZE,
                    settings.STRUCTURED_TEXT_CHUNK_OVERLAP
                )
                chunks.extend(text_chunks)
            else:
                chunks.append(Document(
                    text=text,
                    metadata={
                        **base_metadata,
                        "content_type": "text"
                    }
                ))
        
        return chunks
    
    def _identify_sections(self, text: str) -> List[Tuple[str, str]]:
        """识别文档章节"""
        sections = []
        lines = text.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # 匹配章节标题（如 "1 范围"、"2 化学名称"）
            match = re.match(settings.STRUCTURED_SECTION_PATTERN, line.strip())
            if match:
                # 保存上一章节
                if current_section and current_content:
                    sections.append((current_section, '\n'.join(current_content)))
                # 开始新章节
                current_section = line.strip()
                current_content = [line]
            else:
                current_content.append(line)
        
        # 保存最后一章
        if current_section and current_content:
            sections.append((current_section, '\n'.join(current_content)))
        
        # 如果没有找到章节，返回整个文本作为一个章节
        if not sections:
            sections.append((None, text))
        
        return sections
    
    def _contains_formula(self, text: str) -> bool:
        """检测文本是否包含公式/结构式"""
        # 检测化学结构式特征
        formula_patterns = [
            r'[A-Z][a-z]?\d*[A-Z]?[a-z]?\d*',  # 化学式如 C6H12O6
            r'[=+\-*/^∑∫√]',  # 数学符号
            r'\\frac|\\sqrt|\\sum',  # LaTeX公式
            r'[HO]\s*[CN]',  # 化学结构式片段
            r'\([A-Z][a-z]?\d*\)',  # 带括号的化学式
        ]
        for pattern in formula_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _split_formula_section(self, text: str, base_metadata: Dict, section: Optional[str]) -> List[Document]:
        """分割包含公式的章节，保持公式+上下文"""
        chunks = []
        sentences = re.split(r'[。！？\n]', text)
        
        current_chunk = []
        formula_context = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if self._contains_formula(sentence):
                # 遇到公式，保存之前的上下文
                if current_chunk:
                    chunks.append(Document(
                        text='\n'.join(current_chunk),
                        metadata={
                            **base_metadata,
                            "content_type": "text",
                            "section": section
                        }
                    ))
                    current_chunk = []
                
                # 公式+上下文
                # 添加上下文（保留最近的N个句子）
                context_count = min(settings.STRUCTURED_FORMULA_CONTEXT, len(formula_context))
                context_sentences = formula_context[-context_count:] + [sentence] if formula_context else [sentence]
                
                chunks.append(Document(
                    text='\n'.join(context_sentences),
                    metadata={
                        **base_metadata,
                        "content_type": "formula",
                        "section": section
                    }
                ))
                formula_context = []
            else:
                current_chunk.append(sentence)
                formula_context.append(sentence)
                
                # 如果当前块太大，保存它
                if len('\n'.join(current_chunk)) > settings.STRUCTURED_TEXT_CHUNK_SIZE:
                    chunks.append(Document(
                        text='\n'.join(current_chunk),
                        metadata={
                            **base_metadata,
                            "content_type": "text",
                            "section": section
                        }
                    ))
                    current_chunk = []
        
        # 保存最后一部分
        if current_chunk:
            chunks.append(Document(
                text='\n'.join(current_chunk),
                metadata={
                    **base_metadata,
                    "content_type": "text",
                    "section": section
                }
            ))
        
        return chunks if chunks else [Document(
            text=text,
            metadata={
                **base_metadata,
                "content_type": "formula",
                "section": section
            }
        )]
    
    def _split_large_text(self, text: str, base_metadata: Dict, chunk_size: int, overlap: int) -> List[Document]:
        """将大文本分割成小块"""
        chunks = []
        sentences = re.split(r'[。！？\n]', text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                # 保存当前块
                chunks.append(Document(
                    text='\n'.join(current_chunk),
                    metadata=base_metadata.copy()
                ))
                
                # 开始新块，保留重叠部分
                overlap_text = '\n'.join(current_chunk[-overlap//50:]) if current_chunk else ""
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_length = len('\n'.join(current_chunk))
            else:
                current_chunk.append(sentence)
                current_length += sentence_length + 1  # +1 for newline
        
        # 保存最后一块
        if current_chunk:
            chunks.append(Document(
                text='\n'.join(current_chunk),
                metadata=base_metadata.copy()
            ))
        
        return chunks if chunks else [Document(text=text, metadata=base_metadata)]
    
    def _table_to_markdown(self, table: List[List]) -> str:
        """将表格转换为Markdown格式"""
        if not table or not table[0]:
            return ""
        
        md_lines = []
        
        # 表头
        header = table[0]
        md_lines.append("| " + " | ".join(str(cell) if cell else "" for cell in header) + " |")
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")
        
        # 数据行
        for row in table[1:]:
            md_lines.append("| " + " | ".join(str(cell) if cell else "" for cell in row) + " |")
        
        return "\n".join(md_lines)
    
    def split_documents_with_strategy(
        self, 
        documents: List[Document], 
        strategy: str
    ) -> List[Document]:
        """
        使用指定策略分割文档（临时使用，不改变实例的默认策略）
        
        Args:
            documents: 要分割的文档列表
            strategy: 分割策略名称
        """
        original_strategy = self.split_strategy
        self.split_strategy = strategy
        self.node_parser = self._create_node_parser()
        result = self.split_documents(documents)
        self.split_strategy = original_strategy
        self.node_parser = self._create_node_parser()
        return result


# 全局文档加载器实例
document_loader = DocumentLoader()

