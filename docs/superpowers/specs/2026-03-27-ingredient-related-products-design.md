# 配料详情页「含此配料的产品」功能设计

## 1. 概述

在配料详情页（`/pages/ingredient-detail`）新增「含此配料的产品」数据展示，数据通过 `/api/ingredient/{id}` 接口返回，无需单独接口。

## 2. API 层

### 2.1 新增模型

**文件**: `server/api/product/models.py`

```python
class RelatedProductSimple(BaseModel):
    """配料关联的简化产品信息"""
    id: int
    name: str
    barcode: str
    image_url: str | None  # 取第一张图片
    category: str | None  # product_category
```

### 2.2 修改 IngredientResponse

**文件**: `server/api/product/models.py`

在 `IngredientResponse` 中新增字段：

```python
class IngredientResponse(BaseModel):
    ...
    related_products: list[RelatedProductSimple] = []
```

### 2.3 数据层修改

**文件**: `server/db_repositories/ingredient.py`

修改 `IngredientDetail` dataclass，新增 `related_products` 字段：

```python
@dataclass
class IngredientDetail:
    ...
    related_products: list[dict]  # [{id, name, barcode, image_url, category}]
```

修改 `IngredientRepository.fetch_by_id()` 方法：

```python
# 在查询 analysis 之后添加
# 查询关联产品（通过 FoodIngredient -> Food）
food_query = (
    select(Food.id, Food.name, Food.barcode, Food.image_url_list, Food.product_category)
    .join(FoodIngredient, FoodIngredient.food_id == Food.id)
    .where(FoodIngredient.ingredient_id == ingredient_id)
    .limit(6)
)
food_result = await self._session.execute(food_query)
related_products = [
    {
        "id": row.id,
        "name": row.name,
        "barcode": row.barcode,
        "image_url": row.image_url_list[0] if row.image_url_list else None,
        "category": row.product_category,
    }
    for row in food_result.all()
]
```

### 2.4 Service 层修改

**文件**: `server/api/product/service.py`

修改 `_to_ingredient_response()` 方法，添加 `related_products` 转换：

```python
def _to_ingredient_response(self, d: IngredientDetail) -> IngredientResponse:
    ...
    return IngredientResponse(
        ...
        related_products=[
            RelatedProductSimple(**p) for p in d.related_products
        ],
    )
```

## 3. 前端修改

### 3.1 类型定义

**文件**: `web/apps/uniapp-tw/src/types/ingredient.ts`

```typescript
export interface RelatedProductSimple {
  id: number;
  name: string;
  barcode: string;
  image_url: string | null;
  category: string | null;
}

export interface IngredientDetail {
  ...
  related_products: RelatedProductSimple[];
}
```

### 3.2 页面组件

**文件**: `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue`

恢复「含此配料的产品」卡片的数据绑定，从接口获取：

```vue
<view class="flex gap-2 p-3" style="width: max-content">
  <view
    v-for="p in ingredient?.related_products"
    :key="p.id"
    class="bg-background border-border-c w-24 flex-shrink-0 cursor-pointer rounded-xl border p-2 active:opacity-70"
    @click="goToProduct(p.barcode)"
  >
    <view
      class="bg-card mb-1.5 flex items-center justify-center rounded-md text-2xl w-full py-2"
    >
      {{ p.image_url ? '🖼' : '📦' }}
    </view>
    <text class="text-foreground mb-1 block text-xs font-semibold">
      {{ p.name }}
    </text>
    <text class="text-muted-foreground text-xs">{{ p.category }}</text>
  </view>
</view>
```

## 4. 测试验证

- [ ] 配料有关联产品时正常显示
- [ ] 配料无关联产品时显示空卡片（v-if 控制）
- [ ] 点击产品卡片跳转 product 页面
