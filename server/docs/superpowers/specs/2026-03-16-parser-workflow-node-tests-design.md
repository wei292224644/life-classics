## Parser Workflow Node-Level Real LLM Tests Design

**Date:** 2026-03-16  
**Scope:** `agent-server/tests/core/parser_workflow/` + related parser workflow nodes

### 1. Background & Goals

当前仅有一个端到端测试 `test_workflow.py`，通过 LangGraph 跑完整个 `parser_graph`，并使用真实 LLM + 实际规则目录。它适合作为整体健康检查，但不利于：

- 针对单个节点（如 `classify_node`、`escalate_node`、`transform_node`）的 prompt 调优
- 精准观测每个节点输入 / 输出结构与行为
- 在不受其他节点影响的前提下快速回归某个节点的逻辑

本设计希望为 **每个节点** 提供一组**可选的真实 LLM 测试**，同时保留一个端到端“烟囱测试”，形成：

- **节点级真实 LLM 测试**：聚焦单节点行为 + prompt 效果
- **端到端测试**：确保整个流水线在真实环境下可用

整体遵循：

- 使用真实 markdown 资产（现有 GB 标准 markdown 文件）作为主要数据来源
- 使用真实规则目录 `app/core/parser_workflow/rules`
- 使用真实 LLM 调用（前提是本地设置了 `LLM_API_KEY` 等环境变量；未设置则跳过）
- 用相对宽松的结构性断言 + 丰富日志，方便人工判断 prompt 质量

---

### 2. 测试文件结构设计

在 `tests/core/parser_workflow/` 目录内采用如下结构：

- **端到端测试（保留 / 微调）**
  - `test_workflow.py`
    - 继续做“完整 LangGraph 流程 + streaming 日志”，作为整体健康检查。
    - 主要断言：
      - `final_chunks` 非空
      - `errors` 为空
    - 其他节点中间状态以日志为主，不做严格断言。

- **节点级真实 LLM / 结构性测试（新增）**
  - `test_parse_node_real.py`（无 LLM，主要验证元数据逻辑，可选）
  - `test_structure_node_real_llm.py`
  - `test_slice_node_real.py`（若 `slice_node` 无 LLM，仅做结构性断言）
  - `test_classify_node_real_llm.py`
  - `test_escalate_node_real_llm.py`
  - `test_transform_node_real_llm.py`

- **公共测试工具**
  - 新增 `tests/core/parser_workflow/test_utils.py`（或复用 / 扩展 `conftest.py`）：
    - 加载 markdown 资产：读取现有 `assets` 目录下的 GB 标准 markdown 文件。
    - 根据场景构造 `WorkflowState` / `RawChunk` / `ClassifiedChunk` 的辅助函数。
    - 统一日志辅助：把关键信息格式化输出（截断 content，json 序列化结构等）。

---

### 3. 测试数据与环境约束

#### 3.1 数据来源

- **Markdown 资产**
  - 复用当前端到端测试中使用的资产文件：
    - `tests/core/parser_workflow/assets/《食品安全国家标准 食品添加剂 天门冬酰苯丙氨酸甲酯（又名阿斯巴甜）》（GB 1886.47-2016）第1号修改单.md`
  - 如有需要，可以在后续增加更多典型标准的 markdown 文件，但设计上默认以现有资产为主。

- **规则目录**
  - 一律使用真实规则目录：
    - `app/core/parser_workflow/rules`
  - 所有节点级测试都指向该目录，确保测试行为与生产环境一致（包括 doc_type 规则、content_type 规则、transform_params 等）。

#### 3.2 环境变量与跳过策略

- 真实 LLM 测试依赖环境变量，例如：
  - `LLM_API_KEY`
  - （以及 `settings` 中映射到的其他 KEY / BASE_URL）
- 策略：
  - 在每个“真实 LLM 测试”文件开头，复用 / 抽取 `test_workflow.py` 中读取 `.env` 的逻辑：
    - 若环境变量未设置但 `.env` 存在，则尝试从 `.env` 加载。
    - 若最终仍未拿到必要 key，则通过 `pytest.skip` 跳过整个文件。
  - 保证：
    - CI 环境中没有 LLM key 时，不会导致测试失败。
    - 本地有 key 时，节点级真实 LLM 测试可以完整运行。

---

### 4. 各节点测试设计

#### 4.1 `parse_node`（`test_parse_node_real.py`，无 LLM）

**目的：**

- 验证 `parse_node` 对 `doc_metadata` 的补全和校验逻辑：
  - 从 markdown 首行 `# 标题` 自动补全缺失的 `title`
  - 对缺失的 `standard_no` 追加错误信息

**输入构造：**

- 使用一个最小 `WorkflowState`：
  - `md_content`：从真实 markdown 资产中读取全文或前几行。
  - `doc_metadata`：
    - Case 1：缺失 `title`，有 `standard_no`
    - Case 2：缺失 `standard_no`，有 `title`
  - 其他字段（`raw_chunks` / `classified_chunks` / `final_chunks` / `errors`）可为空列表。

**断言要点：**

- Case 1：
  - 返回的 `doc_metadata["title"]` 被成功补全。
  - `errors` 未新增与 `standard_no` 相关的错误。
- Case 2：
  - 返回的 `errors` 中包含 `"doc_metadata missing required field 'standard_no'"`。

该文件不依赖 LLM，不做复杂日志，仅作结构性保护。

---

#### 4.2 `structure_node_real_llm.py`

**目的：**

- 验证文档类型推断逻辑，支持两种路径：
  - 优先按规则匹配（`match_doc_type_by_rules`）
  - 若规则命中失败，则使用 LLM 推断并写回新 doc_type 规则
- 提供可观测的日志，便于调优 doc_type 推断 prompt。

**输入构造：**

- 使用真实 markdown 全文作为 `md_content`。
- `doc_metadata`：
  - 至少包含 `standard_no`（可选包含简单 `title`）。
- `WorkflowState` 其他字段可保持默认。

**断言要点：**

- 一般场景（规则应能命中）：
  - `doc_metadata["doc_type"]` 存在且为非空字符串。
  - `doc_metadata["doc_type_source"] == "rule"`。
- 特殊场景（构造规则一定不命中的 case，可选）：
  - 通过准备一个“规则中不存在的新类型” markdown（或暂不实现）。
  - 期望：
    - `doc_type_source == "llm"`
    - `RulesStore` 中新增一条 doc_type 规则（可通过操作前后长度差异判断）。

**日志输出建议：**

- 打印：
  - 最终 `doc_type` 与 `doc_type_source`
  - 若有新增 doc_type 规则，则打印该规则的 JSON 内容（适度截断）

---

#### 4.3 `slice_node_real.py`

**目的：**

- 用真实 markdown 验证 `slice_node` 的切块行为：
  - 切块数量是否合理（至少大于 0）
  - 每个 `raw_chunk` 是否具备必要字段

**输入构造：**

- 先通过 `parse_node` + `structure_node` 得到带 `doc_metadata` 的 `WorkflowState`，或直接构造：
  - `md_content`：真实 markdown 全文
  - `doc_metadata`：包含 `standard_no` / `title` / `doc_type`（可直接用前面节点的输出）

**断言要点：**

- 返回 state 中：
  - `raw_chunks` 非空。
  - 每个 `raw_chunk` 至少包含：
    - `content`（非空字符串）
    - `section_path`（列表或类似结构）

**日志输出建议：**

- 针对前若干个 `raw_chunk`：
  - 打印 `section_path`
  - 打印 `content` 的前 N 行（截断）

该测试不依赖 LLM，仅检验切块策略的结构合理性与可读性。

---

#### 4.4 `classify_node_real_llm.py`

**目的：**

- 在真实规则和真实片段上评估分类 prompt 的效果：
  - 是否能输出结构正确的 segments
  - `has_unknown` 的逻辑是否符合预期

**输入构造：**

- 首先运行 `slice_node` 获得一组 `raw_chunks`。
- 从中选择若干具有代表性的 `raw_chunk`（例如：
  - 包含“范围”“适用”“检验方法”等关键词的片段；
  - 或长度适中的正文段落）。
- 构造 `WorkflowState`：
  - `raw_chunks`：选取的少量片段（例如 1–3 个）
  - `rules_dir`：真实规则目录
  - 其他字段可为空列表或合理默认值。

**断言要点：**

- `classified_chunks` 数量与输入 `raw_chunks` 一致。
- 对每个 `ClassifiedChunk`：
  - `segments` 非空。
  - 每个 segment 具备：
    - `content`
    - `content_type`
    - `confidence`
  - `has_unknown` 满足以下逻辑：
    - 若所有 segment 的 `confidence` 均 ≥ 阈值，则为 `False`；
    - 否则为 `True`。
- 可选：为刻意构造的“噪声片段” case，断言 `has_unknown == True`。

**日志输出建议：**

- 针对有限数量的 `raw_chunk`，详细打印：
  - 原始 `raw_chunk.content` 的前 N 行（截断）。
  - `segments` 数组（每个 segment 打印 `content`（截断）+ `content_type` + `confidence`）。

这些日志主要服务于人工调 prompt，而非 CI 断言。

---

#### 4.5 `escalate_node_real_llm.py`

**目的：**

- 验证 unknown 片段的升级逻辑：
  - 是否能根据现有 content_type 规则匹配已有类型；
  - 或者创建新的 content_type + transform_params；
  - 将 `classified_chunks` 中的 `has_unknown` 清零。

**输入构造：**

- 手工构造一个 `classified_chunks` 列表，至少包含 1 个：
  - `has_unknown == True`
  - `segments` 中包含 1–2 个 `content_type == "unknown"` 的 segment，内容可从真实 markdown 中抽取“边界型”句子。
- 构造 `WorkflowState`：
  - `classified_chunks`：上述人工构造的数据
  - `rules_dir`：真实规则目录
  - 其他字段可为空或合理默认。

**断言要点：**

- 返回的 `classified_chunks`：
  - 对于原本 `has_unknown == True` 的条目：
    - 新的 `has_unknown == False`
    - 所有原 `content_type == "unknown"` 的 segments，现应满足：
      - `content_type != "unknown"`
      - `escalated == True`
      - `confidence == 1.0`
      - 具备有效的 `transform_params`（至少包含 `strategy` 和 `prompt_template`）。
- 若 LLM 决定 `action == "create_new"`：
  - `RulesStore` 中 content_type 规则数量应增加（可通过前后长度对比）。

**日志输出建议：**

- 针对每个被升级的 segment：
  - 打印原始 `content`（截断）；
  - 打印 LLM 返回的决策（使用旧类型 / 新类型、对应 id、description）；
  - 打印新生成的 transform 配置（`strategy` / `prompt_template`）。

---

#### 4.6 `transform_node_real_llm.py`

**目的：**

- 评估 transform prompt 的效果与整体结构：
  - 是否能将 segment 转写为结构化、适合向量化的文本；
  - `DocumentChunk` 字段是否齐全、合理。

**输入构造：**

- 构造少量 `ClassifiedChunk`，每个包含 1–3 个 segment：
  - `transform_params` 来自真实规则（可以通过 `RulesStore.get_transform_params` 获取）；
  - `content_type` 为真实的类型 id（如 `definition`、`scope` 等）。
- `doc_metadata` 使用 `structure_node` 的实际输出或人工构造的简化版本（至少包含 `standard_no` 和 `doc_type`）。
- 构造 `WorkflowState`：
  - `classified_chunks`：少量人工或真实构造的数据
  - `doc_metadata`：如上

**断言要点：**

- `final_chunks` 非空。
- 对每个 `DocumentChunk`：
  - 具备：
    - `chunk_id`
    - `doc_metadata`
    - `section_path`
    - `content_type`
    - `content`
    - `raw_content`
    - `meta`
  - `meta["transform_strategy"]` 与对应 segment 中的 strategy 一致。
  - `meta["segment_raw_content"]` 与原 segment 的 `content` 一致。

**日志输出建议：**

- 针对少量 `DocumentChunk`，打印：
  - `content_type`
  - 转写后的 `content`（截断）
  - `meta` 中的 strategy 与原始 segment 内容（截断）

---

### 5. 运行方式与使用场景

- 本地调试某个节点的 prompt 时，可以只运行对应文件，例如：
  - `pytest tests/core/parser_workflow/test_classify_node_real_llm.py -v`
  - `pytest tests/core/parser_workflow/test_escalate_node_real_llm.py -v`
- 端到端健康检查仍使用：
  - `pytest tests/core/parser_workflow/test_workflow.py -v`
- 当 prompt 或规则发生变化时，建议：
  - 优先跑对应节点的真实 LLM 测试，观察日志中的输出变化；
  - 在基本满意后，再跑一次端到端测试，确认整体 pipeline 仍然健康。

---

### 6. 实施范围与后续工作

**涉及文件（计划新增 / 修改）：**

- 新增：
  - `tests/core/parser_workflow/test_parse_node_real.py`
  - `tests/core/parser_workflow/test_structure_node_real_llm.py`
  - `tests/core/parser_workflow/test_slice_node_real.py`
  - `tests/core/parser_workflow/test_classify_node_real_llm.py`
  - `tests/core/parser_workflow/test_escalate_node_real_llm.py`
  - `tests/core/parser_workflow/test_transform_node_real_llm.py`
  - `tests/core/parser_workflow/test_utils.py`（或完善现有 `conftest.py`）
- 复用 / 轻微调整：
  - `tests/core/parser_workflow/test_workflow.py`（可选：只在注释中标注其角色为“端到端烟囱测试”）

**后续步骤（在单独的实现计划中详细展开）：**

- 为每个节点按本设计创建测试文件和辅助工具函数；
- 统一封装 `.env` 加载 + LLM key 检查逻辑，避免重复代码；
- 根据实际运行结果微调各节点的日志内容和断言粒度，使之既不过于脆弱，又能提供足够的 prompt 调试信号。

