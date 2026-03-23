# Product API 分层与服务化设计

## 背景

当前 `api/product/router.py` 的 endpoint 直接依赖 Repository 并自行处理 dataclass → Pydantic 转换，两层边界模糊。此外 `FoodRepository` 返回的配料数据（`IngredientDetail`）字段完整，但 product 列表页面（`IngredientSection.vue`）只需其中少数字段，存在过度返回。

## 目标

1. 引入 Service 层，建立 API → Service → Repository 三层架构
2. 实现按需返回：product 列表接口返回精简的配料数据
3. 消除 `IngredientDetail` 在两个 Repository 中的重复定义
4. 统一 API 层的 Pydantic 模型定义

## 分层架构

```
API Layer        Router       — HTTP 请求处理、参数校验、依赖注入
                   ↓
Service Layer    ProductService — 业务逻辑编排、模型转换
                   ↓
Repository Layer FoodRepository / IngredientRepository — 数据访问、聚合查询
                   ↓
Data Layer       SQLAlchemy ORM — 数据库操作
```

**Service 层职责（薄层）：**
- 调用 Repository 获取 domain dataclass
- 转换为对应的 Pydantic 响应模型
- 不承担复杂业务逻辑（当前场景无此需求）

## API 模型设计

### `api/product/models.py`

```python
# ============== Product 相关 ==============

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

# Product 列表页配料（精简版）
class ProductIngredient(BaseModel):
    id: int
    name: str
    who_level: str | None
    function_type: str | None
    allergen_info: str | None
    analysis: "ProductIngredientAnalysis | None"

class ProductIngredientAnalysis(BaseModel):
    level: str
    reason: str | None

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
    ingredients: list[ProductIngredient]  # 简化版
    analysis: list[AnalysisResponse]


# ============== Ingredient 详情相关 ==============

class IngredientAnalysis(BaseModel):
    id: int
    analysis_type: str
    results: dict
    level: str

# 配料详情（完整版）
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
```

## Repository 层 dataclass

### `db_repositories/food.py`

```python
@dataclass
class NutritionDetail:
    name: str
    alias: list[str]
    value: str
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
class ProductIngredientDetail:  # FoodRepository 专用
    id: int
    name: str
    who_level: str | None
    function_type: str | None
    allergen_info: str | None
    analysis: "ProductIngredientAnalysisDetail | None"

@dataclass
class ProductIngredientAnalysisDetail:
    level: str
    reason: str | None

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
    ingredients: list[ProductIngredientDetail]  # 精简版
    analysis: list[AnalysisSummary]
```

### `db_repositories/ingredient.py`

```python
@dataclass
class IngredientDetail:  # IngredientRepository 专用，完整版
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
```

**关键区别：**
- `ProductIngredientDetail`：精简字段 + `analysis` 只有 `level` + `reason`
- `IngredientDetail`：所有字段 + 完整 `analysis`

## Service 层

### `api/product/service.py`（新建）

```python
class ProductService:
    def __init__(self, food_repo: FoodRepository, ingredient_repo: IngredientRepository):
        self._food_repo = food_repo
        self._ingredient_repo = ingredient_repo

    async def get_product_by_barcode(self, barcode: str) -> ProductResponse | None:
        detail = await self._food_repo.fetch_by_barcode(barcode)
        if detail is None:
            return None
        return self._to_product_response(detail)

    async def get_ingredient_by_id(self, ingredient_id: int) -> IngredientResponse | None:
        detail = await self._ingredient_repo.fetch_by_id(ingredient_id)
        if detail is None:
            return None
        return self._to_ingredient_response(detail)

    def _to_product_response(self, d: FoodDetail) -> ProductResponse: ...
    def _to_ingredient_response(self, d: IngredientDetail) -> IngredientResponse: ...
```

## Router 改造

`api/product/router.py`：

```python
# 原来
@router.get("/product")
async def get_product(..., repo: FoodRepository = Depends(...)):
    result = await repo.fetch_by_barcode(...)
    return ProductResponse(...)

# 改造后
@router.get("/product")
async def get_product(..., svc: ProductService = Depends(get_product_service)):
    result = await svc.get_product_by_barcode(...)
    if result is None:
        raise HTTPException(404, "Product not found")
    return result
```

依赖注入工厂：

```python
def get_product_service(
    food_repo: FoodRepository = Depends(get_food_repository),
    ingredient_repo: IngredientRepository = Depends(get_ingredient_repository),
) -> ProductService:
    return ProductService(food_repo, ingredient_repo)
```

## 测试改造

`tests/api/test_product.py`：
- `MOCK_FOOD.ingredients` 从 `list[IngredientDetail]` 改为 `list[ProductIngredientDetail]`
- mock 对象实现 `fetch_by_barcode` 返回 `ProductIngredientDetail` 列表

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 新建 | `api/product/service.py` |
| 修改 | `api/product/models.py` — 新增 `ProductIngredient`、`ProductIngredientAnalysis` |
| 修改 | `api/product/router.py` — 改用 `ProductService` |
| 修改 | `db_repositories/food.py` — `IngredientDetail` → `ProductIngredientDetail`（精简），移除原 `IngredientDetail` |
| 修改 | `db_repositories/ingredient.py` — 保留自己的 `IngredientDetail`（完整） |
| 修改 | `tests/api/test_product.py` — 更新 mock 数据结构 |
| 修改 | `db_repositories/__init__.py` — 更新导出 |

## 暂不处理

- `db_repositories/models.py` — 当前两个 Repository 无共享类型，暂不创建该文件；未来有跨仓储类型时再引入
- `IngredientDetail` 在 `food.py` 和 `ingredient.py` 中字段略有不同（后者的 `analysis` 是 `dict | None`，前者是 `AnalysisSummary`），暂不统一，留作后续观察
- Service 层暂为薄层，不做复杂业务逻辑
