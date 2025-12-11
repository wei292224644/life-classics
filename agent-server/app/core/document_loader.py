"""
文档加载和处理模块
"""
import os
from typing import List
from pathlib import Path
from llama_index.core import Document
from llama_index.core.node_parser import SimpleNodeParser
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
from app.core.config import settings


class DocumentLoader:
    """文档加载器"""
    
    def __init__(self):
        """初始化文档加载器"""
        self.node_parser = SimpleNodeParser.from_defaults(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
    
    def load_file(self, file_path: str) -> List[Document]:
        """加载单个文件"""
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        if file_ext not in settings.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
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
        """将文档分割成更小的块"""
        nodes = self.node_parser.get_nodes_from_documents(documents)
        # 将节点转换回文档格式
        split_docs = []
        for node in nodes:
            doc = Document(
                text=node.text,
                metadata=node.metadata
            )
            split_docs.append(doc)
        return split_docs


# 全局文档加载器实例
document_loader = DocumentLoader()

