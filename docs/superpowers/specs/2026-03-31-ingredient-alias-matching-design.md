# Ingredient Alias Matching Design

**Date:** 2026-03-31
**Status:** Approved
**Scope:** 配料别名匹配能力，解决真实食品配料表名称与标准配料库不一致的问题

---

## 1. 目标与边界

### 1.1 In Scope

- 新增 `ingredient_aliases` 表存储配料别名
- 预处理规则层标准化原始配料名
- 别名精确匹配

### 1.2 Out of Scope

- 向量检索（本方案仅实现别名精确匹配）
- LLM fallback 匹配（未来扩展方向）
- 别名自动推荐/生成
- 跨语言翻译（英文 ↔ 中文由别名表覆盖，不做机器翻译）

---

## 2. 数据模型

### 2.1 新增表：`ingredient_aliases`

```sql
CREATE TABLE ingredient_aliases (
    id SERIAL PRIMARY KEY,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50) DEFAULT 'chinese',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alias)
);

CREATE INDEX idx_ingredient_aliases_alias ON ingredient_aliases(alias);
CREATE INDEX idx_ingredient_aliases_ingredient_id ON ingredient_aliases(ingredient_id);
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | SERIAL | 主键 |
| `ingredient_id` | INTEGER | 关联 `ingredients.id` |
| `alias` | VARCHAR(255) | 别名文本，唯一索引 |
| `alias_type` | VARCHAR(50) | 别名类型：`chinese` / `english` / `abbreviation` / `folk_name` |
| `created_at` | TIMESTAMP | 创建时间 |

### 2.2 ORM Model：`IngredientAlias`

```python
class IngredientAlias(Base):
    __tablename__ = "ingredient_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(255), unique=True)
    alias_type: Mapped[str] = mapped_column(String(50), default="chinese")
    created_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())
```

---

## 3. 预处理规则

匹配前对原始配料名做标准化：

| 规则 | 示例 | 处理后 |
|------|------|--------|
| 全角转半角 | "碳酸氢钠（小苏打）" | "碳酸氢钠（小苏打）" |
| 去除括号内容 | "焦糖色（着色剂）" | "焦糖色" |
| 英文小写 | "SUCROSE" | "sucrose" |
| 去除首尾空格 | "  蔗糖  " | "蔗糖" |
| 去除"食用"前缀 | "食用盐" | "盐" |

实现：`db_repositories/ingredient_alias.py` 中 `normalize_ingredient_name()` 函数。

---

## 4. 匹配流程

```
原始配料名列表
    ↓
[preprocess] 标准化
    ↓
[alias_match] 查询 ingredient_aliases（精确匹配标准化后的名称）
    ↓
[result] 匹配结果（matched / unmatched）
```

### 4.1 优先级

1. **预处理后别名精确匹配** — 唯一匹配方式

### 4.2 修改点

`match_ingredients()` 函数简化为：预处理 → 别名精确匹配 → 未命中标记为 unmatched。移除向量检索依赖。

---

## 5. 文件结构

```
server/
├── database/
│   ├── models.py                    # 修改：新增 IngredientAlias
│   └── __init__.py                  # 修改：导出 IngredientAlias
│
├── db_repositories/
│   ├── __init__.py                  # 修改：导出 ingredient_alias_repo
│   └── ingredient_alias.py          # 新增：别名 CRUD
│
├── workflow_product_analysis/
│   ├── ingredient_matcher.py        # 修改：集成别名匹配
│   └── types.py                     # 已有（MatchResult 等）
│
└── tests/
    └── workflow_product_analysis/
        ├── test_ingredient_matcher.py  # 修改：新增别名匹配测试
        └── test_ingredient_alias.py    # 新增：别名仓库单元测试
```

---

## 6. 别名仓库接口

```python
class IngredientAliasRepository:
    """配料别名仓库."""

    @staticmethod
    async def find_by_alias(alias: str) -> IngredientAlias | None:
        """按别名精确查询."""

    @staticmethod
    async def find_by_ingredient_id(ingredient_id: int) -> list[IngredientAlias]:
        """按配料 ID 查询所有别名."""

    @staticmethod
    async def create(alias: str, ingredient_id: int, alias_type: str = "chinese") -> IngredientAlias:
        """创建别名."""

    @staticmethod
    async def delete(alias_id: int) -> bool:
        """删除别名."""
```

---

## 7. 设计决策

| 决策 | 结论 | 原因 |
|------|------|------|
| 别名表 vs JSON 字段 | 单独表 | 1:N 关系，需独立索引，支持多类型扩展 |
| 别名唯一约束 | alias 唯一 | 防止重复录入，同一个别名不应指向多个配料 |
| 匹配方式 | 精确匹配（无模糊） | 保持简单和可解释，未来可扩展 LLM fallback |
| 向量检索 | 移除 | 当前方案仅用别名匹配，向量检索作为未来扩展 |

---

## 8. 测试策略

### 8.1 别名仓库测试

- `test_find_by_alias_found` — 精确匹配成功
- `test_find_by_alias_not_found` — 无匹配
- `test_find_by_ingredient_id` — 按配料 ID 查所有别名
- `test_create_duplicate_alias` — 重复别名唯一约束

### 8.2 Matcher 集成测试

- `test_normalize_before_alias_match` — 预处理规则生效
- `test_alias_match_success` — 别名匹配成功
- `test_alias_unmatched` — 别名未命中标记为 unmatched
- `test_mixed_matches` — 部分匹配成功部分未命中

---

## 9. 下一步

实现计划见：`docs/superpowers/plans/2026-03-31-ingredient-alias-matching-plan.md`
