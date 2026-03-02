"""
知识图谱模块：Neo4j 文档/块存储与查询。
"""

from app.core.kg.neo4j_store import write_document_chunks, write_document_chunks_safe

__all__ = ["write_document_chunks", "write_document_chunks_safe"]
