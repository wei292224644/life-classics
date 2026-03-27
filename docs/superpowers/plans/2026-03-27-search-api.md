# Search API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `GET /api/search` 统一搜索端点，支持按关键词搜索食品和配料，返回分页结果。

**Architecture:** 新增通用 `Paginated[T]` 分页模型（`api/shared.py`）、`SearchRepository`（DB 查询层）、`UnifiedSearchService`（业务逻辑层），并在现有 `api/search/router.py` 中新增 GET 端点。服务层合并两次独立 DB 查询结果，在 Python 层做 type 过滤和 offset/limit 切片。

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL ILIKE, Pydantic v2, pytest-asyncio

---

## 文件变更总览

| 操作 | 文件 |
|------|------|
| 新建 | `server/api/shared.py` |
| 新建 | `server/db_repositories/search.py` |
| 新建 | `server/tests/api/test_shared.py` |
| 新建 | `server/tests/api/test_search_unified.py` |
| 新建 | `server/tests/db_repositories/test_search_repo.py` |
| 修改 | `server/api/search/models.py` |
| 修改 | `server/api/search/service.py` |
| 修改 | `server/api/search/router.py` |
| 修改 | `server/tests/api/conftest.py` |

---

## Task 1: `api/shared.py` — 通用分页模型

**Files:**
- Create: `server/api/shared.py`
- Test: `server/tests/api/test_shared.py`

- [ ] **Step 1: 写失败测试**

新建 `server/tests/api/test_shared.py`：

```python
"""测试通用分页模型 Paginated[T]。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.shared import Paginated


def test_paginated_basic_fields():
    result = Paginated(items=[1, 2], total=10, offset=0, limit=2, has_more=True)
    assert result.items == [1, 2]
    assert result.total == 10
    assert result.offset == 0
    assert result.limit == 2
    assert result.has_more is True


def test_paginated_has_more_false():
    result = Paginated(items=[], total=5, offset=4, limit=2, has_more=False)
    assert result.has_more is False


def test_paginated_empty_items():
    result = Paginated(items=[], total=0, offset=0, limit=20, has_more=False)
    assert result.total == 0
    assert result.items == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd server && uv run pytest tests/api/test_shared.py -v
```

期望输出：`ModuleNotFoundError: No module named 'api.shared'`

- [ ] **Step 3: 实现 `server/api/shared.py`**

```python
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd server && uv run pytest tests/api/test_shared.py -v
```

期望输出：`3 passed`

- [ ] **Step 5: 提交**

```bash
git add server/api/shared.py server/tests/api/test_shared.py
git commit -m "feat(search): add generic Paginated[T] model"
```

---

## Task 2: `db_repositories/search.py` — SearchRepository

**Files:**
- Create: `server/db_repositories/search.py`
- Test: `server/tests/db_repositories/test_search_repo.py`

注意：`tests/db_repositories/` 目录可能不存在，需检查并创建 `__init__.py`。

- [ ] **Step 1: 确认测试目录存在**

```bash
ls server/tests/db_repositories/ 2>/dev/null || (mkdir -p server/tests/db_repositories && touch server/tests/db_repositories/__init__.py)
```

- [ ] **Step 2: 写失败测试**

新建 `server/tests/db_repositories/test_search_repo.py`：

```python
"""测试 SearchRepository 的 DB 查询逻辑（mock session）。"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db_repositories.search import SearchRepository


@pytest.mark.asyncio
async def test_search_foods_empty_when_no_match():
    """名称无匹配时应直接返回空列表，只执行一次 execute。"""
    mock_session = AsyncMock()
    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock_session.execute.return_value = empty_result

    repo = SearchRepository(mock_session)
    result = await repo.search_foods("不存在的食品")

    assert result == []
    assert mock_session.execute.call_count == 1


@pytest.mark.asyncio
async def test_search_foods_maps_risk_and_high_risk_count():
    """有匹配时应正确映射 risk_level 和 high_risk_count。"""
    mock_session = AsyncMock()

    foods_result = MagicMock()
    foods_result.all.return_value = [
        SimpleNamespace(id=1, barcode="6901234", name="测试饼干", product_category="零食")
    ]
    risk_result = MagicMock()
    risk_result.all.return_value = [
        SimpleNamespace(target_id=1, level="t2")
    ]
    high_risk_result = MagicMock()
    high_risk_result.all.return_value = [
        SimpleNamespace(food_id=1, cnt=2)
    ]

    mock_session.execute.side_effect = [foods_result, risk_result, high_risk_result]

    repo = SearchRepository(mock_session)
    result = await repo.search_foods("饼干")

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].barcode == "6901234"
    assert result[0].name == "测试饼干"
    assert result[0].product_category == "零食"
    assert result[0].risk_level == "t2"
    assert result[0].high_risk_count == 2


@pytest.mark.asyncio
async def test_search_foods_defaults_unknown_when_no_analysis():
    """食品无 overall_risk 分析时 risk_level 应为 unknown，high_risk_count 为 0。"""
    mock_session = AsyncMock()

    foods_result = MagicMock()
    foods_result.all.return_value = [
        SimpleNamespace(id=5, barcode="999", name="无分析食品", product_category=None)
    ]
    risk_result = MagicMock()
    risk_result.all.return_value = []  # 无分析
    high_risk_result = MagicMock()
    high_risk_result.all.return_value = []  # 无高风险配料

    mock_session.execute.side_effect = [foods_result, risk_result, high_risk_result]

    repo = SearchRepository(mock_session)
    result = await repo.search_foods("无分析")

    assert result[0].risk_level == "unknown"
    assert result[0].high_risk_count == 0


@pytest.mark.asyncio
async def test_search_ingredients_empty_when_no_match():
    """配料无匹配时直接返回空列表。"""
    mock_session = AsyncMock()
    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock_session.execute.return_value = empty_result

    repo = SearchRepository(mock_session)
    result = await repo.search_ingredients("不存在")

    assert result == []
    assert mock_session.execute.call_count == 1


@pytest.mark.asyncio
async def test_search_ingredients_maps_risk_level():
    """有匹配时应正确映射 risk_level。"""
    mock_session = AsyncMock()

    ings_result = MagicMock()
    ings_result.all.return_value = [
        SimpleNamespace(id=10, name="苯甲酸钠", function_type=["防腐剂"])
    ]
    risk_result = MagicMock()
    risk_result.all.return_value = [
        SimpleNamespace(target_id=10, level="t4")
    ]

    mock_session.execute.side_effect = [ings_result, risk_result]

    repo = SearchRepository(mock_session)
    result = await repo.search_ingredients("苯甲")

    assert len(result) == 1
    assert result[0].id == 10
    assert result[0].name == "苯甲酸钠"
    assert result[0].function_type == ["防腐剂"]
    assert result[0].risk_level == "t4"
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd server && uv run pytest tests/db_repositories/test_search_repo.py -v
```

期望输出：`ModuleNotFoundError: No module named 'db_repositories.search'`

- [ ] **Step 4: 实现 `server/db_repositories/search.py`**

```python
from dataclasses import dataclass

from sqlalchemy import func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AnalysisDetail, Food, FoodIngredient, Ingredient


@dataclass
class FoodSearchResult:
    id: int
    barcode: str
    name: str
    product_category: str | None
    risk_level: str
    high_risk_count: int


@dataclass
class IngredientSearchResult:
    id: int
    name: str
    function_type: list[str]
    risk_level: str


class SearchRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search_foods(self, q: str) -> list[FoodSearchResult]:
        """按名称搜索食品，并附带 overall_risk 风险等级和高风险配料数。"""
        foods_result = await self._session.execute(
            select(Food.id, Food.barcode, Food.name, Food.product_category)
            .where(
                Food.name.ilike(f"%{q}%"),
                Food.deleted_at.is_(None),
            )
        )
        foods = foods_result.all()
        if not foods:
            return []

        food_ids = [f.id for f in foods]

        # 获取每个食品的 overall_risk 风险等级
        risk_result = await self._session.execute(
            select(AnalysisDetail.target_id, AnalysisDetail.level).where(
                AnalysisDetail.target_id.in_(food_ids),
                AnalysisDetail.analysis_target == "food",
                AnalysisDetail.analysis_type == "overall_risk",
            )
        )
        risk_map: dict[int, str] = {r.target_id: r.level for r in risk_result.all()}

        # 统计每个食品的高风险配料数（ingredient_summary level 为 t3 或 t4）
        high_risk_result = await self._session.execute(
            select(FoodIngredient.food_id, func.count().label("cnt"))
            .join(
                AnalysisDetail,
                (AnalysisDetail.target_id == FoodIngredient.ingredient_id)
                & (AnalysisDetail.analysis_target == "ingredient")
                & (AnalysisDetail.analysis_type == "ingredient_summary")
                & (AnalysisDetail.level.in_(["t3", "t4"])),
            )
            .where(FoodIngredient.food_id.in_(food_ids))
            .group_by(FoodIngredient.food_id)
        )
        high_risk_map: dict[int, int] = {r.food_id: r.cnt for r in high_risk_result.all()}

        return [
            FoodSearchResult(
                id=f.id,
                barcode=f.barcode,
                name=f.name,
                product_category=f.product_category,
                risk_level=risk_map.get(f.id, "unknown"),
                high_risk_count=high_risk_map.get(f.id, 0),
            )
            for f in foods
        ]

    async def search_ingredients(self, q: str) -> list[IngredientSearchResult]:
        """按名称或别名搜索配料，并附带 ingredient_summary 风险等级。"""
        ings_result = await self._session.execute(
            select(Ingredient.id, Ingredient.name, Ingredient.function_type).where(
                or_(
                    Ingredient.name.ilike(f"%{q}%"),
                    literal(q).op("= ANY")(Ingredient.alias),
                )
            )
        )
        ings = ings_result.all()
        if not ings:
            return []

        ing_ids = [i.id for i in ings]

        risk_result = await self._session.execute(
            select(AnalysisDetail.target_id, AnalysisDetail.level).where(
                AnalysisDetail.target_id.in_(ing_ids),
                AnalysisDetail.analysis_target == "ingredient",
                AnalysisDetail.analysis_type == "ingredient_summary",
            )
        )
        risk_map: dict[int, str] = {r.target_id: r.level for r in risk_result.all()}

        return [
            IngredientSearchResult(
                id=i.id,
                name=i.name,
                function_type=i.function_type or [],
                risk_level=risk_map.get(i.id, "unknown"),
            )
            for i in ings
        ]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd server && uv run pytest tests/db_repositories/test_search_repo.py -v
```

期望输出：`6 passed`

- [ ] **Step 6: 提交**

```bash
git add server/db_repositories/search.py server/tests/db_repositories/test_search_repo.py server/tests/db_repositories/__init__.py
git commit -m "feat(search): add SearchRepository with food and ingredient ILIKE queries"
```

---

## Task 3: `SearchResultItem` 模型 + `UnifiedSearchService`

**Files:**
- Modify: `server/api/search/models.py`（追加 `SearchResultItem`）
- Modify: `server/api/search/service.py`（追加 `UnifiedSearchService`）
- Modify: `server/tests/api/conftest.py`（添加预加载）
- Test: `server/tests/api/test_search_unified.py`

- [ ] **Step 1: 更新 conftest.py，添加预加载**

在 `server/tests/api/conftest.py` 的 `_preload_real_api` fixture 末尾追加一行：

```python
    importlib.import_module("api.search.service")
```

更新后 fixture 末尾如下：

```python
    # Now import the real ones
    importlib.import_module("api.documents.service")
    importlib.import_module("api.chunks.service")
    importlib.import_module("api.kb.service")
    importlib.import_module("api.search.service")
```

- [ ] **Step 2: 写失败测试**

新建 `server/tests/api/test_search_unified.py`：

```python
"""测试 UnifiedSearchService 的业务逻辑（mock SearchRepository）。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.search.service import UnifiedSearchService
from db_repositories.search import FoodSearchResult, IngredientSearchResult


MOCK_FOODS = [
    FoodSearchResult(id=1, barcode="111", name="测试饼干", product_category="饼干", risk_level="t2", high_risk_count=1),
    FoodSearchResult(id=2, barcode="222", name="测试糖果", product_category=None, risk_level="unknown", high_risk_count=0),
]

MOCK_INGREDIENTS = [
    IngredientSearchResult(id=10, name="苯甲酸钠", function_type=["防腐剂"], risk_level="t4"),
    IngredientSearchResult(id=11, name="色素红40", function_type=["着色剂", "稳定剂"], risk_level="t3"),
]


@pytest.mark.asyncio
async def test_search_all_combines_products_first_then_ingredients():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=0, limit=20)

    assert result.total == 4
    assert result.items[0].type == "product"
    assert result.items[1].type == "product"
    assert result.items[2].type == "ingredient"
    assert result.items[3].type == "ingredient"
    assert result.has_more is False


@pytest.mark.asyncio
async def test_search_product_only_skips_ingredients():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="product", offset=0, limit=20)

    mock_repo.search_ingredients.assert_not_called()
    assert result.total == 2
    assert all(item.type == "product" for item in result.items)


@pytest.mark.asyncio
async def test_search_ingredient_only_skips_foods():
    mock_repo = AsyncMock()
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="苯甲", result_type="ingredient", offset=0, limit=20)

    mock_repo.search_foods.assert_not_called()
    assert result.total == 2
    assert all(item.type == "ingredient" for item in result.items)


@pytest.mark.asyncio
async def test_search_pagination_has_more_true():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=0, limit=2)

    assert result.total == 4
    assert len(result.items) == 2
    assert result.has_more is True
    assert result.offset == 0
    assert result.limit == 2


@pytest.mark.asyncio
async def test_search_last_page_has_more_false():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=2, limit=2)

    assert result.total == 4
    assert len(result.items) == 2
    assert result.has_more is False


@pytest.mark.asyncio
async def test_search_offset_beyond_total_returns_empty():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=100, limit=20)

    assert result.total == 2
    assert result.items == []
    assert result.has_more is False


@pytest.mark.asyncio
async def test_search_high_risk_count_none_when_zero():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = [
        FoodSearchResult(id=2, barcode="222", name="测试糖果", product_category=None, risk_level="unknown", high_risk_count=0),
    ]
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="糖果", result_type="all")

    assert result.items[0].high_risk_count is None


@pytest.mark.asyncio
async def test_search_high_risk_count_set_when_nonzero():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = [
        FoodSearchResult(id=1, barcode="111", name="测试饼干", product_category="饼干", risk_level="t2", high_risk_count=3),
    ]
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="饼干", result_type="all")

    assert result.items[0].high_risk_count == 3


@pytest.mark.asyncio
async def test_search_ingredient_subtitle_joined_with_slash():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = []
    mock_repo.search_ingredients.return_value = [
        IngredientSearchResult(id=11, name="色素红40", function_type=["着色剂", "稳定剂"], risk_level="t3"),
    ]

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="色素", result_type="all")

    assert result.items[0].subtitle == "着色剂/稳定剂"


@pytest.mark.asyncio
async def test_search_ingredient_empty_function_type_gives_empty_subtitle():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = []
    mock_repo.search_ingredients.return_value = [
        IngredientSearchResult(id=12, name="水", function_type=[], risk_level="t0"),
    ]

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="水", result_type="all")

    assert result.items[0].subtitle == ""


@pytest.mark.asyncio
async def test_search_product_barcode_included():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = [
        FoodSearchResult(id=1, barcode="6920152420245", name="可口可乐", product_category="碳酸饮料", risk_level="unknown", high_risk_count=0),
    ]
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="可口可乐", result_type="all")

    assert result.items[0].barcode == "6920152420245"


@pytest.mark.asyncio
async def test_search_product_no_barcode_on_ingredient():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = []
    mock_repo.search_ingredients.return_value = [
        IngredientSearchResult(id=10, name="苯甲酸钠", function_type=["防腐剂"], risk_level="t4"),
    ]

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="苯甲", result_type="all")

    assert result.items[0].barcode is None
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd server && uv run pytest tests/api/test_search_unified.py -v
```

期望输出：`ImportError` 或 `AttributeError: UnifiedSearchService`

- [ ] **Step 4: 追加 `SearchResultItem` 到 `server/api/search/models.py`**

在文件末尾追加：

```python
from typing import Literal


class SearchResultItem(BaseModel):
    type: Literal["product", "ingredient"]
    id: int
    barcode: str | None = None
    name: str
    subtitle: str
    risk_level: str
    high_risk_count: int | None = None
```

- [ ] **Step 5: 追加 `UnifiedSearchService` 到 `server/api/search/service.py`**

在文件末尾追加：

```python
from typing import Literal

from api.search.models import SearchResultItem
from api.shared import Paginated
from db_repositories.search import FoodSearchResult, IngredientSearchResult, SearchRepository


class UnifiedSearchService:
    def __init__(self, repo: SearchRepository):
        self._repo = repo

    async def search(
        self,
        q: str,
        result_type: Literal["all", "product", "ingredient"] = "all",
        offset: int = 0,
        limit: int = 20,
    ) -> Paginated[SearchResultItem]:
        food_results: list[FoodSearchResult] = []
        ing_results: list[IngredientSearchResult] = []

        if result_type in ("all", "product"):
            food_results = await self._repo.search_foods(q)
        if result_type in ("all", "ingredient"):
            ing_results = await self._repo.search_ingredients(q)

        all_items: list[SearchResultItem] = [
            SearchResultItem(
                type="product",
                id=f.id,
                barcode=f.barcode,
                name=f.name,
                subtitle=f.product_category or "",
                risk_level=f.risk_level,
                high_risk_count=f.high_risk_count if f.high_risk_count > 0 else None,
            )
            for f in food_results
        ] + [
            SearchResultItem(
                type="ingredient",
                id=i.id,
                name=i.name,
                subtitle="/".join(i.function_type) if i.function_type else "",
                risk_level=i.risk_level,
            )
            for i in ing_results
        ]

        total = len(all_items)
        page = all_items[offset : offset + limit]

        return Paginated(
            items=page,
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        )
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd server && uv run pytest tests/api/test_search_unified.py -v
```

期望输出：`12 passed`

- [ ] **Step 7: 提交**

```bash
git add server/api/search/models.py server/api/search/service.py \
        server/tests/api/test_search_unified.py server/tests/api/conftest.py
git commit -m "feat(search): add SearchResultItem model and UnifiedSearchService"
```

---

## Task 4: `GET /api/search` 路由

**Files:**
- Modify: `server/api/search/router.py`

- [ ] **Step 1: 修改 `server/api/search/router.py`**

在文件顶部的 import 区域追加：

```python
from typing import Literal

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.search.models import SearchResultItem
from api.shared import Paginated
from api.search.service import UnifiedSearchService
from database.session import get_async_session
from db_repositories.search import SearchRepository
```

在文件末尾追加依赖函数和路由：

```python
def _get_search_repository(
    session: AsyncSession = Depends(get_async_session),
) -> SearchRepository:
    return SearchRepository(session)


def _get_unified_search_service(
    repo: SearchRepository = Depends(_get_search_repository),
) -> UnifiedSearchService:
    return UnifiedSearchService(repo)


@router.get("/search", response_model=Paginated[SearchResultItem], tags=["Search"])
async def unified_search(
    q: str = Query(..., min_length=1, max_length=100),
    result_type: Literal["all", "product", "ingredient"] = Query(default="all", alias="type"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    svc: UnifiedSearchService = Depends(_get_unified_search_service),
):
    """按关键词搜索食品和配料，支持分页。type 参数过滤结果类型。"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="q must not be blank")
    return await svc.search(q=q.strip(), result_type=result_type, offset=offset, limit=limit)
```

注意：`HTTPException` 已在文件顶部导入，无需重复添加。

- [ ] **Step 2: 运行全部 search 相关测试**

```bash
cd server && uv run pytest tests/api/test_search_unified.py tests/api/test_shared.py tests/db_repositories/test_search_repo.py -v
```

期望输出：全部 passed，无 failure

- [ ] **Step 3: 运行全量测试确认无回归**

```bash
cd server && uv run pytest tests/ -v --ignore=tests/core
```

期望输出：全部 passed 或仅有已知的基础设施相关 skip

- [ ] **Step 4: 提交**

```bash
git add server/api/search/router.py
git commit -m "feat(search): add GET /api/search unified search endpoint with pagination"
```

---

## 验收标准

完成后，可通过 Swagger UI (`http://localhost:9999/swagger`) 手动验证：

1. `GET /api/search?q=饼干` — 返回 `Paginated[SearchResultItem]`，products 在前，ingredients 在后
2. `GET /api/search?q=饼干&type=product` — 仅返回 product 类型
3. `GET /api/search?q=苯甲&type=ingredient` — 仅返回 ingredient 类型
4. `GET /api/search?q=饼干&offset=0&limit=2` — `has_more` 正确反映是否有更多结果
5. `GET /api/search?q=` — 返回 422 (FastAPI validation)
6. `GET /api/search?q=   ` — 返回 400 (空白字符串校验)
