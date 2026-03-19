# 清空知识库功能设计

**日期：** 2026-03-19
**状态：** 已确认

## 背景

Admin UI 中缺少清空知识库的入口。后端 `DELETE /api/doc/clear` 端点已实现（`DocumentService.clear_all()`），会清空 ChromaDB 向量库和 Markdown DB，但前端没有暴露该能力。

## 目标

在 Admin UI 顶部栏添加"清空知识库"按钮，带二次确认弹窗，成功后刷新界面状态。

## 方案

**方案 A（采用）：AlertDialog 原生组件**

改动最小，使用项目已有的 shadcn/ui AlertDialog 组件，风格与现有 UI 完全一致。

## 变更范围

### 1. `agent-server/admin/src/api/client.ts`

在 `documents` 对象下添加 `clearAll` 方法：

```ts
clearAll: () =>
  request<{
    status: string
    message: string
    deleted_documents: number
    deleted_chunks: number
  }>('/doc/clear', { method: 'DELETE' })
```

### 2. `agent-server/admin/src/App.tsx`

**顶部栏**右侧（统计数字旁）加一个红色描边按钮"清空知识库"。

点击后弹出 `AlertDialog`：
- **标题：** 清空知识库
- **内容：** 此操作将删除所有文档和 Chunks，且不可恢复。是否继续？
- **操作：** 取消 / 确认清空（红色）

确认后执行流程：
1. 调用 `api.documents.clearAll()`
2. 成功 → Toast 提示（含删除文档数/chunks 数），重置 `documents = []`、`selectedDocId = null`，重新拉 stats
3. 失败 → Toast 显示错误信息

## 不涉及

- 后端无需改动（端点已存在）
- FTS SQLite 数据库的清空（当前 `DocumentService.clear_all()` 未包含，不在本次范围）
- 单个文档删除功能（独立需求）
