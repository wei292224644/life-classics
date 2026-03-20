# Console 上传与对话功能 — 待迭代项

关联设计文档：`docs/superpowers/specs/2026-03-20-console-upload-chat-design.md`

---

| # | 问题 | 优先级 | 状态 |
|---|---|---|---|
| 1 | AI 回复等待时缺少 typing indicator（消息列表末尾骨架屏） | 高 | 待处理 |
| 2 | 消息列表缺少自动滚动（新消息出现时滚到底部，用户上翻时不强制） | 高 | 待处理 |
| 3 | Chat API 失败时无消息级错误展示（应插入红色错误气泡，而非仅 toast） | 中 | 待处理 |
| 4 | `react-markdown` 缺少代码高亮（需 `rehype-highlight` 或 `react-syntax-highlighter`） | 中 | 待处理 |
| 5 | 上传成功后文件输入未重置（用户需手动取消才能选新文件） | 中 | 待处理 |
| 6 | 拖拽区域缺少 hover 视觉反馈（文件悬浮时边框/背景变色） | 低 | 待处理 |
| 7 | `thread_id` 固定导致后端线程记忆无法随前端清空（清空 UI 对话不清后端上下文） | 低 | 待处理 |
