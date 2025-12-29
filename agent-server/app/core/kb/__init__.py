import time
from typing import List
from pathlib import Path
from app.core.document_chunk import ContentType, DocumentChunk
from app.core.kb.imports.import_pdf import import_pdf
from app.core.kb.imports.import_markdown import import_markdown
from app.core.kb.imports.import_text import import_text
from app.core.kb.pre_parse.ocr_step import ocr_step
from app.core.kb.pre_parse.convert_to_structured import convert_to_structured
from app.core.kb.strategy.structured_strategy import split_structured
from app.core.kb.strategy.text_strategy import split_text
from app.core.kb.vector_store import vector_store_manager


def split_step(documents: List[DocumentChunk], strategy: str) -> List[DocumentChunk]:
    if strategy == "structured":
        return split_structured(documents)
    else:
        return split_text(documents)


def import_file_step(
    file_path: str, strategy: str, original_filename: str = None, **kwargs
) -> List[DocumentChunk]:
    """
    导入文件（支持多种格式）

    Args:
        file_path: 文件路径
        strategy: 切分策略
        original_filename: 原始文件名（如果提供，将使用此文件名作为 doc_id 和 doc_title）
        **kwargs: 其他参数（chunk_size, chunk_overlap 等）

    Returns:
        DocumentChunk 列表
    """
    file_ext = Path(file_path).suffix.lower()

    print("=" * 20)
    start_time = time.time()
    print("start import file step:")
    print(f"file_path: {file_path}")
    print(f"original_filename: {original_filename}")
    print(f"strategy: {strategy}")
    print(f"kwargs: {kwargs}")
    print("=" * 20)

    # 如果没有提供原始文件名，使用文件路径中的文件名
    if original_filename is None:
        original_filename = Path(file_path).name

    # 根据文件类型选择导入函数
    if file_ext == ".pdf":
        documents = import_pdf(file_path, original_filename=original_filename)
    elif file_ext in [".md", ".markdown"]:
        documents = import_markdown(file_path, original_filename=original_filename)
    elif file_ext == ".txt":
        documents = import_text(file_path, original_filename=original_filename)
    elif file_ext == ".json":
        # JSON 导入暂未实现
        raise NotImplementedError("JSON 格式暂不支持")
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")

    if not documents:
        return []

    # pre-parse
    for i, document in enumerate(documents):
        if document.meta.get("IMAGE_OCR_RESULT", False):
            documents[i] = ocr_step(document)

        if strategy == "structured":
            documents[i] = convert_to_structured(document)

    # strategy
    documents = split_step(documents, strategy)

    # vector store
    vector_store_manager.add_chunks(documents)

    end_time = time.time()
    print("=" * 20)
    print("end import file step:")
    print(f"documents: {len(documents)}")
    print(f"time: {end_time - start_time} seconds")
    print("=" * 20)
    return documents


def import_pdf_step(file_path: str, strategy: str, **kwargs) -> List[DocumentChunk]:
    """导入 PDF 文件（向后兼容）"""
    return import_file_step(file_path, strategy, **kwargs)


if __name__ == "__main__":
    documents = import_markdown("markdown_cache/GB5009.263-2016.md")
    documents = split_step(documents, "structured")
    vector_store_manager.add_chunks(documents)
