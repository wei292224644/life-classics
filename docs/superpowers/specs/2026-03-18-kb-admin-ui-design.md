# 知识库管理 Admin UI — 设计规格

**日期**：2026-03-18
**状态**：已确认（v2，审核后修订）

---

## 概述

为 `agent-server` 构建一个独立的知识库管理界面，访问地址为 `http://localhost:9999/admin`。支持上传 Markdown 文档、查看文档切分结果，并对 Chunk 进行完整的 CRUD 操作。与 `client/` 完全独立，不侵入现有前端体系。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 构建工具 | Vite |
| 框架 | React 19 + TypeScript |
| 样式 | Tailwind CSS |
| UI 组件库 | shadcn/ui |
| HTTP 客户端 | fetch（原生） |
| 托管 | FastAPI `StaticFiles`，挂载于 `/admin` |

---

## 项目结构

```
agent-server/
  admin/                        ← Vite + React 项目根目录
    src/
      api/
        client.ts               ← fetch 封装，baseURL = /api/doc
        types.ts                ← API 响应类型定义（见数据模型说明）
      components/
        DocumentList.tsx        ← 左侧文档列表面板
        ChunkList.tsx           ← 右侧 Chunk 列表面板
        ChunkDrawer.tsx         ← Chunk 编辑侧边抽屉
        UploadModal.tsx         ← 上传文件弹窗
      App.tsx                   ← Master-Detail 布局根组件
      main.tsx
    index.html
    vite.config.ts              ← build.outDir = ../static/admin
    package.json
    tailwind.config.ts
    components.json             ← shadcn 配置

  static/
    admin/                      ← 构建产物（gitignore）

  app/
    main.py                     ← 新增 StaticFiles mount（在所有路由之后）
```

---

## 页面布局

**Master-Detail 左右分栏**，始终在同一页面内操作：

```
┌─────────────────────────────────────────────────────────────────┐
│  顶部导航：Logo + "知识库管理"                       [上传文档]  │
├──────────────────┬──────────────────────────────────────────────┤
│                  │                                              │
│  文档列表        │  Chunk 列表（选中文档的所有 chunks）         │
│                  │                                              │
│  ─ GB 2761 (42)  │  [type ▼] [搜索...]              [+ 新增]   │
│  ─ GB 5009 (35)  │  ─────────────────────────────────────────  │
│  ─ GB 14880 (28) │  scope   │ 本标准适用于...    │ ✏️  🗑️     │
│                  │  def     │ 真菌毒素是指...     │ ✏️  🗑️     │
│  [上传新文档]    │  table   │ AFB1 限量：0.5...  │ ✏️  🗑️     │
│                  │                                              │
└──────────────────┴──────────────────────────────────────────────┘
                                                    ┌─────────────┐
                                                    │ Chunk Drawer│
                                                    │ type [▼]    │
                                                    │ content     │
                                                    │ [textarea]  │
                                                    │ section_path│
                                                    │ [tags]      │
                                                    │ metadata    │
                                                    │ [JSON only] │
                                                    │ [保存][取消]│
                                                    └─────────────┘
```

---

## 数据模型说明

### 重要：两套 Chunk 数据结构并存

代码库中存在新旧两套切分流水线，写入 ChromaDB 的 metadata 字段不同：

| 字段 | 旧流水线（strategy/） | 新流水线（parser_workflow/） |
|------|----------------------|------------------------------|
| 类型字段 | `content_type`（枚举） | `semantic_type`（字符串）+ `structure_type` |
| 章节路径 | `section_path: List[str]` | `section_path: List[str]` |

### `GET /api/doc/chunks` 实际返回结构

```typescript
interface ChunkResponse {
  id: string;
  content: string;
  metadata: Record<string, unknown>; // 所有分类/路径字段都在这里
}
```

**前端读取字段时必须从 `metadata` 中取**，例如：
- `chunk.metadata.content_type` 或 `chunk.metadata.semantic_type`
- `chunk.metadata.section_path`

### Admin UI 的兼容策略

- **类型字段展示**：优先显示 `metadata.content_type`，若不存在则显示 `metadata.semantic_type`
- **类型过滤注意**：`GET /api/doc/chunks` 的 `content_type` 过滤参数对新流水线数据（用 `semantic_type` 字段）无效，会静默返回空。前端需先检测当前文档数据来自哪套流水线（判断第一条 chunk 的 metadata 是否含 `content_type`），若为新流水线则在客户端过滤（因为新流水线文档通常数量可控），若为旧流水线则传服务端参数。后续可在后端统一修复过滤逻辑。
- **ChunkDrawer 编辑字段**：
  - `content`（顶层字段，直接编辑）
  - `content_type` / `semantic_type`（视数据来源显示对应字段）
  - `section_path`（tag 列表）
  - 其余 `metadata` 字段：以 JSON 只读展示，折叠

---

## 组件详细设计

### `DocumentList`

- 展示所有已入库文档，每张卡片显示：
  - 文档标题（`doc_title`）
  - Chunk 总数
  - content_type 分布色块（从 `DocumentInfo.content_types` 取）
- 点击卡片高亮选中，右侧 `ChunkList` 联动刷新
- 顶部「上传文档」按钮触发 `UploadModal`
- 每张卡片右上角「删除」按钮，需 `AlertDialog` 二次确认

### `ChunkList`

- 展示选中文档的所有 chunk
- 工具栏：
  - 类型下拉过滤（从当前文档已有类型中枚举）
  - 文本搜索框（**服务端搜索**，发请求携带 `search` 参数，与分页不冲突）
  - 「+ 新增 Chunk」按钮
- 每行展示：类型 badge、content 预览（截断 80 字符）、section_path
- 操作列：✏️ 编辑（打开 Drawer）、🗑️ 删除（二次确认）
- **分页**：每次加载 50 条（`limit=50&offset=N`），滚动到底加载更多
  - 注：文本搜索走服务端接口，而非前端内存过滤，保证与分页兼容

### `ChunkDrawer`（shadcn `Sheet`）

| 字段 | 控件 | 说明 |
|------|------|------|
| `content` | shadcn `Textarea` | 顶层字段，必填 |
| `content_type` 或 `semantic_type` | shadcn `Select` | 视数据来源显示 |
| `section_path` | 自定义 tag 输入 | 可增删节点 |
| 其余 `metadata` | 只读 JSON 展示 | 折叠，不可编辑 |

底部操作：**保存**、**取消**、**删除**（仅编辑模式，需二次确认）

### `UploadModal`（shadcn `Dialog`）

- 拖拽或点击选择 `.md` 文件（支持多文件批量上传）
- 切分策略下拉选择：`heading` / `text` / `table` / `structured` / `parent_child`（共 5 种）
- 上传进度条
- 完成后自动关闭并刷新文档列表

---

## API 集成

### 现有接口（直接使用）

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/doc/documents` | 文档列表 |
| `GET` | `/api/doc/chunks?doc_id=&limit=&offset=` | Chunk 列表（分页） |
| `POST` | `/api/doc/upload` | 上传文档（multipart/form-data，包含 `file` + `strategy`）|
| `DELETE` | `/api/doc/documents/{doc_id}` | 删除文档 |
| `POST` | `/api/doc/documents/{doc_id}/reprocess` | 重新切分文档（可选触发） |

### 需要新增的后端接口

| 方法 | 路径 | 用途 |
|------|------|------|
| `PUT` | `/api/doc/chunks/{chunk_id}` | 更新 chunk（content + metadata 字段）|
| `DELETE` | `/api/doc/chunks/{chunk_id}` | 删除单个 chunk |
| `POST` | `/api/doc/chunks` | 新增 chunk（需指定 `doc_id`）|
| `GET` | `/api/doc/chunks/search?doc_id=&q=&limit=&offset=` | 服务端文本搜索（支持分页）|

---

## 错误处理

- API 错误统一通过 toast 提示（shadcn `Sonner`）
- 删除操作（文档 & chunk）均需 `AlertDialog` 二次确认
- 乐观更新：删除/编辑后本地先更新状态，请求失败时回滚并提示

---

## FastAPI 静态托管

在 `app/main.py` 所有路由注册（包括 `web_router`）**之后**添加：

```python
from fastapi.staticfiles import StaticFiles

# 必须在 include_router 之后，否则可能被 API 路由覆盖
app.mount("/admin", StaticFiles(directory="static/admin", html=True), name="admin")
```

注意：`static/admin/` 目录需提前存在（可在 CI 或 Makefile 里执行 `admin/` 的构建）。

---

## 开发工作流

```bash
# 开发模式（Vite dev server，自动代理 /api 到 FastAPI）
cd agent-server/admin
pnpm dev   # vite.config.ts 中配置 server.proxy: { '/api': 'http://localhost:9999' }

# 构建（产物输出到 agent-server/static/admin/）
pnpm build
```

---

## 实现顺序

1. 搭建 Vite + React + shadcn 项目骨架，配置 FastAPI 静态托管
2. `DocumentList` + `GET /api/doc/documents`
3. `UploadModal` + `POST /api/doc/upload`（5 种策略）
4. `ChunkList` + `GET /api/doc/chunks`（分页 + 类型过滤）
5. 后端新增 4 个接口：chunk PUT / DELETE / POST + chunks/search
6. `ChunkDrawer` 编辑 / 新增（兼容新旧数据模型）
7. 删除文档 & 删除 chunk（均带二次确认）
8. 服务端文本搜索（`GET /api/doc/chunks/search`）
9. 细节完善：loading 状态、空状态、错误边界
