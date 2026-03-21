# 批量上传 MD 文件脚本 设计文档

## 背景

`/Users/wwj/Desktop/myself/download_test/reorganized` 目录下存放持续增长的 GB 标准 Markdown 文件，需要一个脚本将它们批量上传到知识库，并支持：
- 跳过已上传的文件（幂等）
- 并发上传（加速）
- 失败时报告具体文件名和错误原因

---

## 文件命名约定

源文件名格式：`GB xxx.reorganized.md`

上传前需去除 `.reorganized`，上传时使用 `GB xxx.md` 作为文件名。这样 parser 会将 `GB xxx` 存为 `doc_metadata["title"]`，与去重逻辑保持一致。

---

## 改动一：`service.py` — `get_all_documents` 返回 `title`

**文件**：`server/api/documents/service.py`

`get_all_documents` 方法在构建 `doc_map` 时，从 ChromaDB 元数据中额外提取 `title` 字段并返回：

```python
doc_map[doc_id] = {
    "doc_id": doc_id,
    "title": meta.get("title", ""),   # 新增
    "standard_no": meta.get("standard_no", ""),
    "doc_type": meta.get("doc_type", ""),
    "chunks_count": 0,
}
```

`GET /api/documents` 响应中每条文档将包含 `title` 字段，供脚本去重使用。

---

## 改动二：新建批量上传脚本

**文件**：`server/scripts/batch_upload.py`

### 运行方式

```bash
cd server
uv run python3 scripts/batch_upload.py
```

### 核心流程

```
1. GET http://localhost:9999/api/documents
   → 提取所有已上传文档的 title 集合（uploaded_titles）

2. 扫描 SOURCE_DIR（固定路径）下所有 *.md 文件
   → 对每个文件计算 clean_title：
       去掉 .reorganized（如有），再去掉 .md 扩展名

3. 过滤：clean_title 已在 uploaded_titles 中的文件 → 跳过

4. 对待上传文件，用 asyncio.Semaphore(CONCURRENCY) 并发执行上传：
   - POST /api/documents，multipart/form-data
   - 文件名使用 clean_title + ".md"（去掉 .reorganized）
   - 消费 SSE 流，直到收到 {"type": "done"} 或 {"type": "error"}
   - 超时保护：单文件最长 300 秒

5. 汇总输出：
   ✓ 成功 N 个
   ✗ 失败 M 个：
       - 文件名1.md：错误原因
       - 文件名2.md：错误原因
   → 跳过（已上传）K 个
```

### 关键配置（脚本顶部常量）

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `SOURCE_DIR` | `/Users/wwj/Desktop/myself/download_test/reorganized` | 源文件目录 |
| `API_BASE` | `http://localhost:9999` | 服务地址 |
| `CONCURRENCY` | `3` | 最大并发上传数 |
| `TIMEOUT_PER_FILE` | `300` | 单文件超时（秒） |

### 依赖

仅使用 `httpx`（已在项目 `pyproject.toml` 中），无需额外安装。

---

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| SSE 流返回 `{"type": "error"}` | 记录为失败，保留错误消息 |
| 网络异常 / 连接失败 | 记录为失败，保留异常信息 |
| 单文件超时（>300s） | 记录为失败，提示超时 |
| 服务未启动 | 启动时立即失败，提示无法连接 |
| 文件编码非 UTF-8 | 服务端返回 error 事件，同上 |

失败的文件不影响其他文件的上传。

---

## 不在范围内

- 自动重试（用户可再次运行脚本，已成功的会被跳过）
- 递归扫描子目录
- 修改 `DocumentsListResponse` 模型（`title` 字段直接透传，不需要改 Pydantic 模型）
