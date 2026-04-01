import uuid

from api.ingredients.models import IngredientCreate, IngredientUpdate, IngredientPatch
from api.product.models import (
    AnalysisResponse,
    IngredientResponse,
    RelatedProductSimple,
)
from config import settings
from db_repositories.ingredient import IngredientDetail, IngredientRepository
from enums import RiskLevel


class IngredientService:
    def __init__(self, repo: IngredientRepository):
        self._repo = repo

    def _to_response(self, ingredient) -> IngredientResponse:
        return IngredientResponse(
            id=ingredient.id,
            name=ingredient.name,
            alias=ingredient.alias or [],
            description=ingredient.description,
            is_additive=ingredient.is_additive or False,
            additive_code=ingredient.additive_code,
            standard_code=ingredient.standard_code,
            who_level=ingredient.who_level,
            allergen_info=ingredient.allergen_info or [],
            function_type=ingredient.function_type or [],
            origin_type=ingredient.origin_type,
            limit_usage=ingredient.limit_usage,
            legal_region=ingredient.legal_region,
            cas=ingredient.cas,
            applications=ingredient.applications,
            notes=ingredient.notes,
            safety_info=ingredient.safety_info,
            analyses=[],
            related_products=[],
        )

    async def create(self, body: IngredientCreate) -> IngredientResponse:
        """Upsert：按 name 查找，存在则合并，不存在则创建."""
        ingredient = await self._repo.upsert(**body.model_dump(mode='json'))
        return self._to_response(ingredient)

    async def get_by_id(self, ingredient_id: int) -> IngredientResponse | None:
        ingredient = await self._repo.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def list_(
        self,
        limit: int = 20,
        offset: int = 0,
        name: str | None = None,
        is_additive: bool | None = None,
    ) -> tuple[list[IngredientResponse], int]:
        ingredients, total = await self._repo.fetch_list(
            limit=limit,
            offset=offset,
            name=name,
            is_additive=is_additive,
        )
        return [self._to_response(i) for i in ingredients], total

    async def update_full(
        self, ingredient_id: int, body: IngredientUpdate
    ) -> IngredientResponse | None:
        ingredient = await self._repo.update_full(ingredient_id, **body.model_dump(mode='json'))
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def update_partial(
        self, ingredient_id: int, body: IngredientPatch
    ) -> IngredientResponse | None:
        ingredient = await self._repo.update_partial(
            ingredient_id,
            **{k: v for k, v in body.model_dump(mode='json').items() if v is not None},
        )
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def delete(self, ingredient_id: int) -> bool:
        """软删除，幂等."""
        return await self._repo.soft_delete(ingredient_id)

    async def get_detail_by_id(self, ingredient_id: int) -> IngredientResponse | None:
        """配料详情（含分析记录与关联产品），用于分析展示."""
        detail = await self._repo.fetch_detail_by_id(ingredient_id)
        if detail is None:
            return None
        return self._to_detail_response(detail)

    async def trigger_analysis(self, ingredient_id: int, background_tasks) -> dict | None:
        """检查配料存在，返回 task_id，编排 BackgroundTask 执行完整流程."""
        ingredient = await self._repo.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None

        task_id = str(uuid.uuid4())

        async def _run_workflow():
            from workflow_ingredient_analysis.entry import run_ingredient_analysis
            from database.session import async_session_maker
            from api.ingredient_analysis.service import IngredientAnalysisService

            # 1. 构造 ingredient dict
            ingredient_dict = {
                "ingredient_id": ingredient.id,
                "name": ingredient.name,
                "function_type": ingredient.function_type or [],
                "origin_type": ingredient.origin_type or "",
                "limit_usage": ingredient.limit_usage or "",
                "safety_info": ingredient.safety_info or "",
                "cas": ingredient.cas or "",
            }

            # 2. 调用 workflow（纯计算）
            result = await run_ingredient_analysis(
                ingredient=ingredient_dict,
                task_id=task_id,
                ai_model=settings.DEFAULT_MODEL,
            )

            # 3. 写分析结果
            if result["status"] == "succeeded":
                analysis_output = result["analysis_output"] or {}
                write_payload = {
                    "ai_model": result.get("ai_model", "unknown"),
                    "level": analysis_output.get("level", "unknown"),
                    "safety_info": result["composed_output"]["safety_info"],
                    "alternatives": result["composed_output"]["alternatives"],
                    "confidence_score": analysis_output.get("confidence_score", 0.0),
                    "evidence_refs": result["evidence_refs"] or [],
                    "decision_trace": analysis_output.get("decision_trace", {}),
                }
                async with async_session_maker() as session:
                    svc = IngredientAnalysisService(session)
                    await svc.create(ingredient_id, write_payload)

        background_tasks.add_task(_run_workflow)
        return {"task_id": task_id, "ingredient_id": ingredient_id, "status": "queued"}

    def _to_detail_response(self, d: IngredientDetail) -> IngredientResponse:
        return IngredientResponse(
            id=d.id,
            name=d.name,
            alias=d.alias,
            description=d.description,
            is_additive=d.is_additive,
            additive_code=d.additive_code,
            standard_code=d.standard_code,
            who_level=d.who_level,
            allergen_info=d.allergen_info,
            function_type=d.function_type,
            origin_type=d.origin_type,
            limit_usage=d.limit_usage,
            legal_region=d.legal_region,
            cas=d.cas,
            applications=d.applications,
            notes=d.notes,
            safety_info=d.safety_info,
            analyses=[
                AnalysisResponse(
                    analysis_type=a["analysis_type"],
                    result=a["result"],
                    source=a.get("source"),
                    level=RiskLevel.from_str(a["level"]),
                    confidence_score=a["confidence_score"],
                )
                for a in d.analyses
            ],
            related_products=[RelatedProductSimple(**p) for p in d.related_products],
        )
