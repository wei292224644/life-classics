# 配料管理 Admin CRUD 设计

## 背景

`Ingredient` 主表目前只有 Read 端点（`GET /ingredient/{ingredient_id}`），缺少管理员维度的增删改查能力。本设计补充管理员 API，支持：
- 管理员对配料数据的增删改查
- Create 支持 upsert 语义（按名称匹配，已存在则字段级合并）
- Delete 为软删除

> alias 管理不在本设计范围内，由其他流程处理。

## 端点设计

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/ingredients` | 创建配料（Upsert） |
| `GET` | `/ingredients` | 列表查询（分页 + 过滤） |
| `GET` | `/ingredients/{id}` | 获取单个配料 |
| `PUT` | `/ingredients/{id}` | 全量更新 |
| `PATCH` | `/ingredients/{id}` | 部分更新 |
| `DELETE` | `/ingredients/{id}` | 软删除 |

## 详细设计

### 1. Create — POST /admin/ingredients

**请求体：**
```json
{
  "name": "蔗糖",
  "description": "常见的食糖类型",
  "is_additive": false,
  "additive_code": null,
  "standard_code": "GB 13104",
  "who_level": "Unknown",
  "allergen_info": [],
  "function_type": [],
  "origin_type": "植物",
  "limit_usage": null,
  "legal_region": "中国",
  "cas": "57-50-1",
  "applications": "调味",
  "notes": null,
  "safety_info": "安全"
}
```

**行为（Upsert）：**
1. 按 `name` 精确匹配查找 `Ingredient` 表
2. **存在** → 字段级合并：只更新请求中提供的**非空字段**（`null`/`[]` 不覆盖已有值），保留其他字段原值
3. **不存在** → 新建，所有字段使用请求值

**响应：**
- `201 Created` — 新建返回完整对象
- `200 OK` — 合并更新返回完整对象

### 2. List — GET /admin/ingredients

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | int | 每页条数，默认 20，最大 100 |
| `offset` | int | 跳过条数，默认 0 |
| `name` | string | 按名称模糊搜索 |
| `is_additive` | bool | 按是否添加剂过滤 |

**响应：**
```json
{
  "items": [{ /* IngredientResponse */ }],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

**行为：** 默认过滤掉 `deleted_at IS NOT NULL` 的记录。

### 3. Get — GET /admin/ingredients/{id}

返回单个配料完整信息，已删除返回 404。

### 4. Update (Full) — PUT /admin/ingredients/{id}

全量更新，所有字段使用请求值，未传字段置为 `null` 或默认值。

### 5. Update (Partial) — PATCH /admin/ingredients/{id}

字段级更新，只更新请求中提供的非空字段，保留其他字段原值。

### 6. Delete — DELETE /admin/ingredients/{id}

软删除：设置 `deleted_at` 为当前时间戳。已删除再次删除返回 204。

## 数据模型

`Ingredient` 字段一览（来自 `database/models.py`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String(255) | 名称 |
| `description` | Text | 描述 |
| `is_additive` | Boolean | 是否为添加剂 |
| `additive_code` | String(50) | 添加剂编码 |
| `standard_code` | String(255) | 国标编号 |
| `who_level` | String | WHO 致癌等级 |
| `allergen_info` | Array(String) | 过敏信息 |
| `function_type` | Array(String) | 功能类型 |
| `origin_type` | String(100) | 来源类型 |
| `limit_usage` | String(255) | 使用限量 |
| `legal_region` | String(255) | 法规适用区域 |
| `cas` | String(50) | CAS 号 |
| `applications` | String(500) | 应用场景 |
| `notes` | Text | 注意事项 |
| `safety_info` | Text | 安全性信息 |
| `meta` | JSONB | 扩展字段 |

## 响应模型

使用 Pydantic 模型，与现有 `IngredientResponse` 保持一致：

```python
class IngredientResponse(BaseModel):
    id: int
    name: str
    alias: list[str]           # 保留，与前端兼容
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
    analyses: list[AnalysisResponse]
    related_products: list[RelatedProductSimple]
```

> `alias`、`analyses`、`related_products` 为只读计算字段，管理员编辑时无需填写。

## 认证与权限

当前标记为 `admin_only`，鉴权机制待确认（可在后续迭代中补充 middleware）。

## 文件结构

```
server/
├── api/
│   └── admin/
│       ├── __init__.py
│       ├── ingredient.py      # 路由定义
│       └── models.py          # 请求/响应模型
├── db_repositories/
│   └── ingredient_admin.py    # Repository 类（admin 专用查询）
└── services/
    └── ingredient_admin.py    # Service 类
```

## 错误处理

| 场景 | 状态码 |
|------|--------|
| 配料不存在 | 404 |
| 创建/更新参数校验失败 | 422 |
| 已删除配料再次删除 | 204（幂等） |

## 测试策略

- API 层：CRUD 端点全覆盖
- Repository 层：upsert 逻辑（存在/不存在两种路径）
- Service 层：字段级合并逻辑
