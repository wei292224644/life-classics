# L3 DB Repository Layer 架构合规审查报告

**审查时间**: 2026-04-02
**审查范围**: `server/db_repositories/`
**审查人**: 架构合规审查专家

---

## 约束清单

- [约束T2] 禁止L3调用L2
- [约束跨域] 禁止跨表/跨域查询
- [约束业务] 禁止业务判断
- [约束日志] 禁止记录日志
- [约束G3] DTO转换应在Service层完成

---

## 违规项

### 违规1: `server/db_repositories/search.py:49-60` - [约束跨域 + 约束G3]

```python
# 统计每个食品的高风险配料数（通过 IngredientAnalysis.level）
high_risk_result = await self._session.execute(
    select(FoodIngredient.food_id, func.count(func.distinct(FoodIngredient.ingredient_id)).label("cnt"))
    .join(
        IngredientAnalysis,
        IngredientAnalysis.ingredient_id == FoodIngredient.ingredient_id,
    )
    .where(
        FoodIngredient.food_id.in_(food_ids),
        FoodIngredient.deleted_at.is_(None),
        IngredientAnalysis.is_active.is_(True),
        IngredientAnalysis.level.in_(["t3", "t4"]),
    )
    .group_by(FoodIngredient.food_id)
)
```

原因：
1. **跨域查询**: 该查询 JOIN 了 `FoodIngredient` 和 `IngredientAnalysis` 两张表，属于跨表查询，违反"禁止跨域查询"约束
2. **DTO转换**: 该方法返回 `FoodSearchResult` dataclass（含 `high_risk_count` 等业务字段），而非 `Food` Entity，违反 G3 约束（Repository 应返回 Entity）

---

### 违规2: `server/db_repositories/search.py:90-95` - [约束跨域 + 约束G3]

```python
risk_result = await self._session.execute(
    select(IngredientAnalysis.ingredient_id, IngredientAnalysis.level).where(
        IngredientAnalysis.ingredient_id.in_(ing_ids),
        IngredientAnalysis.is_active.is_(True),
    )
)
risk_map: dict[int, str] = {r.ingredient_id: r.level for r in risk_result.all()}
```

原因：
1. **跨域查询**: 该查询在 `Ingredient` 表的查询结果上，再对 `IngredientAnalysis` 表做 IN 查询，属于跨域操作
2. **DTO转换**: 返回 `IngredientSearchResult` dataclass（含 `risk_level` 等业务字段），而非 `Ingredient` Entity

---

### 违规3: `server/db_repositories/search.py:64-74` - [约束G3]

```python
return [
    FoodSearchResult(
        id=f.id,
        barcode=f.barcode,
        name=f.name,
        product_category=f.product_category,
        image_url=f.image_url_list[0] if f.image_url_list else None,
        risk_level="unknown",  # 硬编码默认值
        high_risk_count=high_risk_map.get(f.id, 0),
    )
    for f in foods
]
```

原因：
1. **业务判断逻辑**: `image_url_list[0] if f.image_url_list else None` 和 `high_risk_count` 的计算属于业务逻辑判断
2. **DTO转换**: 直接在 Repository 层构造业务 DTO，违反 G3 约束

---

### 违规4: `server/db_repositories/food.py:51-56` - [约束跨域 + 约束G3]

```python
result = await self._session.execute(
    select(Food)
    .where(Food.id == food_id, Food.deleted_at.is_(None))
    .options(
        selectinload(Food.food_ingredients).selectinload(FoodIngredient.ingredient),
        selectinload(Food.food_nutrition_entries).selectinload(
            FoodNutritionEntry.nutrition
        ),
    )
)
```

原因：
1. **跨域查询**: `selectinload` 加载了 `Food → FoodIngredient → Ingredient` 和 `Food → FoodNutritionEntry → Nutrition` 的多级关联数据，属于跨域查询
2. **业务判断/DTO转换**: 该方法返回 `FoodDetail` dataclass（含 `nutritions`、`ingredients` 等聚合信息），而非 `Food` Entity，违反 G3 约束

---

### 违规5: `server/db_repositories/food.py:62-83` - [约束业务]

```python
ingredients = [
    ProductIngredientDetail(
        id=fi.ingredient.id,
        name=fi.ingredient.name,
        who_level=fi.ingredient.who_level,
        function_type=fi.ingredient.function_type,
        allergen_info=fi.ingredient.allergen_info,
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
    for fn in food.food_nutrition_entries
]
```

原因：
1. **业务逻辑**: 数据映射、聚合操作属于业务逻辑，不应在 L3 Repository 层处理
2. **跨域数据组装**: 在 L3 层跨多个表的数据进行组合拼接

---

### 违规6: `server/db_repositories/ingredient.py:66` - [约束业务]

```python
if is_additive is not None:
    query = query.where(Ingredient.is_additive == is_additive)
```

原因：
1. **业务判断**: `is_additive` 过滤条件的动态构建属于业务逻辑，不属于纯数据操作

---

### 违规7: `server/db_repositories/ingredient_alias.py:11-39` - [约束业务]

```python
def normalize_ingredient_name(name: str) -> str:
    """
    标准化配料名称。

    规则：
    - 去除括号内容（含括号）："焦糖色（着色剂）" → "焦糖色"
    - 英文转小写："SUCROSE" → "sucrose"
    - 去除首尾空格："  蔗糖  " → "蔗糖"
    - 去除"食用"前缀："食用盐" → "盐"
    """
    if not name:
        return name

    result = name.strip()

    # 去除括号内容
    result = re.sub(r"[（(].*?[)）]", "", result)

    # 去除"食用"前缀
    if result.startswith("食用"):
        result = result[2:]

    # 英文转小写
    result = result.lower()

    # 去除多余空格
    result = re.sub(r"\s+", " ", result).strip()

    return result
```

原因：
1. **业务判断**: 配料名称标准化规则（如去除"食用"前缀、括号内容）属于业务逻辑，不应在 L3 Repository 层实现

---

### 违规8: `server/db_repositories/ingredient.py:58-76` - [约束G3]

```python
async def fetch_list(
    self,
    limit: int = 20,
    offset: int = 0,
    name: str | None = None,
    is_additive: bool | None = None,
) -> tuple[list[Ingredient], int]:
    """分页查询配料列表."""
    ...
    return list(ingredients), total
```

原因：
1. **违反单一职责**: 该方法返回 `(list[Ingredient], int)` 元组，包含总数统计，这是数据+业务混合，不属于纯 Entity 返回

---

## 合规项（显著发现）

- ✅ **无跨层调用**: 所有文件均未 import services/ 模块，未发现 L3 调用 L2 的情况
- ✅ **无日志记录**: 所有 Repository 文件均未使用 logging，符合"禁止记录日志"约束
- ✅ **seed_data.py 为独立脚本**: 该文件是数据库填充脚本（非 Repository 类），不受 L3 架构约束
- ✅ **基础 CRUD 操作合规**: `IngredientRepository`、`ProductAnalysisRepository`、`IngredientAnalysisRepository` 的核心 CRUD 操作符合规范

---

## 违规汇总

| 序号 | 文件 | 行号 | 违规类型 | 严重程度 |
|------|------|------|----------|----------|
| 1 | search.py | 49-60 | 跨域查询 + DTO转换 | 高 |
| 2 | search.py | 90-95 | 跨域查询 + DTO转换 | 高 |
| 3 | search.py | 64-74 | 业务判断 + DTO转换 | 高 |
| 4 | food.py | 51-56 | 跨域查询 + DTO转换 | 高 |
| 5 | food.py | 62-83 | 业务逻辑 + 跨域数据组装 | 高 |
| 6 | ingredient.py | 66 | 业务判断 | 中 |
| 7 | ingredient_alias.py | 11-39 | 业务逻辑 | 中 |
| 8 | ingredient.py | 58-76 | 元组返回（数据+业务混合） | 中 |

---

## 总结

- **违规数量**: 8 项
- **严重程度**:
  - 高危（3项）: `search.py` 的跨域 JOIN 查询和 DTO 返回
  - 高危（2项）: `food.py` 的跨域查询和数据聚合
  - 中危（3项）: `ingredient.py` 和 `ingredient_alias.py` 的业务逻辑
- **最严重问题**: `search.py` 和 `food.py` 的跨域查询是最严重的违规，违反了"L3 Repository 只能做单表/单实体 CRUD"的核心约束
- **核心问题根因**: 多个 Repository 承担了本应由 L2 Service 层负责的数据聚合和 DTO 转换工作

---

## 修复建议

1. **search.py**: 拆分为多个单表查询方法，由 L2 Service 负责 JOIN 和 DTO 转换
2. **food.py**: `fetch_by_id` 应返回 `Food` Entity，关联数据由 L2 Service 通过各自的 Repository 查询后组装
3. **ingredient_alias.py**: `normalize_ingredient_name` 函数应移至 L2 Service 层
4. **ingredient.py**: `fetch_list` 返回的元组中 `total` 统计应由调用方（L2）处理，或新增专门的计数查询方法
