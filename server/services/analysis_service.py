"""Analysis 业务编排服务 — L2 层，编排 OCR、解析、DB 读写和 LLM Agent workflow."""
from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.assembler import assemble_from_agent_output, assemble_from_db_cache
from api.analysis.food_resolver import InvalidFoodIdError, resolve_food_id
from api.analysis.ingredient_matcher import fetch_ingredient_details, match_ingredients
from api.analysis.ingredient_parser import NoIngredientsFoundError, parse_ingredients
from api.analysis.models import FeedbackRequest, FeedbackResponse
from api.analysis.ocr_client import run_ocr
from config import Settings
from database.models import AnalysisFeedback
from db_repositories.food import FoodRepository
from db_repositories.ingredient import IngredientRepository
from db_repositories.ingredient_alias import IngredientAliasRepository
from db_repositories.ingredient_analysis import IngredientAnalysisRepository
from db_repositories.product_analysis import ProductAnalysisRepository
from services.product_analysis_service import ProductAnalysisService
from workflow_product_analysis.types import IngredientInput, ProductAnalysisResult

if TYPE_CHECKING:
    pass


class AnalysisError(Exception):
    """通用分析错误（不区分具体类型，供 router 捕获转换为 HTTP 状态码）。"""

    def __init__(self, message: str, http_status: int = 500):
        super().__init__(message)
        self.http_status = http_status


class AnalysisService:
    """
    L2: Analysis 业务编排服务。

    编排步骤（run_analysis_sync）：
      1. OCR
      2. 解析成分（parse_ingredients）
      3. resolve_food_id（暂时仍调 L1 food_resolver，FoodRepository.fetch_by_name_ilike 待 Task 2）
      4. 成分匹配（match_ingredients，L1 函数，待重构为纯 Repository）
      5. fetch_ingredient_details（L1 函数，待重构为纯 Repository）
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

    async def run_analysis_sync(
        self,
        session: AsyncSession,
        image_bytes: bytes,
        explicit_food_id: int | None,
        settings: Settings,
    ) -> ProductAnalysisResult:
        """
        同步分析管道（可直接调用，跳过 BackgroundTasks）。
        返回完整 ProductAnalysisResult。

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

        # ③ resolve_food_id（L1 直接用 session.execute(select(Food))，待 Task 2 改用 FoodRepository）
        try:
            resolved_food_id = await resolve_food_id(
                explicit_food_id=explicit_food_id,
                product_name=parse_result.product_name,
                task_id=str(uuid.uuid4()),
                session=session,
                settings=settings,
            )
        except InvalidFoodIdError:
            raise AnalysisError("food_id 无效或不存在", http_status=400)

        # ④ 成分匹配（L1 函数，match_ingredients 内部用 session.execute(select(Ingredient))）
        match_result = await match_ingredients(parse_result.ingredients, session)

        # ⑤ 构建 ingredient_inputs（含 level、safety_info）
        # L1 函数 fetch_ingredient_details 内部用 session.execute(select(Ingredient))
        ingredient_inputs: list[IngredientInput] = []
        matched_ids: list[int] = []
        for m in match_result.matched:
            details = await fetch_ingredient_details(m["ingredient_id"], session)
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
        for name in match_result.unmatched:
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
                "unmatched_ingredient_names": match_result.unmatched,
            },
            matched_ids=matched_ids,
            ingredients_data=ingredients_data,
            analyses_data=analyses_data,
        )

        # NOTE: data 缺失 "version" 字段（模型要求非空），为与原 run_analysis_sync 行为保持一致，暂传空字符串。
        # 原代码同样未传 version，这是 ProductAnalysisRepository.insert_if_absent 的潜在 bug，待修复。
        await self._product_analysis_repo.insert_if_absent(
            food_id=resolved_food_id,
            data={
                "ai_model": settings.DEFAULT_MODEL,
                "version": "1.0",  # TODO: 从 settings 或 workflow 输出获取版本号
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
