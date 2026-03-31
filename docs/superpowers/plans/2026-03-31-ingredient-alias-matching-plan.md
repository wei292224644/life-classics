# Ingredient Alias Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现配料别名匹配能力，通过别名精确匹配代替向量检索，解决真实食品配料表名称与标准配料库不一致的问题。

**Architecture:** 新增 `ingredient_aliases` 表存储别名映射，`match_ingredients()` 函数简化为：预处理 → 别名精确匹配 → 未命中标记为 unmatched。

**Tech Stack:** SQLAlchemy async, PostgreSQL

---

## 文件结构

```
server/
├── database/
│   ├── models.py                    # 修改：新增 IngredientAlias
│   └── __init__.py                  # 修改：导出 IngredientAlias
│
├── db_repositories/
│   ├── __init__.py                  # 修改：导出 IngredientAliasRepository
│   └── ingredient_alias.py           # 新增：别名 CRUD + normalize_ingredient_name
│
├── workflow_product_analysis/
│   ├── ingredient_matcher.py        # 修改：移除向量检索，改用别名匹配
│   └── types.py                     # 已有（MatchResult 等）
│
└── tests/
    └── workflow_product_analysis/
        ├── test_ingredient_alias.py          # 新增：别名仓库单元测试
        └── test_ingredient_matcher.py       # 修改：别名匹配集成测试
```

---

## Task 1: 创建 IngredientAlias ORM Model

**Files:**
- Modify: `server/database/models.py`
- Modify: `server/database/__init__.py`

- [ ] **Step 1: 在 `models.py` 末尾添加 IngredientAlias model**

```python
class IngredientAlias(Base):
    """配料别名表 — 别名到标准配料的精确映射."""
    __tablename__ = "ingredient_aliases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    alias_type: Mapped[str] = mapped_column(String(50), default="chinese")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
```

- [ ] **Step 2: 在 `database/__init__.py` 中导出 IngredientAlias**

在 `__all__` 列表中添加 `"IngredientAlias"`。

- [ ] **Step 3: 运行迁移生成表**

```bash
cd server && uv run alembic revision --autogenerate -m "add ingredient_aliases table"
cd server && uv run alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add server/database/models.py server/database/__init__.py
git commit -m "feat(db): add IngredientAlias model and ingredient_aliases table"
```

---

## Task 2: 创建别名仓库 `ingredient_alias.py`

**Files:**
- Create: `server/db_repositories/ingredient_alias.py`
- Modify: `server/db_repositories/__init__.py`

- [ ] **Step 1: 编写测试 `test_ingredient_alias.py`**

```python
# server/tests/workflow_product_analysis/test_ingredient_alias.py
import pytest
from sqlalchemy import select
from db_repositories.ingredient_alias import IngredientAliasRepository, normalize_ingredient_name
from database.models import Ingredient, IngredientAlias

pytestmark = pytest.mark.asyncio


class TestNormalizeIngredientName:
    def test_remove_parentheses(self):
        assert normalize_ingredient_name("焦糖色（着色剂）") == "焦糖色"
        assert normalize_ingredient_name("碳酸氢钠（小苏打）") == "碳酸氢钠"

    def test_english_lowercase(self):
        assert normalize_ingredient_name("SUCROSE") == "sucrose"
        assert normalize_ingredient_name("LECITHIN") == "lecithin"

    def test_strip_whitespace(self):
        assert normalize_ingredient_name("  蔗糖  ") == "蔗糖"

    def test_remove_edible_prefix(self):
        assert normalize_ingredient_name("食用盐") == "盐"
        assert normalize_ingredient_name("食用色素") == "色素"


class TestIngredientAliasRepository:
    async def test_find_by_alias_found(self, session):
        # 先创建一个 Ingredient
        ingredient = Ingredient(name="蔗糖", alias=["白砂糖"], is_additive=False)
        session.add(ingredient)
        await session.flush()

        # 创建别名
        alias = IngredientAlias(ingredient_id=ingredient.id, alias="白砂糖")
        session.add(alias)
        await session.commit()

        # 查询
        result = await IngredientAliasRepository.find_by_alias("白砂糖")
        assert result is not None
        assert result.ingredient_id == ingredient.id

    async def test_find_by_alias_not_found(self, session):
        result = await IngredientAliasRepository.find_by_alias("不存在的别名")
        assert result is None

    async def test_find_by_ingredient_id(self, session):
        ingredient = Ingredient(name="蔗糖", alias=[], is_additive=False)
        session.add(ingredient)
        await session.flush()

        session.add(IngredientAlias(ingredient_id=ingredient.id, alias="白砂糖"))
        session.add(IngredientAlias(ingredient_id=ingredient.id, alias="食糖"))
        await session.commit()

        aliases = await IngredientAliasRepository.find_by_ingredient_id(ingredient.id)
        assert len(aliases) == 2

    async def test_create_alias(self, session):
        ingredient = Ingredient(name="焦糖色", alias=[], is_additive=True)
        session.add(ingredient)
        await session.flush()

        new_alias = await IngredientAliasRepository.create(
            alias="焦糖色素",
            ingredient_id=ingredient.id,
            alias_type="chinese",
            session=session,
        )
        await session.commit()

        assert new_alias.alias == "焦糖色素"
        assert new_alias.ingredient_id == ingredient.id

    async def test_create_duplicate_alias_raises(self, session):
        ingredient1 = Ingredient(name="蔗糖", alias=[], is_additive=False)
        ingredient2 = Ingredient(name="白砂糖", alias=[], is_additive=False)
        session.add(ingredient1)
        session.add(ingredient2)
        await session.flush()

        session.add(IngredientAlias(ingredient_id=ingredient1.id, alias="糖"))
        await session.commit()

        with pytest.raises(Exception):  # unique constraint violation
            await IngredientAliasRepository.create(
                alias="糖",
                ingredient_id=ingredient2.id,
                session=session,
            )
```

- [ ] **Step 2: 创建 `db_repositories/ingredient_alias.py`**

```python
"""配料别名仓库 — 别名精确匹配的核心逻辑."""
from __future__ import annotations

import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import IngredientAlias


# ── 预处理规则 ────────────────────────────────────────────────────────────────


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


# ── 仓库类 ─────────────────────────────────────────────────────────────────────


class IngredientAliasRepository:
    """配料别名仓库."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_alias(self, alias: str) -> IngredientAlias | None:
        """按别名精确查询（区分大小写，alias 列已建唯一索引）。"""
        result = await self._session.execute(
            select(IngredientAlias).where(IngredientAlias.alias == alias)
        )
        return result.scalar_one_or_none()

    async def find_by_normalized_alias(self, normalized_alias: str) -> IngredientAlias | None:
        """
        按标准化后的别名查询。

        注意：alias 列存储的是原始别名（非标准化后），
        查询时需要同时遍历和匹配，生产环境建议提前标准化存储。
        """
        normalized_target = normalize_ingredient_name(normalized_alias)
        result = await self._session.execute(select(IngredientAlias))
        for row in result.scalars().all():
            if normalize_ingredient_name(row.alias) == normalized_target:
                return row
        return None

    async def find_by_ingredient_id(self, ingredient_id: int) -> list[IngredientAlias]:
        """按配料 ID 查询所有别名."""
        result = await self._session.execute(
            select(IngredientAlias).where(IngredientAlias.ingredient_id == ingredient_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        alias: str,
        ingredient_id: int,
        alias_type: str = "chinese",
        session: AsyncSession | None = None,
    ) -> IngredientAlias:
        """创建新别名."""
        sess = session or self._session
        new_alias = IngredientAlias(
            alias=alias,
            ingredient_id=ingredient_id,
            alias_type=alias_type,
        )
        sess.add(new_alias)
        await sess.flush()
        return new_alias

    async def delete(self, alias_id: int) -> bool:
        """删除别名，返回是否删除成功."""
        result = await self._session.execute(
            select(IngredientAlias).where(IngredientAlias.id == alias_id)
        )
        alias = result.scalar_one_or_none()
        if alias is None:
            return False
        await self._session.delete(alias)
        return True
```

- [ ] **Step 3: 更新 `db_repositories/__init__.py`**

```python
from db_repositories.food import FoodRepository
from db_repositories.ingredient import IngredientRepository
from db_repositories.ingredient_alias import IngredientAliasRepository
from db_repositories.product_analysis import get_by_food_id, insert_if_absent
from db_repositories.ingredient_analysis import (
    get_active_by_ingredient_id,
    get_history_by_ingredient_id,
    insert_new_version,
)

__all__ = [
    "FoodRepository",
    "IngredientRepository",
    "IngredientAliasRepository",
    "get_by_food_id",
    "insert_if_absent",
    "get_active_by_ingredient_id",
    "get_history_by_ingredient_id",
    "insert_new_version",
]
```

- [ ] **Step 4: 运行测试验证**

```bash
cd server && uv run pytest tests/workflow_product_analysis/test_ingredient_alias.py -v
```

- [ ] **Step 5: Commit**

```bash
git add server/db_repositories/ingredient_alias.py server/db_repositories/__init__.py
git add server/tests/workflow_product_analysis/test_ingredient_alias.py
git commit -m "feat(db): add IngredientAliasRepository with CRUD and normalize_ingredient_name"
```

---

## Task 3: 修改 `ingredient_matcher.py` 集成别名匹配

**Files:**
- Modify: `server/workflow_product_analysis/ingredient_matcher.py`
- Modify: `server/tests/workflow_product_analysis/test_ingredient_matcher.py`

- [ ] **Step 1: 查看当前 matcher 实现，了解需要改什么**

当前实现使用向量检索（`embed_batch` + ChromaDB）。需要：
- 移除向量检索依赖
- 改为调用 `IngredientAliasRepository.find_by_normalized_alias()`
- 保留 `fetch_ingredient_details()` 获取配料详情和 level

- [ ] **Step 2: 重写 `match_ingredients()` 函数**

新的实现：

```python
"""组件 3：成分匹配 — 将成分名通过别名精确匹配到配料库。"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db_repositories.ingredient_alias import (
    IngredientAliasRepository,
    normalize_ingredient_name,
)
from db_repositories.ingredient_analysis import get_active_by_ingredient_id
from database.models import Ingredient
from workflow_product_analysis.types import (
    IngredientRiskLevel,
    MatchedIngredient,
    MatchResult,
)

if TYPE_CHECKING:
    pass


async def match_ingredients(
    ingredient_names: list[str],
    session: AsyncSession,
) -> MatchResult:
    """
    将成分名列表通过别名精确匹配到配料库（ingredients 表）。

    入参：
        ingredient_names: 原始成分名列表（来自 OCR 解析）
        session: AsyncSession

    出参：
        MatchResult: {matched: [...], unmatched: [...]}：
        - matched: 匹配成功的成分（含 ingredient_id、name、level）
        - unmatched: 匹配失败的原始成分名
    """
    if not ingredient_names:
        return MatchResult(matched=[], unmatched=[])

    repo = IngredientAliasRepository(session)

    async def find_match(name: str) -> tuple[str, MatchedIngredient | None]:
        normalized = normalize_ingredient_name(name)
        alias_record = await repo.find_by_normalized_alias(normalized)

        if alias_record is None:
            return name, None

        ingredient_id = alias_record.ingredient_id
        details = await fetch_ingredient_details(ingredient_id, session)
        if details is None:
            return name, None

        name_db, category_str, level = details
        return name, MatchedIngredient(
            ingredient_id=ingredient_id,
            name=name_db,
            level=level,
        )

    results = await asyncio.gather(*[find_match(name) for name in ingredient_names])

    matched = [m for _, m in results if m is not None]
    unmatched = [name for name, m in results if m is None]

    return MatchResult(matched=matched, unmatched=unmatched)


async def fetch_ingredient_details(
    ingredient_id: int,
    session: AsyncSession,
) -> tuple[str, str, IngredientRiskLevel] | None:
    """
    按 ingredient_id 查 DB，返回 (name, category_str, level)。

    category_str: function_type 数组拼接，如 "增稠剂 · 高升糖指数"
    level: 来自 active IngredientAnalysis；无记录则返回 "unknown"
    """
    result = await session.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id)
    )
    ingredient = result.scalar_one_or_none()

    if ingredient is None:
        return None

    function_types: list[str] = ingredient.function_type or []
    category_str = " · ".join(function_types)

    analysis = await get_active_by_ingredient_id(ingredient_id, session)
    if analysis is not None:
        level: IngredientRiskLevel = analysis.level
    else:
        level = "unknown"

    return ingredient.name, category_str, level
```

- [ ] **Step 3: 更新测试文件**

替换原有的向量检索测试为别名匹配测试：

```python
# server/tests/workflow_product_analysis/test_ingredient_matcher.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from workflow_product_analysis.ingredient_matcher import (
    match_ingredients,
    normalize_ingredient_name,
)
from workflow_product_analysis.types import MatchResult

pytestmark = pytest.mark.asyncio


class TestNormalizeIngredientName:
    """预处理规则测试."""

    def test_remove_parentheses(self):
        assert normalize_ingredient_name("焦糖色（着色剂）") == "焦糖色"

    def test_english_lowercase(self):
        assert normalize_ingredient_name("SUCROSE") == "sucrose"

    def test_strip_whitespace(self):
        assert normalize_ingredient_name("  蔗糖  ") == "蔗糖"

    def test_remove_edible_prefix(self):
        assert normalize_ingredient_name("食用盐") == "盐"

    def test_combined(self):
        assert normalize_ingredient_name("  食用碳酸氢钠（小苏打）  ") == "碳酸氢钠"


class TestMatchIngredients:
    async def test_alias_match_success(self, session):
        """别名匹配成功."""
        from database.models import Ingredient, IngredientAlias

        ingredient = Ingredient(name="蔗糖", alias=[], is_additive=False)
        session.add(ingredient)
        await session.flush()

        session.add(IngredientAlias(ingredient_id=ingredient.id, alias="白砂糖"))
        await session.commit()

        result = await match_ingredients(["白砂糖"], session)
        assert result.matched[0].name == "蔗糖"
        assert result.unmatched == []

    async def test_alias_unmatched(self, session):
        """别名未命中."""
        result = await match_ingredients(["完全不存在的配料"], session)
        assert result.unmatched == ["完全不存在的配料"]
        assert result.matched == []

    async def test_mixed_matches(self, session):
        """混合场景：部分匹配成功."""
        from database.models import Ingredient, IngredientAlias

        ingredient = Ingredient(name="蔗糖", alias=[], is_additive=False)
        session.add(ingredient)
        await session.flush()

        session.add(IngredientAlias(ingredient_id=ingredient.id, alias="白砂糖"))
        await session.commit()

        result = await match_ingredients(["白砂糖", "不存在的配料"], session)
        assert len(result.matched) == 1
        assert result.matched[0].name == "蔗糖"
        assert result.unmatched == ["不存在的配料"]

    async def test_empty_input(self, session):
        """空输入."""
        result = await match_ingredients([], session)
        assert result.matched == []
        assert result.unmatched == []
```

- [ ] **Step 4: 运行测试验证**

```bash
cd server && uv run pytest tests/workflow_product_analysis/test_ingredient_matcher.py -v
```

- [ ] **Step 5: Commit**

```bash
git add server/workflow_product_analysis/ingredient_matcher.py
git add server/tests/workflow_product_analysis/test_ingredient_matcher.py
git commit -m "refactor(ingredient_matcher): replace vector search with alias matching"
```

---

## Task 4: 清理向量检索相关代码

**Files:**
- 可能需要清理：`server/kb/embeddings.py`（如果 `embed_batch` 只被 matcher 使用）
- 检查：`server/config.py` 中的 `INGREDIENT_MATCH_THRESHOLD` 是否可移除

- [ ] **Step 1: 检查 `embed_batch` 使用情况**

```bash
cd server && grep -r "embed_batch" --include="*.py" .
```

- [ ] **Step 2: 如果 `embed_batch` 只被 matcher 使用，移除它**

- [ ] **Step 3: 检查 `INGREDIENT_MATCH_THRESHOLD` 使用情况**

```bash
cd server && grep -r "INGREDIENT_MATCH_THRESHOLD" --include="*.py" .
```

- [ ] **Step 4: Commit 清理**

```bash
git add ...
git commit -m "chore: remove unused ingredient vector search code"
```

---

## 自检清单

### Spec 覆盖检查
- [x] `ingredient_aliases` 表创建 — Task 1
- [x] `IngredientAlias` ORM model — Task 1
- [x] 别名仓库 CRUD — Task 2
- [x] `normalize_ingredient_name()` 预处理规则 — Task 2
- [x] Matcher 集成别名匹配 — Task 3
- [x] 移除向量检索 — Task 3
- [x] 测试覆盖 — Task 2 & Task 3

### 类型一致性检查
- `normalize_ingredient_name()` 输入输出均为 `str`
- `IngredientAliasRepository` 方法签名与 spec 一致
- `match_ingredients()` 返回 `MatchResult` TypedDict
- `MatchedIngredient` 结构 `{ingredient_id, name, level}` 与现有类型一致

### 占位符检查
- 无 `TBD` / `TODO` / `FIXME`
- 所有测试有实际断言
- 所有函数有文档字符串

---

## 种子数据（可选）

初始别名数据可手动录入，或创建迁移脚本：

```python
# migrations/seed_ingredient_aliases.py
ALIASES = [
    ("蔗糖", "白砂糖"),
    ("蔗糖", "食糖"),
    ("碳酸氢钠", "小苏打"),
    ("碳酸氢钠", "焙碱"),
    ("氯化钠", "食盐"),
    ("食用盐", "盐"),
    # ... 更多
]
```
