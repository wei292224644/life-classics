"""Analysis 业务编排服务 — L2 层，编排 OCR、解析、DB 读写和 LLM Agent workflow."""
from __future__ import annotations

import asyncio
import hashlib
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.assembler import assemble_from_agent_output, assemble_from_db_cache
from api.analysis.ingredient_parser import NoIngredientsFoundError, parse_ingredients
from api.analysis.models import FeedbackRequest, FeedbackResponse
from api.analysis.ocr_client import run_ocr
from config import Settings
from database.models import AnalysisFeedback, Food
from db_repositories.ingredient import IngredientRepository
from db_repositories.ingredient_alias import IngredientAliasRepository, normalize_ingredient_name
from db_repositories.ingredient_analysis import IngredientAnalysisRepository
from db_repositories.product_analysis import ProductAnalysisRepository
from services.product_analysis_service import ProductAnalysisService
from workflow_product_analysis.types import IngredientInput


class AnalysisError(Exception):
    """通用分析错误（不区分具体类型，供 router 捕获转换为 HTTP 状态码）。"""

    def __init__(self, message: str, http_status: int = 500):
        super().__init__(message)
        self.http_status = http_status


class InvalidFoodIdError(Exception):
    """显式传入的 food_id 在 DB 中不存在。"""
    pass


class AnalysisService:
    """
    L2: Analysis 业务编排服务。

    编排步骤（run_analysis_sync）：
      1. OCR
      2. 解析成分（parse_ingredients，调用 api.analysis.ingredient_parser 工具函数）
      3. resolve_food_id（使用 FoodRepository，已迁移自 food_resolver.py）
      4. match_ingredients（使用 IngredientAliasRepository，已迁移自 ingredient_matcher.py）
      5. fetch_ingredient_details（使用 IngredientRepository + IngredientAnalysisRepository）
      6. IngredientRepository.fetch_by_ids
      7. IngredientAnalysisRepository.fetch_by_ingredient_ids
      8. ProductAnalysisService.run_product_analysis
      9. ProductAnalysisRepository.insert_if_absent

    session 由 Router 层通过 Depends 注入，L2 Service 不自管 session。
    """

    def __init__(
        self,
        food_repo: FoodRepository,
        ingredient_alias_repo: IngredientAliasRepository,
        ingredient_repo: IngredientRepository,
        ingredient_analysis_repo: IngredientAnalysisRepository,
        product_analysis_repo: ProductAnalysisRepository,
        product_analysis_svc: ProductAnalysisService,
    ):
        self._food_repo = food_repo
        self._ingredient_alias_repo = ingredient_alias_repo
        self._ingredient_repo = ingredient_repo
        self._ingredient_analysis_repo = ingredient_analysis_repo
        self._product_analysis_repo = product_analysis_repo
        self._product_analysis_svc = product_analysis_svc

    # ── L2 内部方法（迁自 L1 food_resolver.py / ingredient_matcher.py）────────

    async def _resolve_food_id(
        self,
        session: AsyncSession,
        explicit_food_id: int | None,
        product_name: str | None,
        task_id: str,
        settings: Settings,
    ) -> int:
        """
        解析确定性 food_id。

        逻辑优先级：
        1. explicit_food_id 不为 None → 查 foods 表，存在即返回；不存在抛 InvalidFoodIdError
        2. product_name 不为 None → ILIKE 模糊匹配 foods.name
        3. 以上均未命中 → 创建占位 Food 记录（barcode=PHOTO-{task_id}）
        """
        # 1. 显式 food_id
        if explicit_food_id is not None:
            food = await self._food_repo.fetch_by_id_simple(explicit_food_id)
            if food is not None:
                return food.id
            raise InvalidFoodIdError(
                f"explicit_food_id={explicit_food_id} not found or deleted"
            )

        # 2. 品名模糊匹配
        if product_name is not None:
            pattern = f"%{product_name}%"
            candidates = await self._food_repo.fetch_by_name_ilike(pattern)

            if len(candidates) == 1:
                threshold = getattr(settings, "FOOD_NAME_MATCH_THRESHOLD", 0.7)
                if threshold > 0:
                    return candidates[0].id
                return candidates[0].id
            elif len(candidates) > 1:
                # 多候选：取 name 最长的
                best = max(candidates, key=lambda f: len(f.name or ""))
                return best.id

        # 3. 创建占位 Food
        barcode = f"PHOTO-{task_id}"
        name = product_name if product_name else "未命名产品"
        placeholder = Food(
            barcode=barcode,
            name=name,
            metadata={"source": "photo_import", "task_id": task_id},
            created_by_user=getattr(settings, "SYSTEM_USER_ID", ""),
        )
        session.add(placeholder)
        await session.flush()
        return placeholder.id

    async def _fetch_ingredient_details(
        self,
        session: AsyncSession,
        ingredient_id: int,
    ) -> tuple[str, str, str] | None:
        """
        按 ingredient_id 查 DB，返回 (name, category_str, level)。

        category_str: function_type 数组拼接
        level: 来自 active IngredientAnalysis；无记录则返回 "unknown"
        """
        ingredient = await self._ingredient_repo.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None

        function_types: list[str] = ingredient.function_type or []
        category_str = " · ".join(function_types)

        analysis = await self._ingredient_analysis_repo.get_active_by_ingredient_id(ingredient_id)
        level: str = analysis.level if analysis else "unknown"

        return ingredient.name, category_str, level

    async def _match_ingredients(
        self,
        session: AsyncSession,
        ingredient_names: list[str],
    ) -> dict[str, Any]:
        """
        将成分名列表通过别名精确匹配到配料库。

        Returns:
            dict with keys: "matched" (list of dicts with ingredient_id, name, level),
                            "unmatched" (list of original names)
        """
        if not ingredient_names:
            return {"matched": [], "unmatched": []}

        async def find_match(name: str) -> tuple[str, dict | None]:
            normalized = normalize_ingredient_name(name)
            alias_record = await self._ingredient_alias_repo.find_by_normalized_alias(normalized)

            if alias_record is None:
                return name, None

            ingredient_id = alias_record.ingredient_id
            details = await self._fetch_ingredient_details(session, ingredient_id)
            if details is None:
                return name, None

            name_db, category_str, level = details
            return name, {
                "ingredient_id": ingredient_id,
                "name": name_db,
                "level": level,
            }

        results = await asyncio.gather(
            *[find_match(name) for name in ingredient_names]
        )

        matched = [m for _, m in results if m is not None]
        unmatched = [name for name, m in results if m is None]

        return {"matched": matched, "unmatched": unmatched}

    # ── 公开编排方法 ─────────────────────────────────────────────────────────

    async def run_analysis_sync(
        self,
        session: AsyncSession,
        image_bytes: bytes,
        explicit_food_id: int | None,
        settings: Settings,
    ) -> dict[str, Any]:
        """
        同步分析管道（可直接调用，跳过 BackgroundTasks）。
        返回完整 dict（assembler 输出格式）。

        Raises:
            AnalysisError: 各阶段失败时抛出，含 http_status 供 Router 转换。
        """
        # ① OCR
        ocr_text = await run_ocr(image_bytes, settings)

        # ② 解析成分
        try:
            parse_result = await parse_ingredients(ocr_text, settings)
        except NoIngredientsFoundError:
            raise AnalysisError("无法从图片中提取到配料表", http_status=422)

        # ③ resolve_food_id（已迁移至 L2 _resolve_food_id）
        try:
            resolved_food_id = await self._resolve_food_id(
                session=session,
                explicit_food_id=explicit_food_id,
                product_name=parse_result.product_name,
                task_id=str(uuid.uuid4()),
                settings=settings,
            )
        except InvalidFoodIdError:
            raise AnalysisError("food_id 无效或不存在", http_status=400)

        # ④ 成分匹配（已迁移至 L2 _match_ingredients）
        match_result = await self._match_ingredients(session, parse_result.ingredients)

        # ⑤ 构建 ingredient_inputs
        ingredient_inputs: list[IngredientInput] = []
        matched_ids: list[int] = []
        for m in match_result["matched"]:
            details = await self._fetch_ingredient_details(session, m["ingredient_id"])
            if details is None:
                continue
            name_db, category_str, level = details
            ingredient_inputs.append(
                IngredientInput(
                    ingredient_id=m["ingredient_id"],
                    name=name_db,
                    category=category_str,
                    level=level,
                    safety_info="",
                )
            )
            matched_ids.append(m["ingredient_id"])
        for name in match_result["unmatched"]:
            ingredient_inputs.append(
                IngredientInput(
                    ingredient_id=0,
                    name=name,
                    category="",
                    level="unknown",
                    safety_info="",
                )
            )

        # ⑥ 预查 Ingredient 和 IngredientAnalysis 数据
        ingredients_raw = await self._ingredient_repo.fetch_by_ids(matched_ids)
        ingredients_data = [
            {
                "id": ing.id,
                "name": ing.name,
                "function_type": ing.function_type or [],
            }
            for ing in ingredients_raw
        ]

        analyses_raw = await self._ingredient_analysis_repo.fetch_by_ingredient_ids(matched_ids)
        analyses_data = {a.ingredient_id: a for a in analyses_raw}

        # ⑦ 查 ProductAnalysis 缓存
        existing = await self._product_analysis_repo.get_by_food_id(resolved_food_id)
        if existing is not None:
            return await assemble_from_db_cache(
                product_analysis=existing,
                matched_ids=matched_ids,
                ingredients_data=ingredients_data,
                analyses_data=analyses_data,
            )

        # ⑧ Agent 分析
        try:
            final_state = await self._product_analysis_svc.run_product_analysis(ingredient_inputs)
        except Exception as exc:
            raise AnalysisError(f"Agent workflow failed: {exc}", http_status=500) from exc

        # ⑨ 组装 + 写缓存
        result = await assemble_from_agent_output(
            agent_output={
                "verdict_level": final_state.get("verdict_level"),
                "verdict_description": final_state.get("verdict_description"),
                "advice": final_state.get("advice"),
                "demographics": final_state.get("demographics", []),
                "scenarios": final_state.get("scenarios", []),
                "references": final_state.get("references", []),
                "unmatched_ingredient_names": match_result["unmatched"],
            },
            matched_ids=matched_ids,
            ingredients_data=ingredients_data,
            analyses_data=analyses_data,
        )

        await self._product_analysis_repo.insert_if_absent(
            food_id=resolved_food_id,
            data={
                "ai_model": settings.DEFAULT_MODEL,
                "version": "1.0",
                "level": final_state.get("verdict_level", "t3"),
                "description": final_state.get("verdict_description", ""),
                "advice": final_state.get("advice", ""),
                "demographics": final_state.get("demographics", []),
                "scenarios": final_state.get("scenarios", []),
                "references": final_state.get("references", []),
            },
            created_by_user=settings.SYSTEM_USER_ID,
        )

        return result

    async def submit_feedback(
        self,
        session: AsyncSession,
        req: FeedbackRequest,
        client_ip: str,
        user_agent: str,
    ) -> FeedbackResponse:
        """
        提交用户对分析结果的反馈。

        Args:
            session: AsyncSession（由 Router 层通过 Depends 注入）
            req: FeedbackRequest
            client_ip: 从 Request.client.host 提取的字符串
            user_agent: 从 Request.headers["user-agent"] 提取的字符串

        Returns:
            FeedbackResponse
        """
        ip_hash = (
            hashlib.sha256(client_ip.encode()).hexdigest()
            if client_ip
            else None
        )

        ua = user_agent[:512] if user_agent else ""

        record = AnalysisFeedback(
            task_id=req.task_id,
            food_id=req.food_id,
            category=req.category,
            message=req.message,
            client_context=req.client_context,
            reporter_user_id=None,
            source_ip_hash=ip_hash,
            user_agent=ua,
        )
        session.add(record)
        await session.flush()

        return FeedbackResponse(accepted=True)
