# 控制台新增上传与对话功能设计文档

**日期：** 2026-03-20
**状态：** 已确认

---

## 背景与目标

当前控制台（`web/apps/console/`）仅支持 Chunk 浏览与编辑。本次新增两个长期功能：

1. **上传文档**：支持上传 Markdown 文件，触发后端 Parser 流水线完成知识库录入
2. **知识库对话**：与主 RAG Agent 对话，测试 Agent 能力与知识库召回策略

---

## 技术栈变更

| 包 | 用途 | 版本策略 |
|---|---|---|
| `react-router-dom` | 路由 | 直接写版本号 `^7`，不走 monorepo catalog |
| `react-markdown` | AI 回复 Markdown 渲染 | 直接写版本号 `^9`，不走 monorepo catalog |

---

## 路由结构

```
/          → 重定向到 /chunks
/chunks    → 现有 DocList + ChunkList 两列布局（零改动）
/upload    → UploadPage（新建）
/chat      → ChatPage（新建）
```

---

## 整体布局

```
App（BrowserRouter）
├── Layout（flex flex-col h-screen，继承全屏高度约束）
│   ├── Header（保持不变：⚡ KB Admin + KBStats + 清空按钮）
│   ├── TabNav（新增：Chunks · 上传 · 对话）
│   └── <Outlet>（flex-1，overflow-hidden）
└── Toaster
```

**TabNav 实现：** 使用 `<NavLink end>`（每个链接均加 `end` 属性，避免前缀误匹配），通过 `isActive` 控制 active 样式（`color: foreground + border-bottom: 2px solid purple`），非 active 为 `color: muted`。

**KBStats 刷新：** stats 状态保留在 Layout 层。Layout 挂载时调用一次 `api.kb.stats()` 初始化数据，此后仅在 `refreshStats()` 被调用时更新。`refreshStats` 回调通过 props 传递给 UploadPage，上传成功后由 UploadPage 调用。

---

## 上传功能（UploadPage）

### 布局：左右分栏

```
UploadPage（flex，gap-5，padding）
├── 左栏（flex-1）— 上传区
│   ├── 拖拽 / 点击选择 .md 文件区域（dashed border）
│   ├── 已选文件名 + 大小展示
│   └── "上传并入库"按钮
└── 右栏（flex-1）— 流水线进度面板
    └── 最近一次上传的阶段状态（上传前为空）
```

### 文件校验（前端）

- 仅接受 `.md` 扩展名，其他格式在选择/拖入时提示"仅支持 Markdown 文件"并拒绝
- 文件大小上限 **5MB**，超出时提示"文件过大，请上传 5MB 以内的文件"
- 重复上传同名文件允许（后端会生成新 doc_id），历史记录不去重

### 交互流程

1. 拖拽或点击选择 `.md` 文件（前端校验通过后显示文件名与大小）
2. 点击"上传并入库" → 按钮禁用，左栏显示流水线进度面板（见下方）
3. 成功：进度面板所有阶段标记完成，调用 `refreshStats()` 更新 Header 统计
4. 失败：进度面板标记失败阶段，toast 错误提示，按钮恢复可用

### 上传进度面板

由于后端 `POST /api/documents` 是单一阻塞请求（无实时进度事件），采用**基于计时器的阶段模拟**方案：在请求发出后，按固定间隔（约 3 秒）依次点亮 Parser 流水线的各个阶段，直到请求返回后强制完成所有阶段。

流水线阶段列表（来自 `server/parser/graph.py`，共 9 个节点）：

| 阶段 | 说明 |
|---|---|
| 1. 解析 Markdown | 按标题切分为原始 chunk |
| 2. 清洗内容 | 去噪、格式规范化 |
| 3. 识别结构类型 | LLM 推断 paragraph / list / table 等 |
| 4. 切片 | 按粒度进一步细分 |
| 5. 分类语义类型 | LLM 分类 limit / procedure / definition 等 |
| 6. 处理低置信度 | 二次 LLM 判断 |
| 7. 交叉引用富化 | 解析表格引用等 |
| 8. 内容转换 | 表格→自然语言 |
| 9. 合并相邻 Chunk | 合并同类 chunk |

**UI 形态：** 垂直步骤列表，每个阶段有三种状态：
- `pending`：灰色圆点 + 阶段名
- `active`：紫色 spinner + 阶段名（加粗）
- `done`：绿色 ✓ + 阶段名

**超时保护：** 请求超过 **180 秒**未返回，标记当前阶段为失败并展示超时错误。

**状态持久化：** 最近一次上传的阶段状态（文件名、各阶段结果、最终 chunks_count）使用 `localStorage`（key: `kb-last-upload`）持久化，刷新后右栏仍展示上次结果。新的上传开始时覆盖旧状态。

### API 调用细节

上传接口**不能使用**通用 `request()` 函数（其强制设置 `Content-Type: application/json` 会破坏 multipart boundary）。需直接使用 `fetch` + `FormData`：

```typescript
// api/client.ts 中单独实现
async upload(file: File): Promise<UploadDocumentResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('strategy', 'text')
  const res = await fetch(`${BASE_URL}/documents`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
```

### 类型定义（新增至 types.ts）

```typescript
export interface UploadDocumentResponse {
  success: boolean
  message: string
  doc_id: string | null
  chunks_count: number
  file_name: string
  strategy: string
}
```

---

## 对话功能（ChatPage）

### 布局：全宽对话流

```
ChatPage（flex flex-col，h-full）
├── 消息列表区域（flex-1，overflow-y-auto）
│   ├── 空状态（初始）
│   ├── 用户消息（右对齐，紫色气泡）
│   └── AI 消息（左对齐）
│       ├── Markdown 内容
│       └── 来源折叠区（预留，当前隐藏）
└── 输入区（border-top，shrink-0）
    ├── 多行文本框
    └── 发送按钮
```

### 空状态

消息列表为空时居中显示：

```
💬
开始与知识库对话
提问关于 GB 标准的任何问题
```

### 消息样式

- **用户消息**：右对齐，紫色气泡（`bg-purple-700 text-white`），圆角 `12px 12px 2px 12px`
- **AI 消息**：左对齐，深色背景卡片（`bg-muted border`），内容使用 `react-markdown` 渲染

### 来源展示（预留）

> **注意：** 当前后端 `_handle_national_standard_chat` 固定返回 `sources: null`，来源区域 UI 预留但不渲染。待后端填充 sources 字段后自动生效。

UI 结构（当 `sources` 不为 null 且长度 > 0 时渲染）：

```
📚 召回来源 · N 个 chunk  ▶
  （展开后：）
  · doc_id / section_path · 相关度 0.94
```

### 输入区边界行为

- 空消息（纯空格）不允许发送，按钮禁用
- 发送中（loading）：输入框和发送按钮均禁用
- `Enter` 发送，`Shift+Enter` 换行

### 多轮对话

- 前端维护 `messages: { role: 'user' | 'assistant', content: string, sources?: SearchResult[] }[]`
- 使用 `localStorage`（key: `kb-chat-messages`）持久化，刷新和切换标签后恢复
- 发送时将 `messages` 中 role/content 映射为 `conversation_history` 传给后端
- `thread_id` 固定为 `"console-test"`

### 清空对话

TabNav 右侧"清空对话"按钮（仅在 `/chat` 路由下显示），点击后重置 messages 状态，无需确认弹窗。

### API 调用细节

```typescript
// api/client.ts 中新增
async chat(payload: AgentChatRequest): Promise<AgentResponse> {
  return request('/agent/chat', { method: 'POST', body: JSON.stringify(payload) })
}
```

### 类型定义（新增至 types.ts）

```typescript
export interface AgentChatRequest {
  message: string
  conversation_history: { role: string; content: string }[]
  thread_id: string
}

export interface SearchResult {
  id: string
  content: string
  metadata?: Record<string, unknown>
  relevance_score?: number
  relevance_reason?: string
}

export interface AgentResponse {
  content: string
  sources: SearchResult[] | null
  tool_calls: Record<string, unknown>[] | null
}
```

---

## 文件变更清单

### 新建文件

| 文件 | 说明 |
|---|---|
| `src/pages/UploadPage.tsx` | 上传页面（居中单栏，含流水线进度面板） |
| `src/pages/ChatPage.tsx` | 对话页面（全宽对话流） |
| `src/components/TabNav.tsx` | 标签导航，使用 NavLink |
| `src/components/Layout.tsx` | 全局布局（Header + TabNav + Outlet），管理 kbStats 状态 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `src/App.tsx` | 引入 BrowserRouter，配置路由（`/` 重定向、三个子路由），移除原有布局逻辑 |
| `src/api/client.ts` | 新增 `documents.upload`（直接 fetch + FormData）和 `agent.chat` 方法 |
| `src/api/types.ts` | 新增 `UploadDocumentResponse`、`AgentChatRequest`、`AgentResponse`、`SearchResult` 类型 |
| `package.json` | 新增 `react-router-dom@^7`、`react-markdown@^9` |

---

## 后续迭代 TODO

以下问题已识别，当前版本暂不处理，后续版本迭代：

| # | 问题 | 优先级 |
|---|---|---|
| 1 | AI 回复等待时缺少 typing indicator（消息列表末尾骨架屏） | 高 |
| 2 | 消息列表缺少自动滚动（新消息出现时滚动到底部，用户上翻时不强制） | 高 |
| 3 | Chat API 失败时无消息级错误展示（目前只有 toast，应插入红色错误气泡） | 中 |
| 4 | `react-markdown` 缺少代码高亮（需 `rehype-highlight` 或 `react-syntax-highlighter`） | 中 |
| 5 | 上传成功后文件输入未重置（用户需手动取消才能选新文件） | 中 |
| 6 | 拖拽区域缺少 hover 视觉反馈（文件悬浮时边框/背景变色） | 低 |
| 7 | `thread_id` 固定导致后端线程记忆无法清空（清空前端对话不清后端上下文） | 低 |
