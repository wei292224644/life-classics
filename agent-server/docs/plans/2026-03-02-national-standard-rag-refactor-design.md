# 国家标准 RAG 服务重构设计

**日期**: 2026-03-02  
**目标**: 将 PDF 解析交给 MinerU，增加 Neo4j 知识图谱，收窄为「国家标准 RAG」单一场景，并明确 MD 切分策略。

---

## 1. 目标与范围

| 项目 | 说明 |
|------|------|
| **产品定位** | 仅做「国家标准 RAG 服务」（如 GB2760 等），不再做通用知识库 |
| **PDF 解析** | 由 [MinerU](https://github.com/opendatalab/MinerU) 负责：PDF → Markdown/JSON（表格、公式、版面保持更好） |
| **知识图谱** | 使用 Neo4j 存储文档/块及可选实体关系，支持图谱检索与展示 |
| **核心链路** | PDF → MinerU → MD → 切分 → 向量(Chroma) + 图谱(Neo4j) → RAG 检索/对话 |

---

## 2. 方案对比（2～3 种）

### 方案 A：MinerU CLI 子进程 + 现有结构化切分 + Neo4j 最小

- **做法**：上传 PDF 后，本服务调用 `mineru -p <pdf> -o <out_dir>`，读取输出目录中的 MD，再走现有「结构化切分 + 向量 + Neo4j」。
- **优点**：与 MinerU 官方推荐用法一致，不依赖其 Python API 是否稳定；环境隔离（可单独装 MinerU）；实现简单。
- **缺点**：需安装 MinerU CLI；子进程调用有 I/O 与进程开销；需约定输出目录结构并解析。

### 方案 B：MinerU Python API 进程内调用 + 同上

- **做法**：在服务内 `from mineru import MinerU`（或等价 API），内存或临时目录拿到 MD 字符串/路径，再走同一套切分与存储。
- **优点**：无子进程、无额外 I/O，延迟更低；依赖统一在项目内。
- **缺点**：依赖 MinerU 的 Python API 稳定性与文档；可能与现有依赖（如 PyTorch/CUDA）冲突；需核实当前 MinerU 是否暴露稳定 API。

### 方案 C：MinerU 独立服务（mineru-api）+ 本服务只消费 MD

- **做法**：单独部署 `mineru-api`，本服务通过 HTTP 上传 PDF、取回 MD/JSON，再切分与入库。
- **优点**：PDF 解析与 RAG 服务解耦，可独立扩缩容；适合 GPU 与 CPU 分离部署。
- **缺点**：多一个服务与网络依赖；需维护 mineru-api 的可用性与版本。

**推荐**：**优先方案 A**。理由：MinerU 官方文档以 CLI 为主，CLI 行为稳定、文档全；先保证「PDF→MD」这条主链路可维护，后续若 MinerU 提供稳定 Python API 再平滑切换到方案 B；若需要独立扩容解析能力再考虑方案 C。

---

## 3. MinerU 输出与「PDF 转知识库」主流程

1. **输入**：用户上传 PDF（或指定已由 MinerU 产出的 MD 路径，用于调试/回放）。
2. **PDF → MD**：  
   - 方案 A：`mineru -p <pdf_path> -o <output_dir>`，从 `output_dir` 中读取生成的 Markdown（按 MinerU 当前输出结构，一般为 `**/md/*.md` 或同名 `.md`）。
3. **MD → Chunks**：见下节「切分策略」。
4. **写入**：  
   - 向量：现有 Chroma 写入逻辑复用，保证 `doc_id`、`chunk_id`、`content`、`content_type`、`section_path` 等一致。  
   - 图谱：Neo4j 写入「文档 → 块」及可选实体（见第 5 节）。

可选：若 MD 来自国标且需统一展示格式，可在切分前增加一步「GB2760 格式化」（沿用现有 format-gb2760-additives 规则），再切分。

---

## 4. 是否继续用「LLM 动态切分 + 文档元信息类」？

### 4.0 现状与问题

当前流程（README 中的「LLM 增强处理」）：

1. PDF 抽文本后，用 **LLM 全文分析**（`convert_to_structured`），要求模型输出「结构化 Markdown」且**每个最小语义单元**都标上 `[content_type: xxx]`（metadata、definition、specification_table 等）。
2. **StructuredMarkdownParser** 再按每个 `[content_type: xxx]` 块切一刀 → 一个 content_type 块 = 一个 chunk。

带来的问题：

- **切得过细**：一个定义、一张表、一段说明各成一块，chunk 数量多、单块信息少。
- **召回不稳定**：用户问「某添加剂在某某食品中的限量」时，答案往往需要「定义块 + 表格行」一起看；切细后要么只召到其中一块，要么召到多块但语义分散，排序和上下文质量都受影响。
- **LLM 不稳定**：同一文档多次跑可能切分不一致、content_type 标得不一致，不利于复现和调试。
- **成本与延迟**：每份 PDF 都走一遍长文 LLM，成本高、耗时长。

**结论：不建议继续把「LLM 动态切分 + 按 content_type 最小单元切块」作为主方案。** 应改为「以结构为主、粗粒度切分」，见下节。

---

## 5. PDF 转成的 MD 如何切分（推荐）

国标类文档（含 GB2760）通常具备：**标题层级 + 表格 + 条款/定义**。在 MinerU 产出的 MD 上，采用「**按结构、粗粒度**」切分，不再依赖 LLM 决定块边界。

### 5.1 原则

- **块 = 完整小节或完整「标题+内容」**：一个 chunk 对应一个 `##`/`###` 下的整段内容（或若干连续小节合并到合理长度），不按「每个 content_type 一行」切。
- **表格**：整张表作为一块，不按行拆（单表极大时再考虑按行分块）。
- **section_path**：保留标题层级，便于按标准→章节做层级检索与展示。
- **content_type**：首版可不作为切分依据；仅作可选过滤时，用规则推断（见 5.3）。

### 5.2 推荐策略：按标题的结构切分（粗粒度）

1. **以标题为边界**  
   - 以 `##`、`###`（及必要时 `####`）为切分点。  
   - **一个块** = 从当前标题到下一个同级或更高级标题之间的**全部内容**（包括该标题下的多段、一表、多表、列表等）。  
   - 即：按「小节」切，而不是按「每个 content_type 标记」切。

2. **长度约束（可选）**  
   - 若某小节过长（如超过 800～1200 字或 512 token），可在该小节内按段落或子标题再切，并保留少量重叠（如 1～2 句），避免从句子中间切断。

3. **表格**  
   - 表格随所在小节一起归入同一 chunk；若表格单独成节（无正文），则「一个标题 + 一张表」= 一块。不按表格行切。

4. **MinerU 输出无 content_type**  
   - MinerU 产出的 MD 通常没有 `[content_type: xxx]`。切分时**不依赖**该标记，只按标题/段落/表格结构切。  
   - 若后续需要 content_type 做过滤，用 5.3 的规则推断即可。

### 5.3 content_type 的处理（可选、规则推断）

- **首版**：可以不写 content_type，或统一标为 `general_rule` / `note`；检索仅用向量 + section_path 即可。
- **后续**：若需按「定义 / 限量表 / 检验方法」过滤，建议用**规则推断**，而不是 LLM 全文标：  
  - 块内包含 Markdown 表格 + 「最大使用量」「残留量」等 → `specification_table`；  
  - 块内包含「CNS号」「INS号」「功能」等 → `definition`；  
  - 块内包含「测定」「检验」「步骤」等 → `test_method`；  
  - 其余 → `general_rule` 或 `note`。  
  这样切分与标注解耦，召回稳定、可复现。

### 5.4 与现有实现的关系

- **不再使用**：`convert_to_structured`（LLM 全文转结构化 + 标 content_type）作为切分的前置步骤。  
- **新增/调整**：实现「按标题的结构切分」逻辑（可新写 `heading_based_strategy` 或改造现有 heading 策略），输入 MinerU 的 MD 字符串，输出 `List[DocumentChunk]`，保留 `doc_id`、`section_path`、`content`；`content_type` 可选。  
- **MinerU**：仅负责 PDF → MD，不做切分、不调 LLM。

---

## 6. Neo4j 使用方式（最小可行）

目标：先支持「文档 → 块」的图谱存储与检索，后续再扩展实体与关系。

### 6.1 最小 schema

- **节点**  
  - `Document`：`doc_id`, `doc_title`, `source_file`, `created_at` 等。  
  - `Chunk`：`chunk_id`, `doc_id`, `content_type`, `section_path`（可存为字符串或列表），`content_preview`（前 200 字等）。  
- **关系**  
  - `Document -[:CONTAINS]-> Chunk`。

### 6.2 写入时机

- 与向量写入同一处：在「切分完成」后，先写 Chroma，再写 Neo4j（Document 若已存在则复用，否则创建；Chunk 与 CONTAINS 一并创建）。

### 6.3 后续可扩展

- 从国标文本中抽取实体（如标准号、添加剂名称、食品分类号），建 `Entity` 节点及 `Chunk -[:MENTIONS]-> Entity`、`Entity -[:APPLIES_TO]-> Category` 等，用于图谱检索与解释；首版可不做，只做文档–块层级。

---

## 7. 整体架构（重构后）

```
用户上传 PDF
      ↓
[MinerU] PDF → MD（CLI 或 API）
      ↓
MD 字符串 / 临时文件
      ↓
可选：GB2760 格式化
      ↓
按标题的结构切分（粗粒度，不依赖 LLM）
      ↓
List[DocumentChunk]
      ↓
  ┌───┴───┐
  ↓       ↓
Chroma   Neo4j
(向量)   (Document, Chunk, CONTAINS)
  ↓       ↓
RAG 检索 / 对话（可结合向量 + 图谱）
```

### 7.1 模块边界

- **PDF → MD**：独立模块（如 `app/core/pdf/mineru_adapter.py`），仅负责调用 MinerU 并返回 MD 字符串或临时路径；不包含切分与存储。
- **MD → Chunks**：采用「按标题的结构切分」（新写或改造 heading 策略），不再使用 `convert_to_structured`；可选规则推断 content_type。
- **存储**：  
  - 向量：保持现有 Chroma 写入；  
  - 图谱：新增 `app/core/kg/`（或 `app/core/neo4j/`），封装 Neo4j 的「创建 Document/Chunk、CONTAINS」及简单查询。
- **API**：现有上传与检索/对话接口保持不变，仅「上传 PDF」内部改为先走 MinerU 再切分再双写。

---

## 8. 依赖与配置

- **MinerU**：需在运行环境中安装 MinerU（如 `pip install mineru[all]` 或按官方文档），并保证 `mineru` CLI 可用（方案 A）。若采用方案 B，需增加对 `mineru` 包的依赖。  
- **Neo4j**：需 Neo4j 实例（本地或云）；在 `app/core/config.py` 中增加 `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD` 等配置，由 `app/core/kg` 读取。

---

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| MinerU 输出目录/文件名变化 | 抽象「解析 MinerU 输出目录」为单一函数，集中适配；必要时加配置项指定 MD 路径模式。 |
| MinerU 依赖重（如 CUDA） | 方案 A 下可把 MinerU 部署在单独机器，本服务通过方案 C（mineru-api）调用；或当前仅支持 CPU/轻量后端。 |
| Neo4j 与向量数据不一致 | 写 Neo4j 与写 Chroma 使用同一批 `DocumentChunk` 与同一事务或顺序写，避免只写一边。 |

---

## 10. 验收与后续

- **验收**：上传一国标 PDF → 能通过 MinerU 得到 MD → 切分后 Chroma 与 Neo4j 中均有对应文档与块；RAG 检索与对话与现有一致或增强（如可按 content_type 过滤）。  
- **设计文档**：本文档保存于 `docs/plans/2026-03-02-national-standard-rag-refactor-design.md`。  
- **下一步**：实施计划见 `docs/plans/2026-03-02-national-standard-rag-implementation-plan.md`；Agent 模块（Deep Agents + Skills + Tools）设计见 `docs/plans/2026-03-02-agent-module-design.md`。
