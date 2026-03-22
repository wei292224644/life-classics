# FastAPI Product API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 FastAPI 后端新增 SQLAlchemy 数据层 + `GET /api/product?barcode=xxx` 端点，读取现有 PostgreSQL 数据库返回产品完整信息。

**Architecture:** 在 `server/db/` 下新建 SQLAlchemy 2.x async models 和 repository，在 `server/api/product/` 下新建路由模块，通过 FastAPI dependency injection 解耦 repository，方便测试时 mock。psycopg3 已在项目依赖中，直接用 `postgresql+psycopg` 驱动，无需新增 asyncpg。

**Tech Stack:** SQLAlchemy 2.x (async)、psycopg3（已有）、FastAPI、pytest + TestClient、pytest-mock

---

## 文件结构

```
server/
├── db/
│   ├── __init__.py              # 新建
│   ├── base.py                  # 新建：DeclarativeBase
│   ├── session.py               # 新建：async engine + get_session()
│   └── models/
│       ├── __init__.py          # 新建
│       ├── food.py              # 新建：Food, FoodIngredient, FoodNutritionEntry
│       ├── ingredient.py        # 新建：Ingredient
│       ├── nutrition.py         # 新建：Nutrition
│       └── analysis.py          # 新建：AnalysisDetail
├── db_repositories/
│   ├── __init__.py              # 新建
│   └── food.py                  # 新建：FoodRepository.fetch_by_barcode()
├── api/
│   ├── __init__.py              # 修改：注册 product router
│   └── product/
│       ├── __init__.py          # 新建
│       ├── models.py            # 新建：Pydantic 响应模型
│       └── router.py            # 新建：GET /product
├── config.py                    # 修改：新增 POSTGRES_URL
└── tests/
    └── api/
        └── test_product.py      # 新建：endpoint 测试（mock repository）
```

> **注意：** repository 目录命名为 `db_repositories/` 而非 `db/repositories/`，避免与 `db/` 包产生路径冲突。

---

### Task 1: 添加 SQLAlchemy 依赖 + POSTGRES_URL 配置

**Files:**
- Modify: `server/pyproject.toml`
- Modify: `server/config.py`

- [ ] **Step 1: 添加 sqlalchemy 依赖**

```bash
cd server
uv add "sqlalchemy[asyncio]>=2.0"
```

预期输出：`Resolved ... sqlalchemy ...`

- [ ] **Step 2: 在 config.py 新增 POSTGRES_URL**

在 `server/config.py` 的 Settings 类中，找到 `# ── 存储路径` 注释块上方，新增：

```python
# ── PostgreSQL 连接 ───────────────────────────────────────────────────────────
POSTGRES_URL: str = ""  # 格式：postgresql+psycopg://user:pass@host:5432/dbname
```

- [ ] **Step 3: 在 server/.env 中添加占位配置**（本地开发用，不提交）

```
POSTGRES_URL=postgresql+psycopg://postgres:postgres@localhost:5432/life_classics
```

- [ ] **Step 4: 验证配置加载正常**

```bash
cd server
uv run python3 -c "from config import settings; print(settings.POSTGRES_URL)"
```

预期：打印出 POSTGRES_URL 字符串（空字符串或配置值均可）

- [ ] **Step 5: Commit**

```bash
git add server/pyproject.toml server/uv.lock server/config.py
git commit -m "feat(db): add sqlalchemy dependency and POSTGRES_URL config"
```

---

### Task 2: SQLAlchemy base + session

**Files:**
- Create: `server/db/__init__.py`
- Create: `server/db/base.py`
- Create: `server/db/session.py`

- [ ] **Step 1: 新建 `server/db/__init__.py`（空文件）**

```python
```

- [ ] **Step 2: 新建 `server/db/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 3: 新建 `server/db/session.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.POSTGRES_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: 提供 AsyncSession，请求结束后自动关闭。"""
    async with _get_session_factory()() as session:
        yield session
```

- [ ] **Step 4: Commit**

```bash
git add server/db/
git commit -m "feat(db): add sqlalchemy base and async session factory"
```

---

### Task 3: SQLAlchemy Models

**Files:**
- Create: `server/db/models/__init__.py`
- Create: `server/db/models/food.py`
- Create: `server/db/models/ingredient.py`
- Create: `server/db/models/nutrition.py`
- Create: `server/db/models/analysis.py`

- [ ] **Step 1: 新建 `server/db/models/__init__.py`**

```python
from .analysis import AnalysisDetail
from .food import Food, FoodIngredient, FoodNutritionEntry
from .ingredient import Ingredient
from .nutrition import Nutrition

__all__ = [
    "Food",
    "FoodIngredient",
    "FoodNutritionEntry",
    "Ingredient",
    "Nutrition",
    "AnalysisDetail",
]
```

- [ ] **Step 2: 新建 `server/db/models/ingredient.py`**

```python
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[list[str]] = mapped_column(default=[])
    description: Mapped[str | None] = mapped_column(Text)
    is_additive: Mapped[bool] = mapped_column(Boolean, default=False)
    additive_code: Mapped[str | None] = mapped_column(String(50))
    standard_code: Mapped[str | None] = mapped_column(String(255))
    who_level: Mapped[str | None] = mapped_column(String(50), default="Unknown")
    allergen_info: Mapped[str | None] = mapped_column(String(255))
    function_type: Mapped[str | None] = mapped_column(String(100))
    origin_type: Mapped[str | None] = mapped_column(String(100))
    limit_usage: Mapped[str | None] = mapped_column(String(255))
    legal_region: Mapped[str | None] = mapped_column(String(255))
```

- [ ] **Step 3: 新建 `server/db/models/nutrition.py`**

```python
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Nutrition(Base):
    __tablename__ = "nutrition_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[list[str]] = mapped_column(default=[])
    category: Mapped[str | None] = mapped_column(String(255))
    sub_category: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    daily_value: Mapped[str | None] = mapped_column(String(255))
    upper_limit: Mapped[str | None] = mapped_column(String(255))
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_info: Mapped[str | None] = mapped_column(Text)
    pregnancy_note: Mapped[str | None] = mapped_column(Text)
    metabolism_role: Mapped[str | None] = mapped_column(String(255))
```

- [ ] **Step 4: 新建 `server/db/models/analysis.py`**

```python
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AnalysisDetail(Base):
    __tablename__ = "analysis_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(Integer)
    target_type: Mapped[str] = mapped_column(String(50))
    analysis_type: Mapped[str] = mapped_column(String(100))
    analysis_version: Mapped[str] = mapped_column(String(10))
    ai_model: Mapped[str] = mapped_column(String(255))
    results: Mapped[dict] = mapped_column(JSONB)
    level: Mapped[str] = mapped_column(String(20))
    confidence_score: Mapped[int] = mapped_column(Integer)
    raw_output: Mapped[dict] = mapped_column(JSONB)
```

- [ ] **Step 5: 新建 `server/db/models/food.py`**

```python
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(primary_key=True)
    barcode: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    image_url_list: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=[])
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    production_address: Mapped[str | None] = mapped_column(String(255))
    origin_place: Mapped[str | None] = mapped_column(String(255))
    production_license: Mapped[str | None] = mapped_column(String(255))
    product_category: Mapped[str | None] = mapped_column(String(255))
    product_standard_code: Mapped[str | None] = mapped_column(String(255))
    shelf_life: Mapped[str | None] = mapped_column(String(100))
    net_content: Mapped[str | None] = mapped_column(String(100))

    food_ingredients: Mapped[list["FoodIngredient"]] = relationship(
        back_populates="food", lazy="selectin"
    )
    food_nutritions: Mapped[list["FoodNutritionEntry"]] = relationship(
        back_populates="food", lazy="selectin"
    )


class FoodIngredient(Base):
    __tablename__ = "food_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))

    food: Mapped["Food"] = relationship(back_populates="food_ingredients")
    ingredient: Mapped["Ingredient"] = relationship(lazy="selectin")  # type: ignore[name-defined]


class FoodNutritionEntry(Base):
    __tablename__ = "food_nutrition_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"))
    nutrition_id: Mapped[int] = mapped_column(ForeignKey("nutrition_table.id"))
    value: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    value_unit: Mapped[str] = mapped_column(String(20))
    reference_type: Mapped[str] = mapped_column(String(50))
    reference_unit: Mapped[str] = mapped_column(String(20))

    food: Mapped["Food"] = relationship(back_populates="food_nutritions")
    nutrition: Mapped["Nutrition"] = relationship(lazy="selectin")  # type: ignore[name-defined]
```

- [ ] **Step 6: 验证 models 可正常导入**

```bash
cd server
uv run python3 -c "from db.models import Food, Ingredient, Nutrition, AnalysisDetail; print('OK')"
```

预期：打印 `OK`，无报错

- [ ] **Step 7: Commit**

```bash
git add server/db/models/
git commit -m "feat(db): add sqlalchemy models for food, ingredient, nutrition, analysis"
```

---

### Task 4: FoodRepository

**Files:**
- Create: `server/db_repositories/__init__.py`
- Create: `server/db_repositories/food.py`

- [ ] **Step 1: 写失败测试**

新建 `server/tests/api/test_product.py`（先只写 repository 相关测试骨架，endpoint 测试在 Task 5 补充）：

```python
"""测试 GET /api/product 端点。"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from api.main import app
from api.product.router import get_food_repository


class MockFoodRepository:
    async def fetch_by_barcode(self, barcode: str):
        return None


@pytest.fixture
def client():
    app.dependency_overrides[get_food_repository] = lambda: MockFoodRepository()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_product_not_found_returns_404(client):
    """条形码未收录时返回 404。"""
    resp = client.get("/api/product?barcode=0000000000000")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd server
uv run pytest tests/api/test_product.py -v
```

预期：FAILED 或 ImportError（`api.product.router` 不存在）

- [ ] **Step 3: 新建 `server/db_repositories/__init__.py`（空文件）**

- [ ] **Step 4: 新建 `server/db_repositories/food.py`**

```python
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import AnalysisDetail, Food, FoodIngredient, FoodNutritionEntry


@dataclass
class IngredientDetail:
    id: int
    name: str
    alias: list[str]
    is_additive: bool
    additive_code: str | None
    who_level: str | None
    allergen_info: str | None
    function_type: str | None
    standard_code: str | None
    analysis: dict | None  # first ingredient_summary analysis or None


@dataclass
class NutritionDetail:
    name: str
    alias: list[str]
    value: str  # Decimal as string
    value_unit: str
    reference_type: str
    reference_unit: str


@dataclass
class AnalysisSummary:
    id: int
    analysis_type: str
    results: dict
    level: str


@dataclass
class FoodDetail:
    id: int
    barcode: str
    name: str
    manufacturer: str | None
    origin_place: str | None
    shelf_life: str | None
    net_content: str | None
    image_url_list: list[str]
    nutritions: list[NutritionDetail]
    ingredients: list[IngredientDetail]
    analysis: list[AnalysisSummary]


class FoodRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_by_barcode(self, barcode: str) -> FoodDetail | None:
        result = await self._session.execute(
            select(Food)
            .where(Food.barcode == barcode)
            .options(
                selectinload(Food.food_ingredients).selectinload(FoodIngredient.ingredient),
                selectinload(Food.food_nutritions).selectinload(FoodNutritionEntry.nutrition),
            )
        )
        food = result.scalar_one_or_none()
        if food is None:
            return None

        # 查询 food 级别的 analysis
        analysis_result = await self._session.execute(
            select(AnalysisDetail)
            .where(
                AnalysisDetail.target_id == food.id,
                AnalysisDetail.target_type == "food",
            )
        )
        food_analyses = analysis_result.scalars().all()

        # 查询每个 ingredient 的 ingredient_summary analysis
        ingredient_ids = [fi.ingredient_id for fi in food.food_ingredients]
        ingredient_analysis_map: dict[int, AnalysisSummary | None] = {}
        if ingredient_ids:
            ing_analysis_result = await self._session.execute(
                select(AnalysisDetail).where(
                    AnalysisDetail.target_id.in_(ingredient_ids),
                    AnalysisDetail.target_type == "ingredient",
                    AnalysisDetail.analysis_type == "ingredient_summary",
                )
            )
            for a in ing_analysis_result.scalars().all():
                ingredient_analysis_map[a.target_id] = AnalysisSummary(
                    id=a.id,
                    analysis_type=a.analysis_type,
                    results=a.results,
                    level=a.level,
                )

        ingredients = [
            IngredientDetail(
                id=fi.ingredient.id,
                name=fi.ingredient.name,
                alias=fi.ingredient.alias or [],
                is_additive=fi.ingredient.is_additive or False,
                additive_code=fi.ingredient.additive_code,
                who_level=fi.ingredient.who_level,
                allergen_info=fi.ingredient.allergen_info,
                function_type=fi.ingredient.function_type,
                standard_code=fi.ingredient.standard_code,
                analysis=ingredient_analysis_map.get(fi.ingredient.id).__dict__
                if ingredient_analysis_map.get(fi.ingredient.id)
                else None,
            )
            for fi in food.food_ingredients
        ]

        nutritions = [
            NutritionDetail(
                name=fn.nutrition.name,
                alias=fn.nutrition.alias or [],
                value=str(fn.value),
                value_unit=fn.value_unit,
                reference_type=fn.reference_type,
                reference_unit=fn.reference_unit,
            )
            for fn in food.food_nutritions
        ]

        analysis = [
            AnalysisSummary(
                id=a.id,
                analysis_type=a.analysis_type,
                results=a.results,
                level=a.level,
            )
            for a in food_analyses
        ]

        return FoodDetail(
            id=food.id,
            barcode=food.barcode,
            name=food.name,
            manufacturer=food.manufacturer,
            origin_place=food.origin_place,
            shelf_life=food.shelf_life,
            net_content=food.net_content,
            image_url_list=food.image_url_list or [],
            nutritions=nutritions,
            ingredients=ingredients,
            analysis=analysis,
        )
```

- [ ] **Step 5: Commit**

```bash
git add server/db_repositories/
git commit -m "feat(db): add FoodRepository.fetch_by_barcode()"
```

---

### Task 5: Product API 端点

**Files:**
- Create: `server/api/product/__init__.py`
- Create: `server/api/product/models.py`
- Create: `server/api/product/router.py`
- Modify: `server/api/__init__.py`
- Modify: `server/tests/api/test_product.py`

- [ ] **Step 1: 新建 `server/api/product/__init__.py`（空文件）**

- [ ] **Step 2: 新建 `server/api/product/models.py`**

```python
from pydantic import BaseModel


class IngredientAnalysis(BaseModel):
    id: int
    analysis_type: str
    results: dict
    level: str


class IngredientResponse(BaseModel):
    id: int
    name: str
    alias: list[str]
    is_additive: bool
    additive_code: str | None
    who_level: str | None
    allergen_info: str | None
    function_type: str | None
    standard_code: str | None
    analysis: IngredientAnalysis | None


class NutritionResponse(BaseModel):
    name: str
    alias: list[str]
    value: str
    value_unit: str
    reference_type: str
    reference_unit: str


class AnalysisResponse(BaseModel):
    id: int
    analysis_type: str
    results: dict
    level: str


class ProductResponse(BaseModel):
    id: int
    barcode: str
    name: str
    manufacturer: str | None
    origin_place: str | None
    shelf_life: str | None
    net_content: str | None
    image_url_list: list[str]
    nutritions: list[NutritionResponse]
    ingredients: list[IngredientResponse]
    analysis: list[AnalysisResponse]
```

- [ ] **Step 3: 新建 `server/api/product/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.product.models import ProductResponse
from db.session import get_session
from db_repositories.food import FoodRepository

router = APIRouter()


def get_food_repository(session: AsyncSession = Depends(get_session)) -> FoodRepository:
    return FoodRepository(session)


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

- [ ] **Step 4: 在 `server/api/__init__.py` 注册路由**

在文件末尾添加：

```python
from api.product.router import router as product_router
# ...（其他 import 保持不变）

router.include_router(product_router, tags=["Product"])
```

- [ ] **Step 5: 补全测试**

将 `server/tests/api/test_product.py` 更新为完整测试：

```python
"""测试 GET /api/product 端点。"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.product.router import get_food_repository
from db_repositories.food import (
    AnalysisSummary,
    FoodDetail,
    IngredientDetail,
    NutritionDetail,
)

# ── Mock Repository ───────────────────────────────────────────────────────────

MOCK_FOOD = FoodDetail(
    id=1,
    barcode="6901234567890",
    name="测试饼干",
    manufacturer="测试食品有限公司",
    origin_place="中国",
    shelf_life="12个月",
    net_content="100g",
    image_url_list=[],
    nutritions=[
        NutritionDetail(
            name="能量",
            alias=[],
            value="2000.0000",
            value_unit="kJ",
            reference_type="PER_100_WEIGHT",
            reference_unit="g",
        )
    ],
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
    analysis=[
        AnalysisSummary(
            id=1,
            analysis_type="health_summary",
            results={"summary": "普通零食"},
            level="t1",
        )
    ],
)


class FoundRepository:
    async def fetch_by_barcode(self, barcode: str):
        return MOCK_FOOD


class NotFoundRepository:
    async def fetch_by_barcode(self, barcode: str):
        return None


@pytest.fixture
def client_found():
    app.dependency_overrides[get_food_repository] = lambda: FoundRepository()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_not_found():
    app.dependency_overrides[get_food_repository] = lambda: NotFoundRepository()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Tests ────────────────────────────────────────────────────────────────────

def test_product_not_found_returns_404(client_not_found):
    """条形码未收录时返回 404。"""
    resp = client_not_found.get("/api/product?barcode=0000000000000")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Product not found"


def test_product_found_returns_200(client_found):
    """存在的条形码返回 200 和完整数据。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    assert resp.status_code == 200
    data = resp.json()
    assert data["barcode"] == "6901234567890"
    assert data["name"] == "测试饼干"


def test_product_response_contains_nutritions(client_found):
    """响应中包含 nutritions 列表。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    data = resp.json()
    assert len(data["nutritions"]) == 1
    assert data["nutritions"][0]["name"] == "能量"
    assert data["nutritions"][0]["value_unit"] == "kJ"


def test_product_response_contains_ingredients(client_found):
    """响应中包含 ingredients 列表。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    data = resp.json()
    assert len(data["ingredients"]) == 1
    assert data["ingredients"][0]["name"] == "小麦粉"
    assert data["ingredients"][0]["who_level"] == "Unknown"


def test_product_response_contains_analysis(client_found):
    """响应中包含 analysis 列表。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    data = resp.json()
    assert len(data["analysis"]) == 1
    assert data["analysis"][0]["analysis_type"] == "health_summary"
    assert data["analysis"][0]["level"] == "t1"


def test_missing_barcode_param_returns_422(client_not_found):
    """缺少 barcode 参数时返回 422。"""
    resp = client_not_found.get("/api/product")
    assert resp.status_code == 422
```

- [ ] **Step 6: 运行测试**

```bash
cd server
uv run pytest tests/api/test_product.py -v
```

预期：所有测试 PASS

- [ ] **Step 7: Commit**

```bash
git add server/api/product/ server/api/__init__.py server/tests/api/test_product.py
git commit -m "feat(api): add GET /api/product endpoint with mock-based tests"
```

---

### Task 6: CORS 配置更新

**Files:**
- Modify: `server/config.py`

小程序线上环境需要明确配置域名白名单（当前默认 `["*"]` 仅适合开发）。

- [ ] **Step 1: 确认 CORS_ORIGINS 已是列表类型（可配置）**

查看 `server/config.py`，确认：

```python
CORS_ORIGINS: list[str] = ["*"]
```

此字段通过 `.env` 可覆盖为具体域名列表，无需修改代码。

- [ ] **Step 2: 在 .env 示例文件中记录配置方式**

在 `server/.env.example`（或已有的文档说明）中添加注释：

```
# 生产环境配置各平台域名，多个用逗号分隔
# CORS_ORIGINS=["https://your-domain.com","https://servicewechat.com"]
CORS_ORIGINS=["*"]
```

- [ ] **Step 3: Commit**

```bash
git add server/.env.example
git commit -m "docs(server): document CORS_ORIGINS config for mini program deployment"
```
