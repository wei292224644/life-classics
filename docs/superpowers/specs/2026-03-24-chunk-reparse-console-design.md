# 控制台 Chunk 列表重解析按钮设计

日期：2026-03-24  
状态：已评审（待用户确认）

## 1. 背景与目标

后端已提供 `POST /api/chunks/{chunk_id}/reparse` 接口，用于基于已存储元数据重跑 `transform_node -> merge_node`，并回写 ChromaDB + FTS。  
当前控制台仅支持编辑保存，不支持直接触发重解析。

本次目标是在控制台 Chunk 列表中提供“重解析”入口，支持用户对单条 chunk 发起重解析，并在处理中禁止该条编辑操作。

## 2. 范围与非目标

### 范围（In Scope）

1. 在列表项（`ChunkCard`）增加“重解析”按钮。
2. 前端 API 客户端新增 `reparse(chunk_id)` 调用。
3. 列表层维护“按 chunk_id 的处理中状态”并驱动按钮 loading/禁用。
4. 重解析成功后刷新当前列表数据；若该条因筛选/分页条件不再位于当前结果集，允许其从当前列表消失，并以 toast 提示该情况。
5. 重解析失败时显示错误提示并恢复可操作状态。

### 非目标（Out of Scope）

1. 不在 `ChunkEditDrawer` 中增加重解析按钮。
2. 不处理“编辑抽屉已打开时又从列表触发重解析”的并发场景。
3. 不引入批量重解析、多选、任务队列等能力。

## 3. 交互设计

## 3.1 按钮位置与样式

- 位置：`ChunkCard` 操作区，与“编辑”等动作并列。
- 文案：`重解析`。
- 状态：
  - 空闲：可点击；
  - 处理中：显示 `重解析中...`（或 spinner + 文案）；
  - 处理中时禁用“编辑”与“重解析”。

## 3.2 触发与反馈

1. 用户点击“重解析”。
2. 该 `chunk_id` 进入处理中集合（`reparsingIds`）。
3. 调用接口 `POST /api/chunks/{chunk_id}/reparse`。
4. 成功：
   - toast：`重解析成功`；
   - 刷新列表数据，展示最新内容与元数据；
   - 从 `reparsingIds` 移除该 id。
5. 失败：
   - toast：`重解析失败` + 错误信息；
   - 从 `reparsingIds` 移除该 id。

## 4. 前端技术设计

## 4.1 API 层改动

文件：`web/apps/console/src/api/client.ts`

- 在 `api.chunks` 下新增：
  - `reparse: (chunk_id: string) => request<Chunk>(\`/chunks/${chunk_id}/reparse\`, { method: 'POST' })`

说明：后端返回结构为 `{ id, content, metadata }`，与 `Chunk` 形状兼容。

## 4.2 列表状态管理

涉及文件：`ChunksPage.tsx` / `ChunkList.tsx` / `ChunkCard.tsx`（按现有数据流落位）。

- 在列表容器层维护：
  - `const [reparsingIds, setReparsingIds] = useState<Set<string>>(new Set())`
- 暴露 handler：
  - `handleReparse(chunkId: string)`：负责置入/移除处理中状态、调用 API、触发刷新与 toast。
- 将 `isReparsing` 和 `onReparse` 透传给列表项组件。
- `reparsingIds` 必须使用不可变更新（创建新 `Set`），避免 React 状态不更新：
  - 置入：`setReparsingIds(prev => new Set(prev).add(chunkId))`
  - 移除：`setReparsingIds(prev => { const next = new Set(prev); next.delete(chunkId); return next })`
- 刷新后判断“该条是否消失”的方式统一为：在当前页返回数据中按 `chunk_id` 查找；若不存在，则 toast 提示“重解析完成，该条在当前筛选条件下不可见”。

## 4.3 组件职责

- `ChunkCard`：仅负责展示按钮状态与触发事件，不承担异步业务。
- 列表容器：承担 API 调用与错误处理，统一刷新策略。
- `ChunkEditDrawer`：维持现状（保存能力不变）。

## 5. 错误处理与边界

1. **重复点击**：同一 id 在 `reparsingIds` 中时直接禁用，避免重复请求。
2. **接口失败**：展示后端 `detail`；若无 `detail` 使用统一兜底文案（如“重解析失败，请稍后重试”），并确保 finally 中释放锁定状态。
3. **刷新一致性**：采用“重拉当前页”策略，避免局部 patch 与服务端状态漂移；不承诺重解析后该条仍在当前筛选/分页视图内。
4. **网络抖动**：按钮 loading 明确反馈，避免用户误判为未触发。
5. **抽屉并发（最小保护）**：不做抽屉状态联动与自动刷新；若检测到该 chunk 抽屉处于打开态且从列表触发重解析，仅在成功后提示“当前抽屉内容可能过期，请关闭后重新打开再编辑”。

## 6. 验收标准

1. 列表每条 chunk 均可见“重解析”按钮。
2. 点击后该条进入 loading，且该条“编辑”按钮不可用。
3. 成功后显示成功提示，列表展示最新 chunk 内容。
4. 失败后显示失败提示，并恢复该条可编辑/可重试状态。
5. 抽屉编辑保存行为无回归。
6. 同一 chunk 在处理中不可重复触发；不同 chunk 可并行重解析且互不影响。
7. 网络异常或后端未返回 `detail` 时，展示统一失败文案并允许立即重试。

## 7. 测试建议

1. 手工测试：
   - 成功路径：触发重解析 -> loading -> 成功 toast -> 列表刷新；
   - 失败路径：模拟接口报错 -> 失败 toast -> 按钮恢复可点；
   - 并发保护：处理中重复点击无二次请求。
2. 可选单测（前端）：
   - 列表容器 `handleReparse` 的状态流转与 finally 释放。
