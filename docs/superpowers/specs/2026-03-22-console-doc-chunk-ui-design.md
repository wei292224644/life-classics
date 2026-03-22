# Console UI 改进设计文档

**日期**：2026-03-22
**范围**：`web/apps/console` 前端 + `server/api/documents` 后端

---

## 背景

当前 console 管理界面存在以下问题：
1. 左侧 Doc 列表宽度 240px，GB 标准标题过长时被截断，无法看清
2. Doc 列表无分页，文档多时需要大量滚动
3. 没有文档编辑功能，无法修改文档的 title / standard_no / doc_type
4. Chunk 编辑抽屉缺少文档元数据字段（doc_id、title、standard_no、doc_type），信息不完整

---

## 设计目标

- Doc 列表宽度扩大至 360px，标题可读性显著提升
- Doc 列表新增客户端分页（每页 20 条）
- 新增文档编辑右侧抽屉，可编辑 title / standard_no / doc_type
- Chunk 编辑抽屉底部补充文档元数据只读字段

---

## 后端改动

### 新接口：`PATCH /api/documents/{doc_id}`

**请求体**（均为可选，partial update）：
```json
{
  "title": "string",
  "standard_no": "string",
  "doc_type": "string"
}
```

**实现逻辑**：
- 在 ChromaDB 中查询所有 doc_id 匹配的 chunks
- 若查询结果为空（该 doc_id 从未存在，或 chunks 已被全部删除），返回 404
- ChromaDB 不支持直接修改 metadata，需先 get 获取所有 chunk IDs 和现有 metadata，再调用 collection.update() 批量更新
- 只更新传入的字段，未传字段保持原值

**返回值**：更新后的 DocumentInfo（doc_id, title, standard_no, doc_type, chunks_count）

---

## 前端改动

### 1. ChunksPage.tsx

- 侧边栏宽度：w-60 → w-[360px]
- 新增 editingDoc: DocumentInfo | null 状态
- 新增 handleEditDoc(doc: DocumentInfo) handler，传给 DocList
- 挂载 DocEditDrawer，onSaved 时调用 refreshDocuments()（回调签名为 () => void，父组件直接重新拉取列表，确保 chunks_count 准确）

### 2. DocList.tsx

**分页**：
- 新增 page 状态（从 1 开始），PAGE_SIZE = 20
- filtered 经分页切片后渲染
- 搜索框 onChange 时重置 page = 1
- 底部分页控件：← 上一页 / 第 X / Y 页 / 下一页 →
- 第 1 页时「上一页」按钮 disabled；最后一页时「下一页」按钮 disabled
- 仅当总页数 > 1 时显示分页控件

**搜索**：
- 过滤字段增加 title，即同时过滤 standard_no、doc_type、doc_id、title

**编辑按钮**：
- 每个 DocItem 新增 onEdit prop
- 悬停时同时显示编辑图标（铅笔）和删除图标，编辑按钮在删除按钮左侧
- 点击编辑图标：调用 onEdit(doc)，不触发 onSelect
- 主按钮 pr-8 调整为 pr-14，为两个图标按钮留出足够空间

### 3. 新建 DocEditDrawer.tsx

复用 Sheet 组件，与 ChunkEditDrawer 保持一致的交互模式，宽度 w-[480px]。

**只读字段**（bg-muted 灰底展示）：doc_id、chunks_count

**可编辑字段**：title（Input）、standard_no（Input）、doc_type（Input，不用 Select，类型值不固定）

**保存流程**：
1. 调用 api.documents.update(doc_id, payload)
2. 成功：toast「已保存」→ 调用 onSaved() 触发父组件刷新列表 → 关闭抽屉
3. 失败：toast「保存失败」+ 错误信息

### 4. ChunkEditDrawer.tsx

在现有字段下方、raw_content 之后，新增只读分组「文档元数据（只读）」，展示：doc_id、title、standard_no、doc_type。
样式与现有 raw_content 只读块一致（bg-muted + text-muted-foreground）。

### 5. api/types.ts

新增 UpdateDocumentPayload：{ title?: string, standard_no?: string, doc_type?: string }

### 6. api/client.ts

顶部 import 增加 UpdateDocumentPayload，api.documents 中新增：
update: (doc_id, payload) => request<DocumentInfo>(`/documents/${doc_id}`, { method: 'PATCH', body: JSON.stringify(payload) })

---

## 边界情况

| 场景 | 处理方式 |
|------|----------|
| 搜索过滤后分页 | 基于过滤结果重新计算页数，过滤时重置到第 1 页 |
| 只有 1 页 | 隐藏分页控件 |
| 第 1 页 / 最后一页 | 对应方向的翻页按钮 disabled |
| 文档在 ChromaDB 中无 chunks | 后端返回 404，前端 toast 提示 |
| 编辑中关闭抽屉 | 不保存，直接关闭（与 ChunkEditDrawer 一致） |

---

## 改动文件清单

| 文件 | 类型 |
|------|------|
| server/api/documents/router.py | 修改 |
| server/api/documents/service.py | 修改 |
| server/api/documents/models.py | 修改 |
| web/apps/console/src/pages/ChunksPage.tsx | 修改 |
| web/apps/console/src/components/DocList.tsx | 修改 |
| web/apps/console/src/components/DocEditDrawer.tsx | 新建 |
| web/apps/console/src/components/ChunkEditDrawer.tsx | 修改 |
| web/apps/console/src/api/types.ts | 修改 |
| web/apps/console/src/api/client.ts | 修改 |
