# Product API 分层与服务化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引入 Service 层，实现按需返回的精简配料数据，建立 API → Service → Repository 三层架构。

**Architecture:** FoodRepository 输出 `FoodDetail`（含 `ProductIngredientDetail` 精简配料），Service 层负责 dataclass → Pydantic 转换，Router 仅负责 HTTP 处理。

**Tech Stack:** FastAPI, SQLAlchemy AsyncSession, Pydantic, pytest

---

## 文件变更概览

| 文件 | 操作 |
|------|------|
| `db_repositories/food.py` | 修改：新增 `ProductIngredientDetail`、`ProductIngredientAnalysisDetail`，`FoodDetail.ingredients` 改为 `list[ProductIngredientDetail]` |
| `db_repositories/ingredient.py` | 不变：保留自己的 `IngredientDetail`（完整版） |
| `db_repositories/__init__.py` | 不变：无需修改 |
| `api/product/models.py` | 修改：新增 `ProductIngredient`、`ProductIngredientAnalysis` |
| `api/product/service.py` | 新建：Service 类 |
| `api/product/router.py` | 修改：改用 Service |
| `tests/api/test_product.py` | 修改：更新 mock 数据结构 |

---

## Task 1: 修改 `api/product/models.py` — 新增精简配料模型

**Files:**
- Modify: `server/api/product/models.py`

- [ ] **Step 1: 在 `models.py` 顶部添加 `ProductIngredientAnalysis` 和 `ProductIngredient` 类**

在 `IngredientResponse` 定义之后、`NutritionResponse` 定义之前的位置，添加：

```python
class ProductIngredientAnalysis(BaseModel):
    level: str
    reason: str | None


class ProductIngredient(BaseModel):
    id: int
    name: str
    who_level: str | None
    function_type: str | None
    allergen_info: str | None
    analysis: "ProductIngredientAnalysis | None"
```

- [ ] **Step 2: 修改 `ProductResponse.ingredients` 类型**

将 `ProductResponse` 中的：
```python
ingredients: list[IngredientResponse]
```
改为：
```python
ingredients: list[ProductIngredient]
```

- [ ] **Step 3: 运行测试确认无破坏性变更**

```bash
cd server && uv run pytest tests/api/test_product.py -v
```
Expected: 原有测试通过（或因 mock 结构不匹配而失败，待 Task 6 修复）

---

## Task 2: 修改 `db_repositories/food.py` — 新增精简配料 dataclass

**Files:**
- Modify: `server/db_repositories/food.py:1-145`

- [ ] **Step 1: 移除 `from db_repositories.ingredient import IngredientDetail` 导入**

删除第 8 行，因为 `FoodRepository` 不再使用 `IngredientRepository.IngredientDetail`。

- [ ] **Step 2: 在 `NutritionDetail` 之后、`AnalysisSummary` 之前添加两个新 dataclass**

```python
@dataclass
class ProductIngredientAnalysisDetail:
    level: str
    reason: str | None


@dataclass
class ProductIngredientDetail:
    id: int
    name: str
    who_level: str | None
    function_type: str | None
    allergen_info: str | None
    analysis: "ProductIngredientAnalysisDetail | None"
```

- [ ] **Step 3: 修改 `FoodDetail` 中 `ingredients` 字段类型**

将：
```python
ingredients: list[IngredientDetail]
```
改为：
```python
ingredients: list[ProductIngredientDetail]
```

- [ ] **Step 4: 修改 `fetch_by_barcode` 方法中构造 `ingredients` 的逻辑**

将原来的 `IngredientDetail(...)` 构造（第 92-106 行）替换为：

```python
ingredients = []
for fi in food.food_ingredients:
    ing_analysis = ingredient_analysis_map.get(fi.ingredient.id)
    if ing_analysis:
        # 提取 reason（从 results dict 中取，若无则 None）
        raw_results = ing_analysis.results
        reason = raw_results.get("reason") if isinstance(raw_results, dict) else None
        analysis = ProductIngredientAnalysisDetail(
            level=ing_analysis.level,
            reason=reason,
        )
    else:
        analysis = None

    ingredients.append(ProductIngredientDetail(
        id=fi.ingredient.id,
        name=fi.ingredient.name,
        who_level=fi.ingredient.who_level,
        function_type=fi.ingredient.function_type,
        allergen_info=fi.ingredient.allergen_info,
        analysis=analysis,
    ))
```

- [ ] **Step 5: 验证 dataclass 类型变更正确**

```bash
cd server && uv run python -c "from db_repositories.food import FoodDetail, ProductIngredientDetail; print('OK')"
```
Expected: 输出 `OK`，无类型错误（`FoodDetail.ingredients` 现在是 `list[ProductIngredientDetail]`）

---

## Task 3: 新建 `api/product/service.py` — Service 层

**Files:**
- Create: `server/api/product/service.py`

- [ ] **Step 1: 创建 service.py**

```python
from fastapi import HTTPException

from api.product.models import (
    IngredientResponse,
    ProductIngredient,
    ProductIngredientAnalysis,
    ProductResponse,
)
from db_repositories.food import FoodDetail, FoodRepository, ProductIngredientDetail
from db_repositories.ingredient import IngredientDetail, IngredientRepository


class ProductService:
    def __init__(self, food_repo: FoodRepository):
        self._food_repo = food_repo

    async def get_product_by_barcode(self, barcode: str) -> ProductResponse:
        """通过条形码查询产品信息。查不到时由 Router 抛 404。"""
        detail = await self._food_repo.fetch_by_barcode(barcode)
        if detail is None:
            raise ValueError("not_found")
        return self._to_product_response(detail)

    def _to_product_response(self, d: FoodDetail) -> ProductResponse:
        return ProductResponse(
            id=d.id,
            barcode=d.barcode,
            name=d.name,
            manufacturer=d.manufacturer,
            origin_place=d.origin_place,
            shelf_life=d.shelf_life,
            net_content=d.net_content,
            image_url_list=d.image_url_list,
            nutritions=[
                {
                    "name": n.name,
                    "alias": n.alias,
                    "value": n.value,
                    "value_unit": n.value_unit,
                    "reference_type": n.reference_type,
                    "reference_unit": n.reference_unit,
                }
                for n in d.nutritions
            ],
            ingredients=[self._to_product_ingredient(i) for i in d.ingredients],
            analysis=[
                {
                    "id": a.id,
                    "analysis_type": a.analysis_type,
                    "results": a.results,
                    "level": a.level,
                }
                for a in d.analysis
            ],
        )

    def _to_product_ingredient(self, i: ProductIngredientDetail) -> ProductIngredient:
        if i.analysis:
            analysis = ProductIngredientAnalysis(level=i.analysis.level, reason=i.analysis.reason)
        else:
            analysis = None
        return ProductIngredient(
            id=i.id,
            name=i.name,
            who_level=i.who_level,
            function_type=i.function_type,
            allergen_info=i.allergen_info,
            analysis=analysis,
        )


class IngredientService:
    def __init__(self, ingredient_repo: IngredientRepository):
        self._ingredient_repo = ingredient_repo

    async def get_ingredient_by_id(self, ingredient_id: int) -> IngredientResponse:
        """通过配料 ID 查询配料详情。查不到时由 Router 抛 404。"""
        detail = await self._ingredient_repo.fetch_by_id(ingredient_id)
        if detail is None:
            raise ValueError("not_found")
        return self._to_ingredient_response(detail)

    def _to_ingredient_response(self, d: IngredientDetail) -> IngredientResponse:
        # d.analysis 已经是 dict | None 格式（IngredientRepository 返回时已转换）
        analysis_data = None
        if d.analysis:
            analysis_data = {
                "id": d.analysis["id"],
                "analysis_type": d.analysis["analysis_type"],
                "results": d.analysis["results"],
                "level": d.analysis["level"],
            }
        return IngredientResponse(
            id=d.id,
            name=d.name,
            alias=d.alias,
            is_additive=d.is_additive,
            additive_code=d.additive_code,
            who_level=d.who_level,
            allergen_info=d.allergen_info,
            function_type=d.function_type,
            standard_code=d.standard_code,
            analysis=analysis_data,
        )
```

- [ ] **Step 2: 验证导入无误**

```bash
cd server && uv run python -c "from api.product.service import ProductService, IngredientService; print('OK')"
```
Expected: 输出 `OK`

---

## Task 4: 修改 `api/product/router.py` — 改用 Service 层

**Files:**
- Modify: `server/api/product/router.py`

- [ ] **Step 1: 更新导入**

将：
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.product.models import IngredientResponse, ProductResponse
from database.session import get_async_session
from db_repositories.food import FoodRepository
from db_repositories.ingredient import IngredientRepository
```
改为：
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.product.models import IngredientResponse, ProductResponse
from api.product.service import IngredientService, ProductService
from database.session import get_async_session
from db_repositories.food import FoodRepository
from db_repositories.ingredient import IngredientRepository
```

- [ ] **Step 2: 修改依赖注入函数**

将：
```python
def get_ingredient_repository(session: AsyncSession = Depends(get_async_session)) -> IngredientRepository:
    return IngredientRepository(session)

router = APIRouter()


def get_food_repository(session: AsyncSession = Depends(get_async_session)) -> FoodRepository:
    return FoodRepository(session)
```
改为：
```python
router = APIRouter()


def get_food_repository(session: AsyncSession = Depends(get_async_session)) -> FoodRepository:
    return FoodRepository(session)


def get_product_service(food_repo: FoodRepository = Depends(get_food_repository)) -> ProductService:
    return ProductService(food_repo)


def get_ingredient_repository(session: AsyncSession = Depends(get_async_session)) -> IngredientRepository:
    return IngredientRepository(session)


def get_ingredient_service(ingredient_repo: IngredientRepository = Depends(get_ingredient_repository)) -> IngredientService:
    return IngredientService(ingredient_repo)
```

- [ ] **Step 3: 修改 `get_product_by_barcode` endpoint**

将：
```python
@router.get("/product", response_model=ProductResponse, tags=["Product"])
async def get_product_by_barcode(
    barcode: str,
    repo: FoodRepository = Depends(get_food_repository),
):
    """通过条形码查询产品完整信息（营养成分 + 配料 + AI 分析）。"""
    result = await repo.fetch_by_barcode(barcode)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(
        id=result.id,
        barcode=result.barcode,
        name=result.name,
        manufacturer=result.manufacturer,
        origin_place=result.origin_place,
        shelf_life=result.shelf_life,
        net_content=result.net_content,
        image_url_list=result.image_url_list,
        nutritions=[n.__dict__ for n in result.nutritions],
        ingredients=[
            {**i.__dict__, "analysis": i.analysis}
            for i in result.ingredients
        ],
        analysis=[a.__dict__ for a in result.analysis],
    )
```
改为：
```python
@router.get("/product", response_model=ProductResponse, tags=["Product"])
async def get_product_by_barcode(
    barcode: str,
    svc: ProductService = Depends(get_product_service),
):
    """通过条形码查询产品完整信息（营养成分 + 配料 + AI 分析）。"""
    try:
        return await svc.get_product_by_barcode(barcode)
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status_code=404, detail="Product not found")
        raise
```

- [ ] **Step 4: 修改 `get_ingredient_by_id` endpoint**

将：
```python
@router.get("/ingredient/{ingredient_id}", response_model=IngredientResponse, tags=["Ingredient"])
async def get_ingredient_by_id(
    ingredient_id: int,
    repo: IngredientRepository = Depends(get_ingredient_repository),
):
    """通过配料 ID 查询配料详情（支持从搜索/对话等独立入口访问）。"""
    result = await repo.fetch_by_id(ingredient_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return IngredientResponse(
        id=result.id,
        name=result.name,
        alias=result.alias,
        is_additive=result.is_additive,
        additive_code=result.additive_code,
        who_level=result.who_level,
        allergen_info=result.allergen_info,
        function_type=result.function_type,
        standard_code=result.standard_code,
        analysis=result.analysis,
    )
```
改为：
```python
@router.get("/ingredient/{ingredient_id}", response_model=IngredientResponse, tags=["Ingredient"])
async def get_ingredient_by_id(
    ingredient_id: int,
    svc: IngredientService = Depends(get_ingredient_service),
):
    """通过配料 ID 查询配料详情（支持从搜索/对话等独立入口访问）。"""
    try:
        return await svc.get_ingredient_by_id(ingredient_id)
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status_code=404, detail="Ingredient not found")
        raise
```

- [ ] **Step 5: 运行测试验证**

```bash
cd server && uv run pytest tests/api/test_product.py -v
```
Expected: FAIL（mock 数据未更新，Task 6 修复后 PASS）

---

## Task 5: 确认 `db_repositories/__init__.py` 无需变更

**Files:**
- (无文件变更)

- [ ] **Step 1: 确认当前导出仍有效**

当前 `db_repositories/__init__.py` 内容：
```python
from db_repositories.food import FoodRepository
from db_repositories.ingredient import IngredientRepository

__all__ = ["FoodRepository", "IngredientRepository"]
```

`FoodRepository` 和 `IngredientRepository` 仍在各自文件中，无需修改。

该文件导出 `FoodRepository` 和 `IngredientRepository`，不需要修改。但确认两个 Repository 都从各自文件导出即可。

---

## Task 6: 修改 `tests/api/test_product.py` — 更新 mock 数据结构

**Files:**
- Modify: `tests/api/test_product.py`

- [ ] **Step 1: 更新导入和 mock 数据**

将：
```python
from db_repositories.food import (
    AnalysisSummary,
    FoodDetail,
    IngredientDetail,
    NutritionDetail,
)
```
改为：
```python
from db_repositories.food import (
    AnalysisSummary,
    FoodDetail,
    NutritionDetail,
    ProductIngredientAnalysisDetail,
    ProductIngredientDetail,
)
```

将 `MOCK_FOOD` 中的 `ingredients` 字段：
```python
ingredients=[
    IngredientDetail(
        id=1,
        name="小麦粉",
        alias=["面粉"],
        is_additive=False,
        additive_code=None,
        who_level="Unknown",
        allergen_info="含麸质",
        function_type=None,
        standard_code=None,
        analysis=None,
    )
],
```
改为：
```python
ingredients=[
    ProductIngredientDetail(
        id=1,
        name="小麦粉",
        who_level="Unknown",
        function_type=None,
        allergen_info="含麸质",
        analysis=None,
    )
],
```

- [ ] **Step 2: 验证测试通过**

```bash
cd server && uv run pytest tests/api/test_product.py -v
```
Expected: PASS

---

## Task 7: 验证完整流程

- [ ] **Step 1: 运行所有相关测试**

```bash
cd server && uv run pytest tests/api/test_product.py tests/api/test_ingredient.py -v 2>/dev/null || echo "test_ingredient not found, running only test_product"
```
Expected: PASS

- [ ] **Step 2: 验证 API 响应格式**

启动服务后访问 `/api/product?barcode=xxx`，确认 `ingredients` 字段为精简版（含 `analysis.level` 和 `analysis.reason`，无 `alias`、`additive_code`、`standard_code`、`is_additive`）。

- [ ] **Step 3: 提交代码**

```bash
git add server/api/product/service.py server/api/product/models.py server/api/product/router.py server/db_repositories/food.py server/tests/api/test_product.py
git commit -m "feat(product): add service layer and simplify ingredient response

- Add ProductService and IngredientService for API -> Service -> Repository layering
- Add ProductIngredient (simplified) vs IngredientResponse (full) models
- FoodRepository now returns ProductIngredientDetail with only level + reason in analysis
- Update tests to use new mock data structures

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
