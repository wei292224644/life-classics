# Seed 数据重设计规范

## 背景

原有 `server/scripts/seed_data.py` 依照旧数据库结构生成种子数据。新数据库模型（`server/database/models.py`）新增了 `IngredientAlias`、`IarcAgent`、`IarcCancerSite`、`IarcAgentLink` 等表，并移除了部分旧字段。需要同步更新 seed 脚本。

## 需求确认

- **生成 AnalysisDetail**：否
- **生成 IngredientAlias**：是（每配料 0~3 个别名）
- **生成 IARC 相关表**：是（模拟数据，但数量大幅减少）
- **生成 IngredientAnalysis / ProductAnalysis**：否
- **生成 AnalysisFeedback**：否

## 生成数据范围

| 表 | 记录数 | 备注 |
|---|---|---|
| `Food` | 50 | 保持不变 |
| `Ingredient` | 80 | 保持不变 |
| `FoodIngredient` | 每食品 5~15 条 | 保持不变 |
| `NutritionTable` | 15 | 减少（原 30） |
| `FoodNutritionEntry` | 每食品 8~20 条 | 保持不变 |
| `IngredientAlias` | 每配料 0~3 条 | 新增 |
| `IarcAgent` | 10 | 大幅减少（原计划 30） |
| `IarcCancerSite` | 5 | 大幅减少（原计划 15） |
| `IarcAgentLink` | 每 Agent 0~2 条 | 新增 |
| `AnalysisDetail` | 0 | 明确跳过 |
| `IngredientAnalysis` | 0 | 明确跳过 |
| `ProductAnalysis` | 0 | 明确跳过 |
| `AnalysisFeedback` | 0 | 明确跳过 |

## 实现要点

### 公共策略
- 固定 `Faker.seed(42)` 保证每次运行生成相同数据
- 所有随机关联使用 `random.seed(x)` 基于主键 ID，保证可复现
- `deleted_at` 字段全部为 `NULL`（未删除状态）
- 使用 `Faker("zh_CN")` 生成中文数据

### IngredientAlias 生成规则
```python
for ingredient_id in ingredient_ids:
    alias_count = random.randint(0, 3)
    for _ in range(alias_count):
        alias_name = fake.name()  # 随机姓名作为别名
        aliases.append(IngredientAlias(
            ingredient_id=ingredient_id,
            alias=alias_name,
            normalized_alias=alias_name,  # 简化处理
            alias_type=fake.random_element(["chinese", "english", "abbr"]),
        ))
```

### IarcAgent 生成规则
- `cas_no`: 格式 `XXXXX-XX-X` 的随机 CAS 号
- `agent_name`: 随机化学物质名称
- `zh_agent_name`: 随机中文译名
- `group`: 随机 IARC 分组 `["1", "2A", "2B", "3", "unknown"]`
- `volume`: 格式 `Volume XX`
- `volume_publication_year`: `1900-2024` 之间的随机年份
- `evaluation_year`: 同上

### IarcCancerSite 生成规则
- `name`: 英文癌症部位名称（如 "Lung", "Liver"）
- `zh_name`: 对应中文
- `sufficient_evidence_agents` / `limited_evidence_agents`: 用 ARRAY 字段存储随机 agent ID 列表（数量 0~3）

### IarcAgentLink 生成规则
- `from_agent_id` → `to_agent_id` 随机选择
- `link_type`: `see` 或 `see_also`

### 清空表顺序（外键依赖）
```python
await session.execute(delete(FoodNutritionEntry))
await session.execute(delete(FoodIngredient))
await session.execute(delete(Food))  # AnalysisDetail 已移除
await session.execute(delete(Ingredient))
await session.execute(delete(NutritionTable))
await session.execute(delete(IngredientAlias))
await session.execute(delete(IarcAgentLink))
await session.execute(delete(IarcCancerSite))
await session.execute(delete(IarcAgent))
```

## 文件变更

- `server/scripts/seed_data.py` — 重写数据生成逻辑
