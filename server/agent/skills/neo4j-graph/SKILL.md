---
name: neo4j-graph
description: 用于查询 GB2760_2024 知识图谱中的食品添加剂限量、功能分类、食品分类层级、香料、加工助剂、酶制剂等信息。当用户询问某添加剂在某食品中是否允许使用、最大使用量、具有哪些功能时使用。
allowed-tools: ["neo4j_query", "neo4j_vector_search"]
---

# Neo4j 图谱查询

## 概述

本技能采用**两阶段流程**查询 GB2760_2024 知识图谱：

1. **实体解析阶段**：调用 `neo4j_vector_search` 将用户的模糊表达（如"菜罐头"、"防腐剂"）解析为图谱中的精确节点（code 或 name）。
2. **结构化查询阶段**：用确认的精确标识符构建 Cypher，调用 `neo4j_query` 执行，获取限量、功能、层级等结构化数据。

两阶段分工保证查询的准确性：向量搜索消除歧义，Cypher 查询保证语义精确。

## 使用步骤

### 第一阶段：实体解析

1. 识别问题中涉及的实体类型：食品名（FoodCategory）、添加剂名（Chemical）、功能名（Function）、香料（Flavoring）、加工助剂（ProcessingAid）、酶制剂（Enzyme）、生物体（Organism）。
2. 对每个**不确定**的实体调用 `neo4j_vector_search(text, node_label)`，默认返回 top_k=5 候选。
3. 取 top-1 结果：
   - **score ≥ 0.7**：直接使用该节点的 code 或 name 进入第二阶段。
   - **score < 0.7**：向用户展示候选列表，请求确认后再继续。

### 第二阶段：Cypher 查询

4. 用确认的 code/name 构建精确 Cypher，调用 `neo4j_query` 执行。
5. 回答时明确引用限量值（含单位）和食品分类名称；若结果为空，告知用户该组合在 GB2760_2024 中无记录。

## 可向量搜索的节点类型

| node_label 传参值 | 关键标识属性 |
|------------------|-------------|
| Chemical | id, name_zh, name_en |
| FoodCategory | code, name |
| Function | name |
| Flavoring | code, name_zh, name_en |
| ProcessingAid | code, name_zh |
| Enzyme | code, name_zh |
| Organism | name_zh, name_en |

## Schema 速查

### 节点

- **Chemical**: id, name_zh, name_en
- **AdditiveCode**: code, code_type (CNS/INS)
- **Function**: name
- **FoodCategory**: code, name, level
- **FoodCategoryGroup**: code, name, description
- **Flavoring**: code, name_zh, name_en, flavoring_type
- **ProcessingAid**: code, name_zh, type, function, usage_scope
- **Enzyme**: code, name_zh, name_en
- **EnzymeSource**: enzyme_code, source_organism, donor_organism
- **Organism**: name_zh, name_en

### 关系

| 关系 | 方向 | 关键属性 |
|------|------|---------|
| REFERS_TO | AdditiveCode → Chemical | — |
| HAS_FUNCTION | Chemical → Function | — |
| PERMITTED_IN | Chemical/Flavoring → FoodCategory | max_usage, unit, note |
| PERMITTED_IN_GROUP | Chemical → FoodCategoryGroup | max_usage, exclude_group |
| CONTAINS | FoodCategoryGroup → FoodCategory | — |
| HAS_SUBCATEGORY | FoodCategory → FoodCategory | — |
| HAS_SOURCE | Enzyme → EnzymeSource | — |
| FROM_ORGANISM / USES_DONOR | EnzymeSource → Organism | — |

## 查询模板

### 1. 查添加剂在特定食品分类的限量

先用 `neo4j_vector_search` 确定 name_zh 和 FoodCategory code，再执行：

```cypher
MATCH (c:Chemical {name_zh: "山梨酸"})-[r:PERMITTED_IN]->(f:FoodCategory {code: "06.03.02"})
RETURN c.name_zh, f.name, r.max_usage, r.unit, r.note
```

### 2. 查添加剂的所有功能

```cypher
MATCH (c:Chemical {name_zh: "山梨酸"})-[:HAS_FUNCTION]->(fn:Function)
RETURN fn.name
```

### 3. 查食品分类下允许的所有添加剂（带限量）

```cypher
MATCH (c:Chemical)-[r:PERMITTED_IN]->(f:FoodCategory {code: "06.03.02"})
RETURN c.name_zh, r.max_usage, r.unit
ORDER BY c.name_zh
LIMIT 50
```

### 4. 查香料是否允许用于某食品

```cypher
MATCH (fl:Flavoring {name_zh: "香兰素"})-[r:PERMITTED_IN]->(f:FoodCategory {code: "05.01"})
RETURN fl.name_zh, f.name, r.max_usage, r.note
```

### 5. 查食品分类的直接子分类

```cypher
MATCH (parent:FoodCategory {code: "06"})-[:HAS_SUBCATEGORY]->(child:FoodCategory)
RETURN child.code, child.name
ORDER BY child.code
```
