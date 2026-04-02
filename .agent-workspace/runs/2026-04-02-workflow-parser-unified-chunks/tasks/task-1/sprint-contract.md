# Sprint Contract: Task 1 — models.py 重构

## Workspace
`server/workflow_parser_kb/models.py`

## 任务目标

定义贯穿 parser workflow 全程的统一 `Chunk` 数据结构，更新 `WorkflowState` 和 `ParserResult`，同时保留旧类型名作为向后兼容别名，确保模块可正常 import。

## 完成标准

- [x] `Chunk` TypedDict 包含所有指定字段：
  - `chunk_id: str`
  - `doc_metadata: dict`
  - `section_path: List[str]`
  - `structure_type: str`
  - `semantic_type: str`
  - `content: str`
  - `raw_content: str`
  - `confidence: float`
  - `escalated: bool`
  - `cross_refs: List[str]`
  - `ref_context: str`
  - `failed_table_refs: List[str]`
  - `transform_params: dict`
  - `meta: dict`
- [x] `WorkflowState` 只有六个字段：`md_content`、`doc_metadata`、`config`、`rules_dir`、`chunks`、`errors`
- [x] `ClassifiedChunk`、`TypedSegment`、`ParserChunk` 保留为 `Chunk` 的类型别名（向后兼容）
- [x] `RawChunk` 保留为独立 TypedDict（原始字段不变，确保 slice_node 可构造实例）
- [x] 删除 `final_chunks` 字段
- [x] `ParserResult` 使用 `List[Chunk]`
- [x] 保留 `make_chunk_id` 函数（签名不变）
- [x] 模块可正常 import，无 ImportError

## 范围外（待后续 Task 接管）

- 不修改任何 node 文件（classify_node、merge_node 等）
- 不修改 graph.py
- 不修改 __init__.py
- 不修改 post_classify_hooks.py
- 不修改测试文件

## 实现方式

- `Chunk` 作为唯一核心类型定义（14 个字段）
- `ClassifiedChunk = Chunk`、`TypedSegment = Chunk`、`ParserChunk = Chunk` 作为类型别名
- `RawChunk` 保持独立 TypedDict（原始字段：`content`、`section_path`、`char_count`），因为 slice_node 仍在构造 RawChunk 实例
- WorkflowState：`raw_chunks` 已删除，`chunks: List[Chunk]` 为唯一列表字段

## 已知问题

- WorkflowState 中 `raw_chunks` 字段已删除，但 slice_node 仍在读取/写入 `raw_chunks`（由 Task 2-7 修复）
- classify_node、escalate_node、enrich_node、transform_node、merge_node 仍引用 classified_chunks / final_chunks（由 Task 2-7 修复）
- __init__.py 仍导出 ParserChunk 别名（由 Task 2-7 修复）
- graph.py 中 ParserChunk 类型注解（由 Task 4 修复）

---

## 合约审核结论

**审核结果: approved**

### 审核意见

**整体评价**: 合约结构完整，完成标准可测试，范围界定清晰。

**需关注的点**:

1. **实现状态**: 当前 `server/workflow_parser_kb/models.py` 已包含 `Chunk`、`WorkflowState`、`ParserResult` 定义，`make_chunk_id` 函数也存在。合约描述的完成标准与当前代码状态一致 — 如任务尚未实施，需确认是回滚还是重新描述。

2. **"不允许修改的文件"**: 合约未显式列出此项。根据 `docs/architecture/server-architecture.md` 的 workspace 约束矩阵，`workflow_parser_kb/models.py` 属于 Infra 层，被 L2 (services/) 通过接口引用，无特殊保护状态。填 **none**。

3. **与 spec.md 的衔接**: spec.md 中提到 `classify_node` 输出写入 `state["chunks"]`、graph 节点连接调整（merge_node 前置），但合约将 node 文件和 graph.py 明确列为范围外。如后续 sprint 涉及节点修改，需新建合约。

4. **`make_chunk_id` 保留**: 仅写"保留函数"不够精确 — 应补充验证方式，如 `grep -c 'def make_chunk_id' server/workflow_parser_kb/models.py` 返回 1。

**无驳回性缺陷，同意放行。**
