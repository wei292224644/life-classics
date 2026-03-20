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

- 引入 `react-router-dom`，将应用从单页状态驱动改为路由驱动

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
├── Layout
│   ├── Header（保持不变：⚡ KB Admin + KBStats + 清空按钮）
│   ├── TabNav（新增：Chunks · 上传 · 对话）
│   └── <Outlet>（路由内容区域）
└── Toaster
```

**TabNav 实现：**
- 使用 `<NavLink>` 实现，自动处理 active 样式
- active 标签：`color: foreground + border-bottom: 2px solid purple`
- 非 active 标签：`color: muted`

---

## 上传功能（UploadPage）

### 布局：左右分栏

```
UploadPage
├── 左栏（上传区）
│   ├── 拖拽 / 点击选择 .md 文件区域
│   ├── 已选文件名展示
│   └── "上传并入库"按钮（上传中禁用 + loading）
└── 右栏（上传记录）
    └── 历史记录列表（最近上传的文档，含 chunks_count 和时间）
```

### 交互流程

1. 用户拖拽或点击选择 `.md` 文件
2. 显示文件名与大小
3. 点击"上传并入库" → 按钮禁用，显示 loading spinner
4. 成功：右栏历史记录新增一条（`✓ 文件名 · N chunks · 刚刚`）
5. 失败：toast 错误提示 + 按钮恢复可用

### 上传记录

- 仅存于前端内存（不持久化，刷新重置）
- 展示字段：文件名、chunks_count、上传时间（相对时间）
- 最多保留最近 20 条

### API 调用

```
POST /api/documents
Content-Type: multipart/form-data

file: <File>
strategy: "text"  （固定，不暴露给用户）
```

响应字段（`UploadDocumentResponse`）：
- `success: bool`
- `message: str`
- `doc_id: string | null`
- `chunks_count: int`
- `file_name: str`

### API 客户端新增

```typescript
api.documents.upload(file: File): Promise<UploadDocumentResponse>
```

---

## 对话功能（ChatPage）

### 布局：全宽对话流

```
ChatPage（flex-col，全高）
├── 消息列表区域（flex-1，可滚动，滚动到底部）
│   ├── 空状态（无消息时：居中引导语）
│   ├── 用户消息（右对齐，紫色气泡）
│   └── AI 消息（左对齐）
│       ├── 内容区（Markdown 渲染）
│       └── 来源折叠区（sources 不为空时显示）
└── 输入区（底部，border-top）
    ├── 多行文本框（Enter 发送，Shift+Enter 换行）
    └── 发送按钮（发送中禁用 + loading）
```

### 来源展示（折叠）

AI 消息下方附带一个可折叠的来源区域：

```
📚 召回来源 · N 个 chunk  ▶
  （展开后显示：）
  · doc_id / section_path · 相关度 0.94
  · doc_id / section_path · 相关度 0.87
```

默认折叠，点击展开/收起。

### 多轮对话

- 前端维护 `messages: { role: 'user' | 'assistant', content: string }[]`
- 每次发送将完整历史作为 `conversation_history` 传给后端
- `thread_id` 固定为 `"console-test"`

### 顶部操作

- "清空对话"按钮（TabNav 右侧）：重置 messages 状态，无需确认弹窗

### Markdown 渲染

引入 `react-markdown` 渲染 AI 回复内容。

### API 调用

```
POST /api/agent/chat
Content-Type: application/json

{
  "message": "用户输入",
  "conversation_history": [...],
  "thread_id": "console-test"
}
```

### API 客户端新增

```typescript
api.agent.chat(payload: {
  message: string
  conversation_history: { role: string; content: string }[]
  thread_id: string
}): Promise<AgentResponse>
```

响应字段（`AgentResponse`）：
- `content: string`（Markdown 格式）
- `sources: SearchResult[] | null`
- `tool_calls: object[] | null`

---

## 新增依赖

| 包 | 用途 |
|---|---|
| `react-router-dom` | 路由 |
| `react-markdown` | AI 回复 Markdown 渲染 |

---

## 文件变更清单

### 新建文件

| 文件 | 说明 |
|---|---|
| `src/pages/UploadPage.tsx` | 上传页面 |
| `src/pages/ChatPage.tsx` | 对话页面 |
| `src/components/TabNav.tsx` | 标签导航组件 |
| `src/components/Layout.tsx` | 包含 Header + TabNav + Outlet 的布局组件 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `src/App.tsx` | 引入 BrowserRouter，配置路由，移除原有布局逻辑 |
| `src/api/client.ts` | 新增 `documents.upload` 和 `agent.chat` 方法 |
| `src/api/types.ts` | 新增 `UploadDocumentResponse`、`AgentChatRequest`、`AgentResponse` 类型 |
| `package.json` | 新增 react-router-dom、react-markdown 依赖 |
