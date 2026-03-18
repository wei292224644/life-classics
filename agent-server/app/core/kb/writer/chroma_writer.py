from __future__ import annotations

from typing import List

from app.core.kb.clients import get_chroma_client
from app.core.kb.embeddings import embed_batch
from app.core.parser_workflow.models import DocumentChunk

COLLECTION_NAME = "gb_standards"

_TRUNCATE_SUFFIX = "...（内容已截断）"
_MAX_RAW_LEN = 2000


def get_collection():
    return get_chroma_client().get_or_create_collection(COLLECTION_NAME)


async def delete_by_doc_id(doc_id: str, errors: List[str]) -> bool:
    """删除 collection 中所有 doc_id 匹配的记录。文档不存在视为成功。"""
    try:
        get_collection().delete(where={"doc_id": {"$eq": doc_id}})
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
                "doc_id": doc_metadata["doc_id"],
                "standard_no": doc_metadata.get("standard_no", ""),
                "semantic_type": c["semantic_type"],
                "section_path": "|".join(c["section_path"]),
                "doc_type": doc_metadata.get("doc_type", ""),
                "raw_content": (
                    lambda raw: (
                        raw[:_MAX_RAW_LEN - len(_TRUNCATE_SUFFIX)] + _TRUNCATE_SUFFIX
                        if len(raw) > _MAX_RAW_LEN
                        else raw
                    )
                )(c.get("raw_content") or ""),
            }
            for c in chunks
        ],
    )
