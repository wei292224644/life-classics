"""组件 3：Embedding 成分匹配 — 将成分名通过向量检索匹配到配料库。"""
from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from db_repositories.ingredient_analysis import get_active_by_ingredient_id
from database.models import Ingredient
from kb.embeddings import embed_batch
from workflow_product_analysis.types import (
    IngredientRiskLevel,
    MatchedIngredient,
    MatchResult,
)

if TYPE_CHECKING:
    pass

# ChromaDB collection name for ingredient vectors
_INGREDIENT_COLLECTION = "ingredients"


async def match_ingredients(
    ingredient_names: list[str],
    session: AsyncSession,
    settings: Settings,
) -> MatchResult:
    """
    将成分名列表通过向量检索匹配到配料库（ingredients 表）。

    入参：
        ingredient_names: 原始成分名列表（来自 OCR 解析）
        session: AsyncSession
        settings: 配置（含 INGREDIENT_MATCH_THRESHOLD）

    出参：
        MatchResult: {matched: [...], unmatched: [...]}：
        - matched: 相似度 >= 阈值的成分（含 ingredient_id、name、level）
        - unmatched: 相似度 < 阈值的原始成分名
    """
    if not ingredient_names:
        return MatchResult(matched=[], unmatched=[])

    threshold = settings.INGREDIENT_MATCH_THRESHOLD

    # 并发 embedding + 检索
    embeddings = await embed_batch(ingredient_names)

    async def find_match(name: str, embedding: list[float]) -> MatchedIngredient | None:
        results = await _query_ingredient_collection(name, embedding, top_k=1)
        if not results:
            return None
        chunk_id, distance = results[0]  # top_k=1，取第一个结果
        # ChromaDB distance：越小越相似；distance < (1 - threshold) 等价于 similarity >= threshold
        if distance >= threshold:
            return None
        ingredient_id = _parse_ingredient_chunk_id(chunk_id)
        if ingredient_id is None:
            return None
        # 查 DB 获取 details
        name_db, category_str, level = await fetch_ingredient_details(
            ingredient_id, session
        )
        return MatchedIngredient(
            ingredient_id=ingredient_id,
            name=name_db,
            level=level,
        )

    matched_list: list[MatchedIngredient | None] = await asyncio.gather(
        *[
            find_match(name, emb)
            for name, emb in zip(ingredient_names, embeddings)
        ]
    )

    matched: list[MatchedIngredient] = [
        m for m in matched_list if m is not None
    ]
    matched_ids = {m["ingredient_id"] for m in matched}
    unmatched = [
        name
        for name, m in zip(ingredient_names, matched_list)
        if m is None
    ]

    return MatchResult(matched=matched, unmatched=unmatched)


async def _query_ingredient_collection(
    query_text: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[tuple[str, float]] | None:
    """
    查询成分向量 collection。

    返回: [(chunk_id, distance), ...] 或 None（collection 不存在或查询失败）
    ChromaDB distance 值越小表示越相似。
    """
    try:
        from kb.clients import get_chroma_client

        client = get_chroma_client()
        collection = client.get_or_create_collection(_INGREDIENT_COLLECTION)

        def _sync_query():
            return collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

        result = await asyncio.to_thread(_sync_query)
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]

        if not ids:
            return None
        return list(zip(ids, distances))
    except Exception:  # noqa: BLE001
        # Collection 不存在或查询失败 → 降级
        return None


def _parse_ingredient_chunk_id(chunk_id: str) -> int | None:
    """从 ChromaDB chunk_id 解析 ingredient_id。格式：'ingredient_{id}'"""
    m = re.match(r"ingredient_(\d+)", chunk_id)
    if m:
        return int(m.group(1))
    return None


async def fetch_ingredient_details(
    ingredient_id: int,
    session: AsyncSession,
) -> tuple[str, str, IngredientRiskLevel]:
    """
    按 ingredient_id 查 DB，返回 (name, category_str, level)。

    category_str: function_type 数组拼接，如 "增稠剂 · 高升糖指数"
    level: 来自 active IngredientAnalysis；无记录则返回 "unknown"
    """
    result = await session.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id)
    )
    ingredient = result.scalar_one_or_none()

    if ingredient is None:
        return f"ingredient_{ingredient_id}", "", "unknown"

    # category = function_type join
    function_types: list[str] = ingredient.function_type or []
    category_str = " · ".join(function_types)

    # active analysis level
    analysis = await get_active_by_ingredient_id(ingredient_id, session)
    if analysis is not None:
        level: IngredientRiskLevel = analysis.level  # type: ignore[assignment]
    else:
        level = "unknown"

    return ingredient.name, category_str, level
