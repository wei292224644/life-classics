from __future__ import annotations

from typing import List

from app.core.kb.clients import get_neo4j_driver
from app.core.parser_workflow.models import DocumentChunk

_BATCH_CYPHER = """
MERGE (d:Document {standard_no: $standard_no})
SET d.title = $title,
    d.doc_type = $doc_type,
    d.doc_type_source = $doc_type_source,
    d.publish_date = $publish_date,
    d.implement_date = $implement_date,
    d.status = $status,
    d.issuing_authority = $issuing_authority
WITH d
UNWIND $chunks AS chunk
CREATE (c:Chunk {
    chunk_id: chunk.chunk_id,
    content_type: chunk.content_type,
    section_path: chunk.section_path,
    content: chunk.content,
    raw_content: chunk.raw_content
})
CREATE (d)-[:HAS_CHUNK]->(c)
"""

_ONE_CYPHER = """
MERGE (d:Document {standard_no: $standard_no})
CREATE (c:Chunk {
    chunk_id: $chunk_id,
    content_type: $content_type,
    section_path: $section_path,
    content: $content,
    raw_content: $raw_content
})
CREATE (d)-[:HAS_CHUNK]->(c)
"""

_REPLACES_CYPHER = """
MERGE (d:Document {standard_no: $standard_no})
MERGE (old:Document {standard_no: $old_sn})
MERGE (d)-[:REPLACES]->(old)
"""

_DELETE_CYPHER = """
MATCH (d:Document {standard_no: $standard_no})
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
DETACH DELETE c, d
"""


async def delete_by_standard_no(standard_no: str, errors: List[str]) -> bool:
    """删除文档节点及其所有 Chunk。文档不存在视为成功。"""
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            await session.run(_DELETE_CYPHER, standard_no=standard_no)
        return True
    except Exception as e:
        errors.append(f"neo4j delete error: {e}")
        return False


async def write_batch(chunks: List[DocumentChunk], doc_metadata: dict) -> None:
    """批量写入：一次事务创建 Document 节点、所有 Chunk 节点及关系。"""
    driver = get_neo4j_driver()
    async with driver.session() as session:
        await session.run(
            _BATCH_CYPHER,
            standard_no=doc_metadata.get("standard_no", ""),
            title=doc_metadata.get("title", ""),
            doc_type=doc_metadata.get("doc_type", ""),
            doc_type_source=doc_metadata.get("doc_type_source", ""),
            publish_date=doc_metadata.get("publish_date", ""),
            implement_date=doc_metadata.get("implement_date", ""),
            status=doc_metadata.get("status", ""),
            issuing_authority=doc_metadata.get("issuing_authority", ""),
            chunks=[
                {
                    "chunk_id": c["chunk_id"],
                    "content_type": c["content_type"],
                    "section_path": c["section_path"],
                    "content": c["content"],
                    "raw_content": c["raw_content"],
                }
                for c in chunks
            ],
        )
        # 建立版本替代关系
        for old_sn in doc_metadata.get("replaces", []):
            await session.run(
                _REPLACES_CYPHER,
                standard_no=doc_metadata["standard_no"],
                old_sn=old_sn,
            )


async def write_one(chunk: DocumentChunk, doc_metadata: dict) -> None:
    """单条写入，适合调试或增量补充场景。"""
    driver = get_neo4j_driver()
    async with driver.session() as session:
        await session.run(
            _ONE_CYPHER,
            standard_no=doc_metadata.get("standard_no", ""),
            chunk_id=chunk["chunk_id"],
            content_type=chunk["content_type"],
            section_path=chunk["section_path"],
            content=chunk["content"],
            raw_content=chunk["raw_content"],
        )


async def write(chunks: List[DocumentChunk], doc_metadata: dict) -> None:
    """write_to_kb 调用的入口，使用 write_batch。"""
    await write_batch(chunks, doc_metadata)
