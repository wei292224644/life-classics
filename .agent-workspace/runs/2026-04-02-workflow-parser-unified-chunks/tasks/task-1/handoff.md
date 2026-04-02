# Handoff: task-1

## 版本
v1-after-fix-1

## 完成情况
- [x] Chunk TypedDict 包含所有指定字段
- [x] WorkflowState 只有六个字段
- [x] 删除 ClassifiedChunk、TypedSegment、ParserChunk 作为独立类型，保留为 Chunk 的向后兼容别名
- [x] 删除 final_chunks 字段
- [x] ParserResult 使用 List[Chunk]
- [x] 保留 make_chunk_id 函数
- [x] 保留 RawChunk TypedDict（保持原始字段）——向后兼容必须，slice_node 仍在构造 RawChunk 实例

## 做了什么 / 没做什么

models.py 重构，修复验收失败问题：
- 新增统一 Chunk TypedDict（14 个字段）
- WorkflowState 缩减为 6 字段（移除 raw_chunks / classified_chunks / final_chunks）
- ClassifiedChunk、TypedSegment、ParserChunk 保留为 Chunk 的类型别名
- RawChunk 保留为独立 TypedDict（字段不变），因为 slice_node 仍在构造 RawChunk 实例
- 所有类型均可正常 import，模块可运行

## 已知问题

- WorkflowState 中 `raw_chunks` 字段已删除，但 slice_node 仍在读取/写入 `raw_chunks`（由 Task 2-7 修复）
- classify_node、escalate_node、enrich_node、transform_node、merge_node 仍引用 classified_chunks / final_chunks（由 Task 2-7 修复）
- __init__.py 仍导出 ParserChunk 别名（由 Task 2-7 修复）
- graph.py 中 ParserChunk 类型注解（由 Task 4 修复）

## 修改的文件
- server/workflow_parser_kb/models.py: 重构类型定义，新增 Chunk，保留旧类型别名确保向后兼容
