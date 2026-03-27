# Search API 设计文档

## 目标

实现 `GET /api/search` 统一搜索端点，支持按关键词搜索食品和配料，返回分页结果，供前端搜索页消费。

---

## 接口契约

```
GET /api/search?q={keyword}&type={all|product|ingredient}&offset={n}&limit={n}
```

### 查询参数

| 参数 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| `q` | string | 必填 | 非空，≤100 字符 | 搜索关键词 |
| `type` | string | `all` | `all/product/ingredient` | 结果类型过滤 |
| `offset` | int | `0` | ≥0 | 分页偏移量 |
| `limit` | int | `20` | 1-50 | 每页条数 |

### 响应体

```json
{
  "items": [
    {
      "type": "product",
      "id": 101,
      "barcode": "6920152420245",
      "name": "康师傅红烧牛肉面",
      "subtitle": "方便面",
      "riskLevel": "t3",
      "highRiskCount": 3
    },
    {
      "type": "ingredient",
      "id": 1,
      "name": "苯甲酸钠",
      "subtitle": "防腐剂",
      "riskLevel": "t4"
    }
  ],
  "total": 45,
  "offset": 0,
  "limit": 20,
  "has_more": true
}
```

### SearchResultItem 字段说明

| 字段 | 来源 |
|------|------|
| `type` | `"product"` 或 `"ingredient"` |
| `id` | `foods.id` 或 `ingredients.id` |
| `barcode` | `foods.barcode`（仅 product） |
| `name` | `foods.name` 或 `ingredients.name` |
| `subtitle` | product: `foods.product_category`；ingredient: `ingredients.function_type` 首元素（多个用 `/` 连接） |
| `riskLevel` | product: `analysis_details` 中 `analysis_target='food'` + `analysis_type='overall_risk'` 的 level，无则 `unknown`；ingredient: `analysis_target='ingredient'` + `analysis_type='ingredient_summary'` 的 level，无则 `unknown` |
| `highRiskCount` | 仅 product：该食品所有配料中 `ingredient_summary` level 为 t3 或 t4 的数量；为 0 时省略 |

---

## 错误处理

| 情况 | HTTP 状态码 |
|------|-------------|
| `q` 为空或纯空白 | 400 |
| `q` 超过 100 字符 | 400 |
| `limit` 超出 1-50 | 400 |
| `type` 非法值 | 400 |
| 无结果 | 200，`items: []`，`has_more: false` |
| `offset` 超过 `total` | 200，`items: []`，`has_more: false` |
| DB 异常 | 500（现有全局异常处理） |

---

## 架构

### 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `server/api/shared.py` | 通用 `Paginated[T]` Pydantic 泛型模型 |
| 新建 | `server/db_repositories/search.py` | `SearchRepository`，封装食品和配料的 ILIKE 搜索查询 |
| 修改 | `server/api/search/router.py` | 新增 `GET /api/search` 端点 |
| 修改 | `server/api/search/service.py` | 新增 `UnifiedSearchService` |

### 数据流

```
GET /api/search?q=xx&type=all&offset=0&limit=20
  └─ router.py（参数校验 + 依赖注入）
       └─ UnifiedSearchService.search()
            ├─ SearchRepository.search_foods(q)
            │    → SELECT foods WHERE name ILIKE '%q%'
            │    → JOIN analysis_details (overall_risk) 取 riskLevel
            │    → 子查询 COUNT 高风险配料 (ingredient_summary level IN t3/t4)
            ├─ SearchRepository.search_ingredients(q)
            │    → SELECT ingredients WHERE name ILIKE '%q%' OR q = ANY(alias)
            │    → JOIN analysis_details (ingredient_summary) 取 riskLevel
            ├─ Python 层合并（foods 在前，ingredients 在后）
            ├─ 按 type 过滤
            ├─ 统计 total
            └─ 截取 [offset : offset+limit] → Paginated[SearchResultItem]
```

### 通用分页模型（`server/api/shared.py`）

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

### 查询策略

- 食品：`foods.name ILIKE '%q%'`，软删除过滤 `deleted_at IS NULL`
- 配料：`ingredients.name ILIKE '%q%' OR q = ANY(ingredients.alias)`，软删除过滤
- 两次独立 SQLAlchemy 查询，Python 层合并后再做 offset/limit 切片
- 暂不添加 DB 索引（当前数据量小）；后续数据量增大可加 `pg_trgm` GIN 索引优化 ILIKE 性能

---

## 前端适配说明（不在本次后端任务范围）

- 筛选 chip 切换需重新发起请求（`type` 参数），不再客户端过滤
- 新搜索关键词时重置 `offset=0`，清空 `items` 累积列表
- 滚动到底判断 `has_more`：`true` 触发加载更多（`offset += limit`），`false` 显示"到底了"
