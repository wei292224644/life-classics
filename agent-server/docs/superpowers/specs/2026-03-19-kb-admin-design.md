# KB Admin 可视化界面设计文档

**日期：** 2026-03-19
**状态：** 已确认，待实现

---

## 概述

为 agent-server 知识库构建一个可视化管理界面，支持浏览、搜索和编辑 ChromaDB 中的 chunk 数据。同时重建 agent-server 的整个 API 层，使资源边界更清晰。

---

## 一、整体架构

### 前端位置

`agent-server/admin/` 是独立的 Vite + React 子项目，物理上位于 agent-server 目录内，与 `client/` 完全隔离。

- **开发时：** `npm run dev`（端口 5173），通过 vite proxy 将 `/api` 转发到 `localhost:9999`
- **生产时：** `npm run build` 生成 `admin/dist/`，FastAPI 在 `/admin` 路径挂载静态文件

### 目录结构

```
agent-server/
├── admin/                        # 独立 Vite + React 子项目
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx               # 左右分栏布局根组件
│   │   ├── components/
│   │   │   ├── DocList.tsx       # 左侧：文档搜索 + 列表
│   │   │   ├── ChunkList.tsx     # 右侧：chunk 列表 + 分页
│   │   │   └── ChunkCard.tsx     # 单条 chunk，含内联编辑态
│   │   ├── api/
│   │   │   └── client.ts         # fetch 封装，指向 /api/...
│   │   └── lib/
│   │       └── utils.ts
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts            # proxy /api → http://localhost:9999
│   ├── tailwind.config.ts
│   └── components.json           # shadcn/ui 配置
├── app/
│   ├── api/                      # 重建后的 API 层
│   │   ├── documents/
│   │   │   ├── router.py
│   │   │   ├── models.py
│   │   │   └── service.py
│   │   ├── chunks/
│   │   │   ├── router.py
│   │   │   ├── models.py
│   │   │   └── service.py
│   │   ├── kb/
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   └── search/
│   │       ├── router.py
│   │       ├── models.py
│   │       └── service.py
│   ├── core/                     # 保持不变
│   │   ├── kb/                   # ChromaDB、embeddings、retriever
│   │   └── parser_workflow/
│   └── main.py                   # 注册新路由，挂载 admin/dist/
```

---

## 二、新 API 架构

旧的 `app/api/document/` 目录整体废弃，重建为以资源为中心的 REST API。`app/core/` 层完全保留不动。

### 路由设计

```
# 文档资源
GET    /api/documents                  列出所有文档（支持 title/standard_no 模糊搜索）
POST   /api/documents                  上传新文档（含策略参数）
DELETE /api/documents/{doc_id}         删除文档及其所有 chunks

# Chunk 资源
GET    /api/chunks                     列出 chunks（过滤：doc_id, semantic_type, section_path，支持分页）
GET    /api/chunks/{chunk_id}          获取单条 chunk
PUT    /api/chunks/{chunk_id}          更新 chunk（触发 re-embed + ChromaDB upsert）
DELETE /api/chunks/{chunk_id}          删除单条 chunk

# 知识库操作
GET    /api/kb/stats                   统计信息（总 chunk 数、文档数、各 semantic_type 分布）
DELETE /api/kb                         清空整个知识库

# 搜索 & 对话
POST   /api/search                     向量搜索（支持 rerank）
POST   /api/chat                       非流式对话（RAG）
POST   /api/chat/stream/start          启动流式对话，返回 session_id
GET    /api/chat/stream/{session_id}   SSE 流式回复
```

### PUT /api/chunks/{chunk_id} 行为

更新字段：`content`、`semantic_type`、`section_path`

保存流程：
1. 更新 ChromaDB 中的 document 文本和 metadata
2. 对新 content 重新生成向量嵌入（re-embed）
3. upsert 回 ChromaDB（chunk_id 不变）

---

## 三、前端设计

### 布局

左右分栏，无路由跳转：

```
┌──────────────────────────────────────────────────────────┐
│  ⚡ KB Admin                    [stats: chunks · docs]    │
├──────────────┬───────────────────────────────────────────┤
│ 左侧（240px）│ 右侧（flex）                               │
│              │                                           │
│ 🔍 搜索文档  │ [semantic_type ▼]  [清除]   共 38 条      │
│              │                                           │
│ ● GB2762     │ ┌─ chunk card ─────────────────────────┐  │
│   GB5009     │ │ scope · 1/1.1                  [编辑] │  │
│   GB2760     │ │ 本标准规定了食品中污染物的限量...      │  │
│              │ └──────────────────────────────────────┘  │
│              │ ┌─ chunk card (编辑态) ─────────────────┐  │
│              │ │ ✏️ 编辑中           [保存] [取消]      │  │
│              │ │ [content textarea]                    │  │
│              │ │ [semantic_type ▼] [section_path input]│  │
│              │ │ ⚡ 保存后将自动重新生成向量嵌入         │  │
│              │ └──────────────────────────────────────┘  │
│              │                                           │
│              │ ← 1  2  3 →                               │
└──────────────┴───────────────────────────────────────────┘
```

### 技术栈

- Vite + React + TypeScript
- Tailwind CSS
- shadcn/ui 组件：`Input`、`Select`、`Button`、`Badge`、`Textarea`、`Separator`、`ScrollArea`、`Skeleton`、`Toast`

### 色系

深灰底色 + 翠绿点缀（参考 Tailwind gray-900/800/700 + emerald-500/400）

### 文档搜索逻辑

启动时一次性请求 `GET /api/documents` 缓存到内存，输入框对 `doc_title` / `standard_no` 做前端模糊匹配，匹配结果点击后以 `doc_id` 过滤右侧 chunk 列表。

### 内联编辑

点击「编辑」展开表单（不弹 modal）：
- `content`：多行 Textarea
- `semantic_type`：Select 下拉（枚举值）
- `section_path`：Input，用 `/` 分隔（如 `3/3.1`）

同一时间只允许一个 chunk 处于编辑态。若当前有未保存改动，点击其他「编辑」时弹出确认对话框。

---

## 四、错误处理

| 场景 | 处理方式 |
|------|----------|
| 保存失败 | Toast 显示错误信息，编辑表单保持展开，内容不丢失 |
| Re-embed 进行中 | 保存按钮 loading spinner，表单禁用 |
| 保存成功 | Toast "已保存并重新嵌入"，刷新该条 chunk |
| 文档列表为空 | 右侧空态提示"请先通过 parser_workflow 写入数据" |
| 切换文档时有未保存改动 | 弹出确认"放弃当前修改？" |

---

## 五、FastAPI 静态文件挂载

```python
# app/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/admin", StaticFiles(directory="admin/dist", html=True), name="admin")
```

开发时访问：`http://localhost:5173`
生产时访问：`http://localhost:9999/admin`
