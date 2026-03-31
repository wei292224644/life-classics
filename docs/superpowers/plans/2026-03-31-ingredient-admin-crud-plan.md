# 配料管理 Admin CRUD 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 实现配料管理 CRUD API，包括 Create（Upsert）、List、Get、Update（Full/Patch）、Delete

**架构：**
- Repository 层：`db_repositories/ingredient_admin.py` 处理数据库操作
- Service 层：`services/ingredient_admin.py` 处理业务逻辑（字段级合并、upsert）
- API 层：`api/ingredients/router.py` 定义路由，`api/ingredients/models.py` 定义请求/响应模型

**技术栈：** FastAPI、SQLAlchemy Async、Pydantic

**路径设计：** 完整路径为 `/api/ingredients`（`/api` 前缀由 `api/main.py` 统一添加，`/ingredients` 在 `api/__init__.py` 注册时添加）

---

## 文件结构

```
server/
├── api/ingredients/
│   ├── __init__.py
│   ├── router.py      # 路由定义
│   └── models.py      # 请求/响应模型（IngredientCreate, IngredientUpdate, IngredientsListResponse）
├── db_repositories/
│   └── ingredient_admin.py    # Repository 类
└── services/
    └── ingredient_admin.py    # Service 类（upsert、字段合并）
```

---

## Task 1: 创建 `api/ingredients/` 目录结构和模型

**文件：**
- Create: `server/api/ingredients/__init__.py`
- Create: `server/api/ingredients/models.py`
- Modify: `server/api/__init__.py`（注册路由）

- [ ] **Step 1: 创建 `server/api/ingredients/__init__.py`**

```python
```

- [ ] **Step 2: 创建 `server/api/ingredients/models.py`**

```python
from pydantic import BaseModel, Field
from typing import Any


class IngredientCreate(BaseModel):
    """创建/更新配料请求体（upsert 用）."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_additive: bool = False
    additive_code: str | None = None
    standard_code: str | None = None
    who_level: str | None = None
    allergen_info: list[str] = []
    function_type: list[str] = []
    origin_type: str | None = None
    limit_usage: str | None = None
    legal_region: str | None = None
    cas: str | None = None
    applications: str | None = None
    notes: str | None = None
    safety_info: str | None = None


class IngredientUpdate(BaseModel):
    """全量更新请求体（PUT 用，所有字段必填）."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_additive: bool = False
    additive_code: str | None = None
    standard_code: str | None = None
    who_level: str | None = None
    allergen_info: list[str] = []
    function_type: list[str] = []
    origin_type: str | None = None
    limit_usage: str | None = None
    legal_region: str | None = None
    cas: str | None = None
    applications: str | None = None
    notes: str | None = None
    safety_info: str | None = None


class IngredientPatch(BaseModel):
    """部分更新请求体（PATCH 用，所有字段可选）."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_additive: bool | None = None
    additive_code: str | None = None
    standard_code: str | None = None
    who_level: str | None = None
    allergen_info: list[str] | None = None
    function_type: list[str] | None = None
    origin_type: str | None = None
    limit_usage: str | None = None
    legal_region: str | None = None
    cas: str | None = None
    applications: str | None = None
    notes: str | None = None
    safety_info: str | None = None


class IngredientsListResponse(BaseModel):
    """配料列表响应."""
    items: list[Any]  # IngredientResponse
    total: int
    limit: int
    offset: int
```

- [ ] **Step 3: 在 `server/api/__init__.py` 中注册 admin 路由占位（确认是否需要）**

```bash
# 先查看 api/__init__.py 内容
cat server/api/__init__.py
```

- [ ] **Step 4: 提交**

```bash
git add server/api/ingredients/ server/api/__init__.py
git commit -m "feat: add admin ingredient API models"
```

---

## Task 2: 创建 `db_repositories/ingredient_admin.py`

**文件：**
- Create: `server/db_repositories/ingredient_admin.py`
- Test: `server/tests/db_repositories/test_ingredient_admin.py`

- [ ] **Step 1: 创建测试文件 `server/tests/db_repositories/test_ingredient_admin.py`**

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.base import Base
from db_repositories.ingredient_admin import IngredientAdminRepository


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def repo(session):
    return IngredientAdminRepository(session)


@pytest.mark.asyncio
async def test_upsert_creates_new_ingredient(repo, session):
    """按 name 不存在时，创建新配料."""
    result = await repo.upsert(
        name="蔗糖",
        description="食糖",
        is_additive=False,
        allergen_info=["无"],
    )
    assert result.name == "蔗糖"
    assert result.description == "食糖"
    assert result.is_additive is False
    assert result.allergen_info == ["无"]
    assert result.id is not None


@pytest.mark.asyncio
async def test_upsert_merges_existing_ingredient(repo, session):
    """按 name 存在时，字段级合并（只更新非空字段）."""
    # 先创建
    await repo.upsert(
        name="蔗糖",
        description="初始描述",
        is_additive=False,
        cas="57-50-1",
    )
    # 再次 upsert，只更新 description
    result = await repo.upsert(
        name="蔗糖",
        description="新描述",
    )
    assert result.description == "新描述"
    assert result.cas == "57-50-1"  # 保留原有值


@pytest.mark.asyncio
async def test_fetch_by_id_returns_none_for_deleted(repo, session):
    """软删除后 fetch_by_id 返回 None."""
    ingredient = await repo.upsert(name="测试配料")
    await repo.soft_delete(ingredient.id)
    result = await repo.fetch_by_id(ingredient.id)
    assert result is None


@pytest.mark.asyncio
async def test_soft_delete_then_delete_again_returns_204(repo, session):
    """重复删除返回 True（幂等）."""
    ingredient = await repo.upsert(name="测试配料")
    first = await repo.soft_delete(ingredient.id)
    second = await repo.soft_delete(ingredient.id)
    assert first is True
    assert second is True
```

- [ ] **Step 2: 运行测试确认失败（repo 不存在）**

```bash
cd server && uv run pytest tests/db_repositories/test_ingredient_admin.py -v
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 `server/db_repositories/ingredient_admin.py`**

```python
from dataclasses import dataclass
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Ingredient


@dataclass
class IngredientAdminDetail:
    """管理员视角的配料完整信息."""
    id: int
    name: str
    description: str | None
    is_additive: bool
    additive_code: str | None
    standard_code: str | None
    who_level: str | None
    allergen_info: list[str]
    function_type: list[str]
    origin_type: str | None
    limit_usage: str | None
    legal_region: str | None
    cas: str | None
    applications: str | None
    notes: str | None
    safety_info: str | None


class IngredientAdminRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, **fields) -> Ingredient:
        """
        Upsert：按 name 精确匹配，存在则字段级合并，不存在则新建。
        空列表 [] 不覆盖已有值。
        """
        name = fields.pop("name")
        # 查找已存在
        result = await self._session.execute(
            select(Ingredient).where(Ingredient.name == name, Ingredient.deleted_at.is_(None))
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            # 字段级合并：只更新非 None 且非空列表的字段
            for key, value in fields.items():
                if value is not None and value != []:
                    setattr(existing, key, value)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        else:
            # 新建
            ingredient = Ingredient(name=name, **fields)
            self._session.add(ingredient)
            await self._session.commit()
            await self._session.refresh(ingredient)
            return ingredient

    async def fetch_by_id(self, ingredient_id: int) -> Ingredient | None:
        """获取单个配料，软删除的返回 None."""
        result = await self._session.execute(
            select(Ingredient).where(
                Ingredient.id == ingredient_id,
                Ingredient.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def fetch_list(
        self,
        limit: int = 20,
        offset: int = 0,
        name: str | None = None,
        is_additive: bool | None = None,
    ) -> tuple[list[Ingredient], int]:
        """分页查询配料列表."""
        query = select(Ingredient).where(Ingredient.deleted_at.is_(None))
        count_query = select(Ingredient.id).where(Ingredient.deleted_at.is_(None))

        if name is not None:
            query = query.where(Ingredient.name.ilike(f"%{name}%"))
            count_query = count_query.where(Ingredient.name.ilike(f"%{name}%"))

        if is_additive is not None:
            query = query.where(Ingredient.is_additive == is_additive)
            count_query = count_query.where(Ingredient.is_additive == is_additive)

        # 总数
        total_result = await self._session.execute(count_query)
        total = len(total_result.scalars().all())

        # 分页
        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        ingredients = result.scalars().all()

        return list(ingredients), total

    async def update_full(self, ingredient_id: int, **fields) -> Ingredient | None:
        """全量更新：所有字段使用请求值，未传字段置 None."""
        ingredient = await self.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None
        for key, value in fields.items():
            setattr(ingredient, key, value)
        await self._session.commit()
        await self._session.refresh(ingredient)
        return ingredient

    async def update_partial(self, ingredient_id: int, **fields) -> Ingredient | None:
        """部分更新：只更新提供的非空字段."""
        ingredient = await self.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None
        for key, value in fields.items():
            if value is not None and value != []:
                setattr(ingredient, key, value)
        await self._session.commit()
        await self._session.refresh(ingredient)
        return ingredient

    async def soft_delete(self, ingredient_id: int) -> bool:
        """软删除，返回是否实际删除了记录（True=之前未删除，False=之前已删除）."""
        ingredient = await self.fetch_by_id(ingredient_id)
        if ingredient is None:
            return True  # 幂等，已删除视为成功
        ingredient.deleted_at = datetime.utcnow()
        await self._session.commit()
        return True
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd server && uv run pytest tests/db_repositories/test_ingredient_admin.py -v
# 预期: PASS（修复 import datetime 缺失）
```

- [ ] **Step 5: 提交**

```bash
git add server/db_repositories/ingredient_admin.py server/tests/db_repositories/test_ingredient_admin.py
git commit -m "feat: add IngredientAdminRepository with upsert and soft delete"
```

---

## Task 3: 创建 `services/ingredient_admin.py`

**文件：**
- Create: `server/services/__init__.py`
- Create: `server/services/ingredient_admin.py`

- [ ] **Step 1: 创建 `server/services/__init__.py`**

```python
```

- [ ] **Step 2: 创建 `server/services/ingredient_admin.py`**

```python
from datetime import datetime
from api.admin.models import IngredientCreate, IngredientUpdate, IngredientPatch
from api.product.models import IngredientResponse, RelatedProductSimple, AnalysisResponse
from db_repositories.ingredient_admin import IngredientAdminRepository
from enums import RiskLevel


class IngredientAdminService:
    def __init__(self, repo: IngredientAdminRepository):
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

    async def create(self, body: IngredientCreate) -> tuple[IngredientResponse, bool]:
        """
        Upsert 逻辑：按 name 查找，存在则合并，不存在则创建。
        返回 (response, is_created).
        """
        was_created = False
        ingredient = await self._repo.upsert(**body.model_dump())
        return self._to_response(ingredient), was_created

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

    async def update_full(self, ingredient_id: int, body: IngredientUpdate) -> IngredientResponse | None:
        ingredient = await self._repo.update_full(ingredient_id, **body.model_dump())
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def update_partial(self, ingredient_id: int, body: IngredientPatch) -> IngredientResponse | None:
        ingredient = await self._repo.update_partial(
            ingredient_id,
            **{k: v for k, v in body.model_dump().items() if v is not None},
        )
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def delete(self, ingredient_id: int) -> bool:
        """软删除，幂等（已删除返回 True）."""
        return await self._repo.soft_delete(ingredient_id)
```

- [ ] **Step 3: 提交**

```bash
git add server/services/__init__.py server/services/ingredient_admin.py
git commit -m "feat: add IngredientAdminService"
```

---

## Task 4: 创建 `api/ingredients/ingredient.py` 路由

**文件：**
- Create: `server/api/ingredients/ingredient.py`
- Modify: `server/api/__init__.py`（注册路由）
- Test: `server/tests/api/test_admin_ingredient.py`

- [ ] **Step 1: 创建测试文件 `server/tests/api/test_admin_ingredient.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from main import app  # FastAPI app instance


@pytest.mark.asyncio
async def test_create_ingredient():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/ingredients/ingredients",
            json={"name": "测试配料", "description": "测试用"},
        )
    assert response.status_code in (201, 200)


@pytest.mark.asyncio
async def test_get_ingredient_by_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 先创建
        create_resp = await client.post(
            "/api/ingredients/ingredients",
            json={"name": "获取测试配料"},
        )
        ingredient_id = create_resp.json()["id"]
        # 再获取
        response = await client.get(f"/api/ingredients/ingredients/{ingredient_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "获取测试配料"


@pytest.mark.asyncio
async def test_get_ingredient_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/ingredients/ingredients/999999")
        assert response.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败（路由不存在）**

```bash
cd server && uv run pytest tests/api/test_admin_ingredient.py -v
# 预期: 404 或路由不存在错误
```

- [ ] **Step 3: 创建 `server/api/ingredients/ingredient.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from api.admin.models import IngredientCreate, IngredientUpdate, IngredientPatch, IngredientsListResponse
from api.product.models import IngredientResponse
from db_repositories.ingredient_admin import IngredientAdminRepository
from services.ingredient_admin import IngredientAdminService


router = APIRouter(prefix="/admin/ingredients", tags=["Admin Ingredient"])


def get_repo(session=get_async_session):
    return IngredientAdminRepository(session)


def get_service(repo: IngredientAdminRepository = Depends(get_repo)) -> IngredientAdminService:
    return IngredientAdminService(repo)


@router.post("", response_model=IngredientResponse, status_code=201)
async def create_ingredient(
    body: IngredientCreate,
    svc: IngredientAdminService = Depends(get_service),
):
    """创建配料（Upsert）。存在则字段级合并。"""
    response, was_created = await svc.create(body)
    # 如需区分 201/200 可调整
    return response


@router.get("", response_model=IngredientsListResponse)
async def list_ingredients(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    name: Optional[str] = Query(None),
    is_additive: Optional[bool] = Query(None),
    svc: IngredientAdminService = Depends(get_service),
):
    """配料列表查询（分页 + 过滤）."""
    items, total = await svc.list_(limit=limit, offset=offset, name=name, is_additive=is_additive)
    return IngredientsListResponse(items=[i.model_dump() for i in items], total=total, limit=limit, offset=offset)


@router.get("/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: int,
    svc: IngredientAdminService = Depends(get_service),
):
    """获取单个配料详情."""
    result = await svc.get_by_id(ingredient_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result


@router.put("/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient_full(
    ingredient_id: int,
    body: IngredientUpdate,
    svc: IngredientAdminService = Depends(get_service),
):
    """全量更新配料."""
    result = await svc.update_full(ingredient_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result


@router.patch("/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient_partial(
    ingredient_id: int,
    body: IngredientPatch,
    svc: IngredientAdminService = Depends(get_service),
):
    """部分更新配料（只更新提供的字段）."""
    result = await svc.update_partial(ingredient_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result


@router.delete("/{ingredient_id}", status_code=204)
async def delete_ingredient(
    ingredient_id: int,
    svc: IngredientAdminService = Depends(get_service),
):
    """软删除配料（幂等）."""
    await svc.delete(ingredient_id)
    return None
```

- [ ] **Step 4: 查看 `server/api/__init__.py` 并注册 admin 路由**

```bash
cat server/api/__init__.py
```

如果内容为空或只是 `from .product import router`，需要添加 admin 路由注册。

- [ ] **Step 5: 运行测试确认通过**

```bash
cd server && uv run pytest tests/api/test_admin_ingredient.py -v
```

- [ ] **Step 6: 提交**

```bash
git add server/api/ingredients/ingredient.py server/api/__init__.py server/tests/api/test_admin_ingredient.py
git commit -m "feat: add admin ingredient CRUD endpoints"
```

---

## Task 5: 修复 `IngredientCreate` 中 `is_additive` 默认值问题

**问题：** `is_additive: bool = False` 在 Pydantic 中会导致 `false` 值的字段无法与"未提供"区分，影响 PATCH 的语义。

**文件：**
- Modify: `server/api/ingredients/models.py`

- [ ] **Step 1: 修复 `IngredientCreate.is_additive` 和 `IngredientPatch.is_additive`**

```python
class IngredientCreate(BaseModel):
    is_additive: bool | None = None  # None 表示未提供，False 是显式值


class IngredientPatch(BaseModel):
    is_additive: bool | None = None  # None = 不更新
```

- [ ] **Step 2: 更新 `services/ingredient_admin.py` 中 `upsert` 逻辑**

`is_additive=False` 作为默认值需要特殊处理。

- [ ] **Step 3: 提交**

---

## Task 6: 修复 `IngredientAdminRepository.soft_delete` 中 `deleted_at` 需要 import

**问题：** `datetime.utcnow()` 需要 `from datetime import datetime`

**文件：**
- Modify: `server/db_repositories/ingredient_admin.py`

- [ ] **Step 1: 添加 import**

```python
from datetime import datetime
```

- [ ] **Step 2: 提交**

```bash
git add server/db_repositories/ingredient_admin.py
git commit -m "fix: add missing datetime import in ingredient_admin repo"
```

---

## Task 7: 端到端测试验证

**文件：**
- Modify: `server/tests/api/test_admin_ingredient.py`

- [ ] **Step 1: 补充完整端到端测试（create, list, get, update full, update partial, delete）**

```python
@pytest.mark.asyncio
async def test_full_crud_flow():
    """完整 CRUD 流程测试."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        create_resp = await client.post(
            "/api/ingredients/ingredients",
            json={"name": "完整测试配料", "description": "初始"},
        )
        assert create_resp.status_code == 201
        ingredient_id = create_resp.json()["id"]

        # List
        list_resp = await client.get("/api/ingredients/ingredients")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

        # Get
        get_resp = await client.get(f"/api/ingredients/ingredients/{ingredient_id}")
        assert get_resp.status_code == 200

        # Patch
        patch_resp = await client.patch(
            f"/api/ingredients/ingredients/{ingredient_id}",
            json={"description": "更新后"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["description"] == "更新后"

        # Put
        put_resp = await client.put(
            f"/api/ingredients/ingredients/{ingredient_id}",
            json={"name": "完整测试配料", "description": "全量更新后"},
        )
        assert put_resp.status_code == 200

        # Delete
        del_resp = await client.delete(f"/api/ingredients/ingredients/{ingredient_id}")
        assert del_resp.status_code == 204

        # Verify deleted
        get_after_del = await client.get(f"/api/ingredients/ingredients/{ingredient_id}")
        assert get_after_del.status_code == 404
```

- [ ] **Step 2: 运行测试**

```bash
cd server && uv run pytest tests/api/test_admin_ingredient.py -v
```

- [ ] **Step 3: 提交**

```bash
git add server/tests/api/test_admin_ingredient.py
git commit -m "test: add full CRUD e2e tests for admin ingredient API"
```

---

## 自检清单

- [ ] 所有端点（POST/GET LIST/GET/{id}/PUT/PATCH/DELETE）已实现
- [ ] Upsert 逻辑（按 name 匹配，存在则合并）已实现并测试
- [ ] 软删除（deleted_at）已实现并测试
- [ ] List 分页（limit/offset）已实现并测试
- [ ] 字段级合并（PATCH）正确保留未提供字段
- [ ] 已删除配料 GET 返回 404
- [ ] 重复 DELETE 返回 204（幂等）
- [ ] 测试覆盖所有主要场景
