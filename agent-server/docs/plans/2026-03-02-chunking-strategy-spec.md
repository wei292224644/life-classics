# 国家标准 Markdown 切分策略规范

> 约定从 MinerU 等得到的国标 Markdown 如何按「业务单元」切分为 RAG 可用的 DocumentChunk，以及引用展开规则。实现与测试应遵循本规范。

## 1. 目的与适用范围

- **目的**：使切分后的块在检索时尽量自包含、语义完整，便于 RAG 回答「某指标是多少」「某检测方法怎么做」等问题。
- **适用范围**：食品安全国家标准等结构化 Markdown（如 GB 8821、GB 5009.xx、GB 4789.xx、GB 31636 等）；GB2760 的 RAG 侧若也存 Markdown 文本，同样适用。
- **不适用范围**：GB2760 业务图谱的实体与关系建模见 `docs/plans/2026-03-02-knowledge-base-gb2760-strategy.md`，不在此规范内。

## 2. 总体原则

1. **业务单元驱动**：按「业务单元」切分，而非单纯按标题层级或固定字数。业务单元指：一条技术指标、一个主条款、一个完整检验方法、一个流程节点等。
2. **引用展开**：正文中出现的本文件内引用（如「同 A.3.3。」「按 A.4.2」）应在生成 chunk 时**将引用指向的内容展开进当前块**，并保留原引用表述；同时在 chunk 元数据中记录 `ref_section_code`，便于追溯与去重。
3. **块内自包含**：单个 chunk 应尽量包含回答一类问题所需的完整信息，减少「见某条」导致的检索缺失。
4. **与现有结构兼容**：切分输出为 `DocumentChunk`，使用现有 `section_path`、`content_type`、`meta`；版本信息使用统一元数据字段（见第 6 节）。

## 3. 文档类型与切分策略

**文档类型推断**：建议以 **Agent（LLM）为主、规则兜底**，避免规则难以覆盖非标命名、修改单、合订本等情况。实现上可调用 `infer_doc_type_auto`（见 `app/core/kb/strategy/doc_type.py`），通过配置 `DOC_TYPE_INFERENCE`（`agent` / `rule` / `agent_then_rule`）选择行为；Agent 失败或未配置时自动回退到规则。

### 3.1 单添加剂/产品标准（如 GB 8821、GB 31636）

| 内容类型 | 切分粒度 | content_type 建议 | 说明 |
|----------|----------|-------------------|------|
| 主条款（范围、化学名称、分子式等） | 按**顶级条款**（如「1 范围」「2 化学名称、分子式、结构式和相对分子质量」） | SCOPE / DEFINITION / CHEMICAL_FORMULA 等 | 每个一级标题对应一块，包含其下所有子标题与正文直至下一同级标题 |
| 技术指标表（感官、理化等） | **按行** | SPECIFICATION_TABLE | 表头 + 该行指标 + 检验方法列；每行一个 chunk，便于问「某指标限值是多少」 |
| 附录检验方法 | **按方法**（如 A.3 鉴别试验、A.4 β-胡萝卜素的测定） | TEST_METHOD / IDENTIFICATION_TEST 等 | 一个方法为一块，内含：原理、试剂与材料、仪器设备、分析步骤、结果计算；若方法内出现「同 A.x.x」则做引用展开 |

### 3.2 检测方法标准（如 GB 5009.129、GB 5009.33）

| 内容类型 | 切分粒度 | content_type 建议 | 说明 |
|----------|----------|-------------------|------|
| 多法结构 | **按「第 N 法」** 作为根块 | TEST_METHOD / CHROMATOGRAPHIC_METHOD | 如「第一法 液相色谱法」为一根块，其下再按功能块切分 |
| 方法内功能块 | 按**功能段落** | REAGENT / INSTRUMENT / CALCULATION_FORMULA 等 | 原理、试剂与材料、仪器和设备、分析步骤（可再分子步骤）、色谱条件、标准曲线、结果计算、精密度等各为一块或合并为少量块 |
| 引用 | 同 3.1，做引用展开 | — | 「同 X.X」「按附录 A」等展开后写入当前块，并记 ref_section_code |

### 3.3 微生物检验/流程类标准（如 GB 4789.4）

| 内容类型 | 切分粒度 | content_type 建议 | 说明 |
|----------|----------|-------------------|------|
| 检验程序流程图 | 单块（含图注/描述） | GENERAL_RULE 或 NOTE | 流程图单独一块；若已用 VLM 生成图注，图注与图引用一并写入该块 |
| 操作步骤（增菌、分离、鉴定等） | 按**流程节点**（如预增菌、选择性增菌、分离） | TEST_METHOD / GENERAL_RULE | 每个节点下所有文字与相关表格归为一块 |
| 判定/特征表（如菌落特征表） | **整表一块** | SPECIFICATION_TABLE | 表名 + 表头 + 全部行，便于按表查询 |

## 4. 引用展开规则

### 4.1 识别的引用模式（本文件内）

- `同 A.3.3。`、`同 A.3.3`、`同 A.4.2。` 等：节号可能含空格（如 `A. 3 . 3`），需归一化匹配。
- `按 A.4.2`、`按附录 A 中 A.4`：指向某一节或方法。
- 其他可扩展模式：`见 X.X`、`按 GB/T xxxx 中 X.X`（本文件内指代）等，可在实现时按需加入。

### 4.2 展开行为

1. **解析引用**：从当前文档已切分的节或「标题 → 内容」映射中，根据节号（如 A.3.3）找到对应内容文本。
2. **写入当前块**：在引用句后追加展开内容（如「（引用自 A.3.3：…）」或直接追加段落），保证块内自包含。
3. **保留原句**：不删除「同 A.3.3。」等原句，便于溯源。
4. **元数据**：在 chunk 的 `meta` 中记录 `ref_section_code: ["A.3.3", ...]`（可多个），便于后续统计或去重。

### 4.3 无法解析时的处理

- 若节号不存在或尚未解析到：可不展开，仅保留原引用句；或在 meta 中记录 `ref_section_code_unresolved: ["A.x.x"]` 供后续改进。

## 5. 标题与 section_path

- **section_path**：按标题层级组成列表，如 `["附录 A", "A.3 鉴别试验", "A.3.4 分析步骤"]`，与现有 `DocumentChunk.section_path` 一致。
- 标题识别：Markdown 标题正则 `^#{1,6}\s+.+`；若源文档有「A.3.4.1」「A.3.4.2」等编号，纳入 section_path 最后一级或与标题合并。
- 表格块：section_path 包含其所属章节；若为「表 1 感官要求」，可在 section_path 或 meta 中保留表名便于检索。

## 6. 元数据约定

### 6.1 与现有实现一致

- `source`：来源标识（如文件名）。
- `markdown_id`：Markdown 文档唯一标识，与 `DocumentChunk.markdown_id` 一致。

### 6.2 版本与标准（与知识库策略对齐）

所有国标 chunk 建议携带统一版本元数据（与 `2026-03-02-knowledge-base-gb2760-strategy.md` 一致），写入 `meta` 或向量库 metadata：

| 字段 | 说明 | 示例 |
|------|------|------|
| `standard_no` | 标准号 | GB2760, GB8821 |
| `standard_title` | 标准全称（可选） | 食品安全国家标准 食品添加剂 β-胡萝卜素 |
| `standard_year` | 年份 | 2011, 2024 |
| `standard_version` | 标准+版本 | GB2760-2014, GB8821-2011 |
| `standard_status` | 现行/废止/草案（可选） | active, obsolete, draft |
| `effective_from` / `effective_to` | 实施/废止日期（可选） | 日期字符串 |

### 6.3 引用展开相关

| 字段 | 说明 |
|------|------|
| `ref_section_code` | 本块展开过的本文件内节号列表，如 `["A.3.3"]` |
| `ref_section_code_unresolved` | 未解析到的节号（可选） |

## 7. ContentType 使用建议

与 `app/core/document_chunk.ContentType` 对齐，按内容语义选择：

- **SCOPE**：范围；**DEFINITION**：术语/定义；**CHEMICAL_FORMULA / CHEMICAL_STRUCTURE / MOLECULAR_WEIGHT**：化学信息。
- **SPECIFICATION_TABLE**：技术指标表/判定表；**SPECIFICATION_TEXT**：技术要求叙述。
- **TEST_METHOD**：检验/测定方法整体；**IDENTIFICATION_TEST**：鉴别试验；**CHROMATOGRAPHIC_METHOD**：色谱/光谱法。
- **REAGENT / INSTRUMENT**：试剂与仪器；**CALCULATION_FORMULA**：计算公式；**GENERAL_RULE**：一般规定；**NOTE**：注释。

未明确归类时使用 **GENERAL_RULE**。

## 8. 实现与测试的对应关系

- **当前实现**：`app/core/kb/strategy/heading_strategy.split_heading_from_markdown` 仅按标题粗粒度切分，未区分文档类型、未做引用展开、未按表行切分。后续可在此基础上增加：
  - 文档类型检测（按标题/结构推断：单添加剂、检测方法、微生物）；
  - 按本节 3.1～3.3 的粒度与 content_type 切分；
  - 引用识别与展开（第 4 节）及 ref_section_code 写入 meta。
- **测试**：建议针对三类样本（如 GB 8821、GB 5009.33、GB 4789.4）做单测或集成测：断言 chunk 数量与类型、section_path、含「同 A.x.x」的块是否包含展开内容、meta 中 ref_section_code 与 standard_* 是否正确。

## 9. 参考文档

- 知识库与 GB2760 策略：`docs/plans/2026-03-02-knowledge-base-gb2760-strategy.md`
- DocumentChunk 与 ContentType：`app/core/document_chunk.py`
- 当前标题切分实现：`app/core/kb/strategy/heading_strategy.py`
- 示例国标 Markdown：`docs/assets/` 下 GB 8821、GB 5009.33、GB 4789.4 等
