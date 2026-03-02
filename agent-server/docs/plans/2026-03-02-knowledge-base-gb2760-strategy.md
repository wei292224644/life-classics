# 知识库与 GB2760 图谱策略

> 普通国标与 GB2760 的存储与联动策略；多版本 GB2760 采用分库存储。

## 1. 总体策略（C 路线）

- **现阶段**：普通国标（如 GB 8821）仅做 RAG：MinerU → Markdown → 按标题切分 → 写入 Chroma 向量库（暂不写入 Neo4j）；**不与 GB2760 知识图谱联动**。
- **GB2760**：单独建设「添加剂–食品分类–限量」等业务知识图谱，使用 `docs/assets/neo4j_schema.cypher` 定义的节点与关系。
- **后续**：待 GB2760 图谱与实体模型稳定后，再考虑对部分普通国标做实体抽取并与 GB2760 打通（如 Standard -[:IS_PRODUCT_STANDARD_FOR]-> Chemical）。

## 2. 多版本 GB2760：分库存储

- 不同年份的 GB2760（如 2014、2024）放在 **不同的 Neo4j database** 中（如 `gb2760_2014`、`gb2760_2024`）。
- 每个 database 内使用同一份 schema，**不设 Standard 节点、不在关系上带 standard_id**；版本切换通过连接时指定 `database` 实现。
- 应用配置：通过 `NEO4J_URI` + `NEO4J_DATABASE`（或按用途配置多个 database 名）指定当前使用的 GB2760 版本；RAG 用的 Document/Chunk 可放在默认 database 或单独 database。

## 3. 普通国标

- 不入 GB2760 业务图谱；仅通过 RAG 流水线写入向量库，用于检索与问答；未来如有需要，可为少数关键标准补充 Document/Chunk 图。
- 与 GB2760 的联动留待后续阶段设计。

## 4. 所有国标的多版本：同一库内用元数据区分

**约定**：所有国标（含 GB2760 的 RAG 侧、普通国标如 GB 8821）在入库时，均在 Document / Chunk / 向量 metadata 中写入统一的版本元数据，便于同一库内区分多版本、按版本检索或默认选现行版。

**建议字段**（名称与用途可随实现微调）：

| 字段 | 说明 | 示例 |
|------|------|------|
| `standard_no` | 标准号（可统一去空格） | `GB2760`, `GB8821` |
| `standard_title` | 标准中文全名（可选） | 食品安全国家标准 食品添加剂 β-胡萝卜素 |
| `standard_year` | 年份 | `2011`, `2024` |
| `standard_version` | 标准+版本标识，便于比对 | `GB2760-2014`, `GB8821-2011` |
| `standard_status` | 可选：现行/废止/草案 | `active`, `obsolete`, `draft` |
| `effective_from` / `effective_to` | 可选：实施/废止日期，便于按时间查询 | 日期字符串 |

**使用方式**：

- **默认现行版**：检索时若无指定版本，可优先过滤 `standard_status='active'` 或取同一 `standard_no` 下 `standard_year` 最大的一版。
- **显式指定版本**：用户问「按 2011 版 GB 8821」时，条件带 `standard_no` + `standard_year`（或 `standard_version`）。
- **GB2760 图谱**：仍按「分库」区隔版本；若 RAG 侧也存 GB2760 文本，其 Document/Chunk 同样带上述元数据，与普通国标一致。

## 5. 参考

- Schema 定义：`docs/assets/neo4j_schema.cypher`
- 现有 Document/Chunk 写入：`app/core/kg/neo4j_store.py`（用于 RAG 文档，与 GB2760 业务图可同实例不同 database）
