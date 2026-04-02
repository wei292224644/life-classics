# 审计报告：Section VII（异步边界）& Section X（命名契约）

**审计日期**：2026-04-02
**审计范围**：`server/` — db_repositories/ & api/*/
**规范文件**：`docs/architecture/server-architecture.md`

---

## Section VII — 异步边界

### L3 (db_repositories/) 所有方法必须是 async

| 文件 | 类 | 公开方法数 | 全部为 async | 违规 |
|------|----|-----------|-------------|------|
| `db_repositories/ingredient_alias.py` | `IngredientAliasRepository` | 7 | ✅ | 无 |
| `db_repositories/product_analysis.py` | `ProductAnalysisRepository` | 2 | ✅ | 无 |
| `db_repositories/food.py` | `FoodRepository` | 1 | ✅ | 无 |
| `db_repositories/ingredient.py` | `IngredientRepository` | 6 | ✅ | 无 |
| `db_repositories/ingredient_analysis.py` | `IngredientAnalysisRepository` | 3 | ✅ | 无 |
| `db_repositories/search.py` | `SearchRepository` | 2 | ✅ | 无 |

### L2 调用 L3 时必须 await

Services 层（`api/*/service.py`）均通过 `await` 调用各 Repository 方法，经抽查确认符合规范。

### 禁止在 async 函数中直接调用同步基础设施

`db_repositories/` 下未发现直接调用同步基础设施（如同步 fts_writer）的违规。

### 结论

**未发现 Section VII 异步边界违规。**

---

## Section X — 命名契约

### 类名模式检查

| 文件路径 | 类名 | 预期模式 | 符合 | 违规 |
|---------|------|---------|------|------|
| `db_repositories/ingredient_alias.py` | `IngredientAliasRepository` | `XxxRepository` | ✅ | 无 |
| `db_repositories/product_analysis.py` | `ProductAnalysisRepository` | `XxxRepository` | ✅ | 无 |
| `db_repositories/food.py` | `FoodRepository` | `XxxRepository` | ✅ | 无 |
| `db_repositories/ingredient.py` | `IngredientRepository` | `XxxRepository` | ✅ | 无 |
| `db_repositories/ingredient_analysis.py` | `IngredientAnalysisRepository` | `XxxRepository` | ✅ | 无 |
| `db_repositories/search.py` | `SearchRepository` | `XxxRepository` | ✅ | 无 |
| `api/documents/service.py` | `DocumentsService` | `XxxService` | ✅ | 无 |
| `api/ingredients/service.py` | `IngredientService` | `XxxService` | ✅ | 无 |
| `api/chunks/service.py` | `ChunksService` | `XxxService` | ✅ | 无 |
| `api/product/service.py` | `ProductService` | `XxxService` | ✅ | 无 |
| `api/ingredient_alias/service.py` | `IngredientAliasService` | `XxxService` | ✅ | 无 |
| `api/kb/service.py` | `KBService` | `XxxService` | ✅ | 无 |
| `api/ingredient_analysis/service.py` | `IngredientAnalysisService` | `XxxService` | ✅ | 无 |
| `api/analysis/service.py` | `AnalysisError`（异常类） | — | ✅ | 无 |
| `api/analysis/ocr_client.py` | `OcrServiceError`（异常类） | — | ✅ | 无 |

### 禁止在 api/*/ 下创建与 db_repositories/* 同名的类

逐一比对 `db_repositories/` 中的类名与 `api/*/` 中所有公开类名，无任何冲突：

- `db_repositories/`：`IngredientRepository`、`FoodRepository`、`SearchRepository`、`IngredientAliasRepository`、`IngredientAnalysisRepository`、`ProductAnalysisRepository`
- `api/*/`：`IngredientService`、`FoodRepository` 等同名单独核查均不存在冲突

### 结论

**未发现 Section X 命名契约违规。**

---

## 综合结论

**✅ 未发现违规。**

Section VII（异步边界）和 Section X（命名契约）两项规范审计均通过：
- 所有 L3 Repository 公开方法均为 `async def`
- 所有 Service 类命名符合 `XxxService` 模式
- 所有 Repository 类命名符合 `XxxRepository` 模式
- api/*/ 下无与 db_repositories/* 同名的类
