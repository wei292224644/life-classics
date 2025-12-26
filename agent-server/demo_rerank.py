#!/usr/bin/env python3
"""
Demo: 演示 Rerank 重排序功能

功能：
1. 从向量库检索文档
2. 使用 Rerank 对检索结果进行重排序
3. 输出最相关的几条 chunk
"""

import sys
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from app.core.kb.vector_store.vector_store import VectorStore
from app.core.kb.vector_store.rerank import rerank_documents, RerankedChunk
from app.core.document_chunk import DocumentChunk, ContentType
import json


def load_chunks_from_json(json_file: str) -> List[dict]:
    """从 JSON 文件加载 chunks"""
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def json_to_document_chunk(chunk_dict: dict) -> DocumentChunk:
    """将 JSON chunk 转换为 DocumentChunk"""
    try:
        content_type = ContentType(chunk_dict.get("content_type", "note"))
    except ValueError:
        content_type = ContentType.NOTE

    return DocumentChunk(
        doc_id=chunk_dict.get("doc_id", ""),
        doc_title=chunk_dict.get("doc_title", ""),
        section_path=chunk_dict.get("section_path", []),
        content_type=content_type,
        content=chunk_dict.get("content", ""),
        meta=chunk_dict.get("meta", {}),
    )


def format_chunk_info(chunk: RerankedChunk, index: int) -> str:
    """格式化 chunk 信息用于显示"""
    doc = chunk.document
    metadata = doc.metadata or {}
    
    section_path = metadata.get("section_path", [])
    section_path_str = " > ".join(section_path) if section_path else "根目录"
    content_type = metadata.get("content_type", "unknown")
    
    content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
    
    return f"""
[结果 {index + 1}] 相关性分数: {chunk.relevance_score:.3f}
评分理由: {chunk.relevance_reason}
章节路径: {section_path_str}
内容类型: {content_type}
内容预览: {content_preview}
{'='*60}"""


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("使用方法:")
        print("  python demo_rerank.py <JSON文件路径> <查询问题> [top_k] [use_llm]")
        print("\n参数说明:")
        print("  JSON文件路径: chunks 的 JSON 文件")
        print("  查询问题: 要查询的问题")
        print("  top_k: 返回前 k 个结果（默认 5）")
        print("  use_llm: 是否使用 LLM 重排序，true/false（默认 true）")
        print("\n示例:")
        print("  python demo_rerank.py 20120518_10_analysis_chunks.json 'β-胡萝卜素含量是多少？' 5 true")
        sys.exit(1)

    json_file = sys.argv[1]
    query = sys.argv[2]
    top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    use_llm = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else True

    json_path = Path(json_file)
    if not json_path.exists():
        print(f"错误: 文件不存在: {json_file}")
        sys.exit(1)

    print("=" * 60)
    print("Rerank 重排序 Demo")
    print("=" * 60)
    print(f"查询问题: {query}")
    print(f"返回前 {top_k} 个结果")
    print(f"使用 LLM 重排序: {use_llm}")
    print("=" * 60)
    print()

    # 加载 chunks
    try:
        print(f"正在加载 JSON 文件: {json_path.name}...")
        chunks_data = load_chunks_from_json(str(json_path))
        chunks = [json_to_document_chunk(chunk_dict) for chunk_dict in chunks_data]
        print(f"✓ 成功加载 {len(chunks)} 个 chunks\n")
    except Exception as e:
        print(f"✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 初始化向量存储
    try:
        print("正在初始化向量存储...")
        vector_store = VectorStore()
        print("✓ 向量存储初始化成功\n")
    except Exception as e:
        print(f"✗ 向量存储初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 添加 chunks 到向量库（如果还没有添加）
    try:
        print("正在添加 chunks 到向量库...")
        # 注意：这里假设向量库是空的，实际使用时可能需要检查是否已存在
        vector_store.add_chunks(chunks)
        print("✓ Chunks 添加成功\n")
    except Exception as e:
        print(f"⚠ 添加 chunks 时出现警告（可能已存在）: {e}\n")

    # 执行检索
    try:
        print(f"正在检索相关内容（top_k={top_k * 2}）...")
        # 先检索更多结果，然后进行重排序
        retrieved_docs = vector_store.search(query, top_k=top_k * 2)
        print(f"✓ 检索到 {len(retrieved_docs)} 个文档\n")
    except Exception as e:
        print(f"✗ 检索失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not retrieved_docs:
        print("未检索到相关文档")
        sys.exit(0)

    # 执行重排序
    try:
        print(f"正在使用 {'LLM' if use_llm else '简单方法'} 进行重排序...")
        reranked_chunks = rerank_documents(
            query=query,
            documents=retrieved_docs,
            top_k=top_k,
            use_llm=use_llm,
        )
        print(f"✓ 重排序完成，返回 {len(reranked_chunks)} 个最相关的结果\n")
    except Exception as e:
        print(f"✗ 重排序失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 输出结果
    print("=" * 60)
    print("重排序结果（按相关性从高到低）:")
    print("=" * 60)
    
    for i, chunk in enumerate(reranked_chunks):
        print(format_chunk_info(chunk, i))
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

