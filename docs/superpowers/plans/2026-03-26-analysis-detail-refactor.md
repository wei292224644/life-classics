# AnalysisDetail 数据结构重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `AnalysisDetail` 表的 `results` JSONB 字段拆分为独立的 `result` 字符串列，并删除冗余的审计字段。

**Architecture:** Append-only 设计，去掉 `last_updated_*`、`deleted_at`，新增 `result`（分析结论字符串）和 `source`（来源）字段，`level` 和 `confidence_score` 保留为顶层列。无旧数据，无需迁移。

**Tech Stack:** SQLAlchemy (Python), PostgreSQL (JSONB), Pydantic

---

## 新旧字段对照

| 旧字段 | 新字段 | 说明 |
|---|---|---|
| `results: dict` (JSONB) | `result: str` (Text) | 分析结论字符串 |
| — (新增) | `source: str \| None` (Text) | 来源，如 WHO 报告 |
| `level` | `level` (保留) | 风险等级 t0-t4 |
| `confidence_score` | `confidence_score` (保留) | 置信度 |
| `raw_output` | `raw_output` (保留) | 原始 LLM 输出 |
| `last_updated_at` | — (删除) | append-only 不需要 |
| `last_updated_by_user` | — (删除) | append-only 不需要 |
| `deleted_at` | — (删除) | 不需要软删除 |

---

## 文件变更映射

| 文件 | 职责 |
|---|---|
| `server/database/models.py` | 修改 `AnalysisDetail` 类定义 |
| `server/db_repositories/ingredient.py` | 改 `analysis["results"]` → `analysis["result"]` |
| `server/db_repositories/food.py` | 改 `AnalysisSummary` dataclass + `results` 引用 |
| `server/api/product/models.py` | 改 `results: dict` → `result: str` |
| `server/api/product/service.py` | 改 `a.results` → `a.result` |
| `server/scripts/seed_data.py` | 改 `results={...}` → `result="..."` |
| `server/db_repositories/seed_data.py` | 改 SQL 插入的 `results` → `result` |
| `tests/api/test_product.py` | 改 mock `AnalysisSummary(results=...)` → 新字段 |

---

## Task 1: 修改 `AnalysisDetail` 模型

**文件:** Modify: `server/database/models.py`

- [ ] **Step 1: 确认当前 `AnalysisDetail` 行号**

```bash
grep -n "class AnalysisDetail" server/database/models.py
```

- [ ] **Step 2: 修改 `AnalysisDetail` 类**

将原有类替换为：

```python
class AnalysisDetail(Base):
    __tablename__ = "analysis_details"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    analysis_target: Mapped[str] = mapped_column(analysis_target_enum, nullable=False)
    analysis_type: Mapped[str] = mapped_column(analysis_type_enum, nullable=False)
    analysis_version: Mapped[str] = mapped_column(analysis_version_enum, nullable=False)
    ai_model: Mapped[str] = mapped_column(String(255), nullable=False)

    result: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[str] = mapped_column(level_enum, nullable=False, default="unknown")
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)

    raw_output: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
```

- [ ] **Step 3: 验证语法**

```bash
cd server && uv run python -c "from database.models import AnalysisDetail; print('OK')"
```

---

## Task 2: 更新 Repository 层 — `ingredient.py`

**文件:** Modify: `server/db_repositories/ingredient.py`

- [ ] **Step 1: 确认 `analysis_data` 字典构造位置**

```bash
grep -n "results" server/db_repositories/ingredient.py
```

- [ ] **Step 2: 修改 `analysis_data` 字典**

将：
```python
analysis_data = {
    "id": a.id,
    "analysis_type": a.analysis_type,
    "results": a.results,
    "level": a.level,
}
```

改为：
```python
analysis_data = {
    "id": a.id,
    "analysis_type": a.analysis_type,
    "result": a.result,
    "source": a.source,
    "level": a.level,
    "confidence_score": a.confidence_score,
}
```

- [ ] **Step 3: 验证语法**

```bash
cd server && uv run python -c "from db_repositories.ingredient import IngredientRepository; print('OK')"
```

---

## Task 3: 更新 Repository 层 — `food.py`

**文件:** Modify: `server/db_repositories/food.py`

- [ ] **Step 1: 确认所有 `results` 引用位置**

```bash
grep -n "results" server/db_repositories/food.py
```

- [ ] **Step 2: 修改 `AnalysisSummary` dataclass**

将：
```python
@dataclass
class AnalysisSummary:
    id: int
    analysis_type: str
    results: dict
    level: str
```

改为：
```python
@dataclass
class AnalysisSummary:
    id: int
    analysis_type: str
    result: str
    source: str | None
    level: str
    confidence_score: int
```

- [ ] **Step 3: 修改所有 `AnalysisSummary` 构造**

将所有：
```python
AnalysisSummary(id=a.id, analysis_type=a.analysis_type, results=a.results, level=a.level)
```

改为：
```python
AnalysisSummary(id=a.id, analysis_type=a.analysis_type, result=a.result, source=a.source, level=a.level, confidence_score=a.confidence_score)
```

- [ ] **Step 4: 删除 `raw_results.get("reason")` 逻辑**（约第 112 行）

原本：
```python
raw_results = ing_analysis.results
reason = raw_results.get("reason") if isinstance(raw_results, dict) else None
```

删除这段（`result` 已是完整结论字符串，无需再提取 `reason`）。

- [ ] **Step 5: 验证语法**

```bash
cd server && uv run python -c "from db_repositories.food import FoodRepository; print('OK')"
```

---

## Task 4: 更新 API Models

**文件:** Modify: `server/api/product/models.py`

- [ ] **Step 1: 修改 `IngredientAnalysis`**

将：
```python
class IngredientAnalysis(BaseModel):
    id: int
    analysis_type: str
    results: dict
    level: RiskLevel
```

改为：
```python
class IngredientAnalysis(BaseModel):
    id: int
    analysis_type: str
    result: str
    source: str | None
    level: RiskLevel
    confidence_score: int
```

- [ ] **Step 2: 修改 `AnalysisResponse`**

将：
```python
class AnalysisResponse(BaseModel):
    analysis_type: str
    results: dict
```

改为：
```python
class AnalysisResponse(BaseModel):
    analysis_type: str
    result: str
    source: str | None
    level: RiskLevel
    confidence_score: int
```

- [ ] **Step 3: 验证语法**

```bash
cd server && uv run python -c "from api.product.models import IngredientAnalysis, AnalysisResponse; print('OK')"
```

---

## Task 5: 更新 API Service

**文件:** Modify: `server/api/product/service.py`

- [ ] **Step 1: 修改 `ProductService._to_product_response`**

将：
```python
analysis=[
    {
        "analysis_type": a.analysis_type,
        "results": a.results,
    }
    for a in d.analysis
],
```

改为：
```python
analysis=[
    {
        "analysis_type": a.analysis_type,
        "result": a.result,
        "source": a.source,
        "level": a.level,
        "confidence_score": a.confidence_score,
    }
    for a in d.analysis
],
```

- [ ] **Step 2: 修改 `IngredientService._to_ingredient_response`**

将：
```python
analysis_data = {
    "id": d.analysis["id"],
    "analysis_type": d.analysis["analysis_type"],
    "results": d.analysis["results"],
    "level": RiskLevel.from_str(d.analysis["level"]),
}
```

改为：
```python
analysis_data = {
    "id": d.analysis["id"],
    "analysis_type": d.analysis["analysis_type"],
    "result": d.analysis["result"],
    "source": d.analysis.get("source"),
    "level": RiskLevel.from_str(d.analysis["level"]),
    "confidence_score": d.analysis["confidence_score"],
}
```

- [ ] **Step 3: 验证语法**

```bash
cd server && uv run python -c "from api.product.service import ProductService, IngredientService; print('OK')"
```

---

## Task 6: 更新 Seed 脚本

**文件:** Modify: `server/scripts/seed_data.py`

- [ ] **Step 1: 修改 `make_analysis_detail` 函数中 `AnalysisDetail` 构造**

将：
```python
results={
    "summary": fake.text(max_nb_chars=200),
    "risk_level": fake.random_element(levels),
    "reason": fake.random_element(reasons),
    "health_benefit": fake.random_element(health_benefits),
    "advice": fake.sentence(nb_words=20),
    "risk_factors": [rf for rf in risk_factors if rf],
    "suggestions": suggestions,
},
level=fake.random_element(levels),
confidence_score=fake.random_int(min=60, max=99),
```

改为：
```python
result=fake.text(max_nb_chars=200),
source=fake.random_element(["WHO食品添加剂评估", "FAO/JECFA报告", "EFSA评估报告"]) if fake.random.random() > 0.3 else None,
level=fake.random_element(levels),
confidence_score=fake.random_int(min=60, max=99),
```

- [ ] **Step 2: 验证语法**

```bash
cd server && uv run python -c "from scripts.seed_data import make_analysis_detail; print('OK')"
```

---

## Task 7: 更新 DB Seed Repository

**文件:** Modify: `server/db_repositories/seed_data.py`

- [ ] **Step 1: 修改 `upsert_analysis` 函数中的 SQL**

将：
```python
results_json = json.dumps({"summary": "mock summary", "reason": "mock reason"})
# ...
INSERT INTO analysis_details ... results ...
VALUES ... CAST(:results AS JSONB) ...
```

改为：
```python
result_text = "mock summary"
source_text = "WHO mock source"
# ...
INSERT INTO analysis_details ... result, source ...
VALUES ... :result, :source ...
```

- [ ] **Step 2: 验证语法**

```bash
cd server && uv run python -c "from db_repositories.seed_data import upsert_analysis; print('OK')"
```

---

## Task 8: 更新测试 Mock 数据

**文件:** Modify: `tests/api/test_product.py`

- [ ] **Step 1: 确认 mock 数据位置**

```bash
grep -n "results=" tests/api/test_product.py
```

- [ ] **Step 2: 修改所有 `AnalysisSummary(results=...)` 为新字段**

将：
```python
AnalysisSummary(
    id=1,
    analysis_type="health_summary",
    results={"summary": "普通零食"},
    level="t1",
)
```

改为：
```python
AnalysisSummary(
    id=1,
    analysis_type="health_summary",
    result="普通零食",
    source="WHO评估报告",
    level="t1",
    confidence_score=85,
)
```

- [ ] **Step 3: 运行测试**

```bash
cd server && uv run pytest tests/api/test_product.py -v
```

---

## Task 9: 清理数据库表（重建）

> ⚠️ 仅在本地开发环境执行此步骤。生产环境请联系 DBA 处理。

- [ ] **Step 1: 确认无旧数据**

如果使用 `reset_db.py` 重建数据库，SQLAlchemy 会自动按新模型重建表（无 `results`，有 `result`）。

```bash
cd server && python scripts/reset_db.py --rebuild
```

---

## Task 10: 提交变更

- [ ] **Step 1: Git 状态检查**

```bash
git status
```

- [ ] **Step 2: 提交**

```bash
git add server/database/models.py server/db_repositories/ingredient.py server/db_repositories/food.py server/api/product/models.py server/api/product/service.py server/scripts/seed_data.py server/db_repositories/seed_data.py tests/api/test_product.py
git commit -m "refactor(analysis-detail):拆解results JSONB为独立result列并精简冗余字段

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 验证清单

- [ ] `AnalysisDetail.results` 已删除，新增 `result` (Text) 和 `source` (Text)
- [ ] `last_updated_at`、`last_updated_by_user`、`deleted_at` 已删除
- [ ] `level` 和 `confidence_score` 保留为顶层列
- [ ] `raw_output` 保留
- [ ] Repository 层所有 `results` 引用已更新
- [ ] API Models 的 `results: dict` 已改为 `result: str`
- [ ] Seed 数据结构已更新
- [ ] 测试通过
- [ ] Commit 完成
