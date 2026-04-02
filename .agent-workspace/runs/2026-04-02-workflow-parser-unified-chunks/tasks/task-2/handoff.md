# Handoff: task-2

## 版本
v1

## 完成情况
- [x] classify_raw_chunk 返回 List[Chunk] 而非 ClassifiedChunk
- [x] 每个 LLM SegmentItem 直接转为独立 Chunk（14 字段完整填充）
- [x] confidence < threshold 时 semantic_type = "unknown"
- [x] 相邻合并逻辑：section_path + semantic_type + raw_content 均相同则合并
- [x] classify_node 输出 {"chunks": List[Chunk], "errors": List[str]}
- [x] 读取 state["raw_chunks"]（slice_node 尚未改输出 chunks）
- [x] 删除 POST_CLASSIFY_HOOKS 调用
- [ ] test_classify_node_unified.py（范围外，未创建）

## 做了什么 / 没做什么

完全重构了 classify_node.py：
- `classify_raw_chunk` 现在返回 `List[Chunk]`，不再嵌套 ClassifiedChunk/TypedSegment
- 新增 `_merge_adjacent_chunks` 函数，实现相邻 Chunk 合并（同 section_path + semantic_type + raw_content）
- `classify_node` 输出 `{"chunks": ..., "errors": ...}` 替代 `{"classified_chunks": ...}`
- `doc_metadata` 从 `state["doc_metadata"]` 传入（RawChunk 不含此字段）
- 删除 POST_CLASSIFY_HOOKS 调用
- 模块可正常 import

## 已知问题

- `classify_node` 仍读取 `state["raw_chunks"]`，因为 slice_node 仍输出 RawChunk（Task 3/4 解决）
- 现有测试文件（test_classify_node_unit.py 等）引用旧 `classified_chunks`/`final_chunks` 字段，会失败（Task 9 负责修复）
- POST_CLASSIFY_HOOKS 扩展机制删除后待重新设计

## 修改的文件
- server/workflow_parser_kb/nodes/classify_node.py: 完全重构
