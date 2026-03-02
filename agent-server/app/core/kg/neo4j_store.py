"""
Neo4j 存储：写入 Document、Chunk 节点及 CONTAINS 关系。
"""

import json
import logging
from typing import List, Optional

import neo4j
from app.core.config import settings
from app.core.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


def _get_driver():
    return neo4j.GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


def write_document_chunks(
    doc_id: str,
    doc_title: str,
    chunks: List[DocumentChunk],
    source: Optional[str] = None,
) -> None:
    """
    将文档及其 chunks 写入 Neo4j（Document -[:CONTAINS]-> Chunk）。

    Args:
        doc_id: 文档 ID
        doc_title: 文档标题
        chunks: 文档块列表
        source: 来源标识（可选）
    """
    driver = _get_driver()
    try:
        with driver.session() as session:
            # 先删除该文档下已有 Chunk 关系及 Chunk 节点，再创建（与 Chroma 重导一致）
            session.run(
                """
                MATCH (d:Document {doc_id: $doc_id})
                OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
                DETACH DELETE c
                """,
                doc_id=doc_id,
            )
            session.run(
                """
                MERGE (d:Document {doc_id: $doc_id})
                ON CREATE SET d.doc_title = $doc_title, d.source = $source, d.created_at = datetime()
                ON MATCH SET d.doc_title = $doc_title, d.source = $source
                """,
                doc_id=doc_id,
                doc_title=doc_title or "",
                source=source or "",
            )
            for i, ch in enumerate(chunks):
                chunk_id = f"{doc_id}_{i}"
                content_type = (
                    ch.content_type.value
                    if hasattr(ch.content_type, "value")
                    else str(ch.content_type)
                )
                section_path_json = json.dumps(
                    ch.section_path if ch.section_path else [], ensure_ascii=False
                )
                content_preview = (
                    (ch.content[:200] + "…")
                    if isinstance(ch.content, str) and len(ch.content) > 200
                    else (str(ch.content)[:200] if ch.content else "")
                )
                session.run(
                    """
                    MERGE (c:Chunk {chunk_id: $chunk_id})
                    ON CREATE SET c.doc_id = $doc_id, c.content_type = $content_type,
                                  c.section_path = $section_path, c.content_preview = $content_preview
                    ON MATCH SET c.doc_id = $doc_id, c.content_type = $content_type,
                                c.section_path = $section_path, c.content_preview = $content_preview
                    WITH c
                    MATCH (d:Document {doc_id: $doc_id})
                    MERGE (d)-[:CONTAINS]->(c)
                    """,
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content_type=content_type,
                    section_path=section_path_json,
                    content_preview=content_preview,
                )
    finally:
        driver.close()


def write_document_chunks_safe(
    doc_id: str,
    doc_title: str,
    chunks: List[DocumentChunk],
    source: Optional[str] = None,
) -> None:
    """同 write_document_chunks，失败时仅打日志，不阻断调用方。"""
    try:
        write_document_chunks(doc_id, doc_title, chunks, source=source)
    except Exception as e:
        logger.warning("Neo4j write_document_chunks failed: %s", e, exc_info=True)
