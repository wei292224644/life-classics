from __future__ import annotations

from typing import List

from app.core.kb.clients import get_chroma_client
from app.core.kb.embeddings import embed_batch
from app.core.parser_workflow.models import DocumentChunk

COLLECTION_NAME = "gb_standards"


def get_collection():
    return get_chroma_client().get_or_create_collection(COLLECTION_NAME)


async def delete_by_standard_no(standard_no: str, errors: List[str]) -> bool:
    """删除 collection 中所有 standard_no 匹配的记录。文档不存在视为成功。"""
    try:
        get_collection().delete(where={"standard_no": {"$eq": standard_no}})
        return True
    except Exception as e:
        errors.append(f"chroma delete error: {e}")
        return False


async def write(chunks: List[DocumentChunk], doc_metadata: dict) -> None:
    """批量向量化并 upsert 到 ChromaDB。"""
    if not chunks:
        return
    collection = get_collection()
    embeddings = await embed_batch([c["content"] for c in chunks])
    collection.upsert(
        ids=[c["chunk_id"] for c in chunks],
        documents=[c["content"] for c in chunks],
        embeddings=embeddings,
        metadatas=[
            {
                "standard_no": doc_metadata["standard_no"],
                "content_type": c["content_type"],
                "section_path": "|".join(c["section_path"]),
                "doc_type": doc_metadata.get("doc_type", ""),
            }
            for c in chunks
        ],
    )
