# 批量上传 MD 文件脚本 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个脚本，批量上传指定目录下的 MD 文件到知识库，支持跳过已上传文件、并发上传、失败报告。

**Architecture:** 共三处改动：(1) `DocumentInfo` Pydantic 模型新增 `title` 字段；(2) `get_all_documents` 从 ChromaDB 元数据中提取并返回 `title`；(3) 新建脚本使用 `requests` + `ThreadPoolExecutor` 并发上传，按行解析 SSE 流，汇总结果。

**Tech Stack:** Python 3.12, `requests`（已有）, `concurrent.futures.ThreadPoolExecutor`, FastAPI/Pydantic（已有）

---

## 文件变更一览

| 操作 | 文件 | 说明 |
|------|------|------|
| Modify | `server/api/documents/models.py` | `DocumentInfo` 增加 `title: str = ""` |
| Modify | `server/api/documents/service.py` | `get_all_documents` 提取并返回 `title` |
| Create | `server/scripts/__init__.py` | 空文件，使 scripts 成为包 |
| Create | `server/scripts/batch_upload.py` | 批量上传脚本主体 |
| Modify | `server/tests/api/test_documents.py` | 为 `title` 字段补充测试（如果该文件存在） |

---

## Task 1: `DocumentInfo` 模型增加 `title` 字段

**Files:**
- Modify: `server/api/documents/models.py`
- Test: `server/tests/api/test_documents.py`（如存在）

- [ ] **Step 1: 确认现有测试状态**

```bash
cd server
uv run pytest tests/api/ -v 2>&1 | head -40
```

记录当前通过/失败数量作为基准。

- [ ] **Step 2: 修改 `DocumentInfo` 模型**

编辑 `server/api/documents/models.py`，在 `doc_id` 后面加入 `title` 字段：

```python
from pydantic import BaseModel


class DocumentInfo(BaseModel):
    doc_id: str
    title: str = ""
    standard_no: str
    doc_type: str
    chunks_count: int


class DocumentsListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int
```

- [ ] **Step 3: 确认原有测试仍通过**

```bash
cd server
uv run pytest tests/api/ -v
```

预期：所有 api 测试继续通过（新字段有默认值，不会破坏现有行为）。

- [ ] **Step 4: Commit**

```bash
git add server/api/documents/models.py
git commit -m "feat(documents): add title field to DocumentInfo model"
```

---

## Task 2: `get_all_documents` 返回 `title`

**Files:**
- Modify: `server/api/documents/service.py:26-37`

- [ ] **Step 1: 修改 `get_all_documents`**

编辑 `server/api/documents/service.py`，在 `doc_map` 初始化块中增加 `title` 提取：

```python
if doc_id not in doc_map:
    doc_map[doc_id] = {
        "doc_id": doc_id,
        "title": meta.get("title", ""),   # 新增
        "standard_no": meta.get("standard_no", ""),
        "doc_type": meta.get("doc_type", ""),
        "chunks_count": 0,
    }
doc_map[doc_id]["chunks_count"] += 1   # 保持不变
```

- [ ] **Step 2: 确认测试通过**

```bash
cd server
uv run pytest tests/api/ -v
```

预期：全部通过。

- [ ] **Step 3: Commit**

```bash
git add server/api/documents/service.py
git commit -m "feat(documents): return title field in get_all_documents"
```

---

## Task 3: 新建批量上传脚本

**Files:**
- Create: `server/scripts/__init__.py`
- Create: `server/scripts/batch_upload.py`

- [ ] **Step 1: 创建 scripts 包**

创建空文件 `server/scripts/__init__.py`（内容为空）。

- [ ] **Step 2: 创建批量上传脚本**

创建 `server/scripts/batch_upload.py`，内容如下：

```python
"""
批量上传 MD 文件到知识库。

使用方式：
    cd server
    uv run python3 scripts/batch_upload.py

跳过已上传的文件（通过 title 字段去重）。
失败文件不影响其他文件的上传。
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ── 配置 ──────────────────────────────────────────────────────────────────────
SOURCE_DIR = Path("/Users/wwj/Desktop/myself/download_test/reorganized")
API_BASE = "http://localhost:9999"
CONCURRENCY = 3
TIMEOUT_PER_FILE = 300  # 秒


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def get_uploaded_titles() -> set[str]:
    """从服务器获取已上传文档的 title 集合。"""
    try:
        resp = requests.get(f"{API_BASE}/api/documents", timeout=10)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        return {d["title"] for d in docs if d.get("title")}
    except requests.ConnectionError:
        print(f"[错误] 无法连接到服务器 {API_BASE}，请确认服务已启动。")
        raise SystemExit(1)


def clean_title(path: Path) -> str:
    """
    从文件路径提取 clean title：
      GB xxx.reorganized.md → GB xxx
      GB xxx.md             → GB xxx
    """
    stem = path.stem  # 去掉 .md
    if stem.endswith(".reorganized"):
        stem = stem[: -len(".reorganized")]
    return stem


def upload_file(path: Path) -> tuple[str, str | None]:
    """
    上传单个文件。返回 (clean_title, error_message)。
    error_message 为 None 表示成功。
    """
    title = clean_title(path)
    upload_filename = title + ".md"

    try:
        with open(path, "rb") as f:
            file_content = f.read()

        with requests.post(
            f"{API_BASE}/api/documents",
            files={"file": (upload_filename, file_content, "text/markdown")},
            stream=True,
            timeout=TIMEOUT_PER_FILE,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "done":
                    return title, None
                if event.get("type") == "error":
                    return title, event.get("message", "未知错误")
            # SSE 流结束但未收到 done/error
            return title, "SSE 流意外结束"

    except requests.Timeout:
        return title, f"超时（>{TIMEOUT_PER_FILE}s）"
    except Exception as e:
        return title, str(e)


# ── 主逻辑 ────────────────────────────────────────────────────────────────────

def main() -> None:
    uploaded_titles = get_uploaded_titles()

    all_files = sorted(SOURCE_DIR.glob("*.md"))
    to_upload = [f for f in all_files if clean_title(f) not in uploaded_titles]
    skipped = len(all_files) - len(to_upload)

    if not to_upload:
        print(f"全部文件已上传，跳过 {skipped} 个。")
        return

    print(f"共 {len(all_files)} 个文件，跳过 {skipped} 个，待上传 {len(to_upload)} 个\n")

    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(upload_file, f): f for f in to_upload}
        for future in as_completed(futures):
            title, error = future.result()
            if error is None:
                successes.append(title)
                print(f"  ✓ {title}")
            else:
                failures.append((title, error))
                print(f"  ✗ {title}：{error}")

    print(f"\n── 汇总 ──────────────────────────────────────────")
    print(f"✓ 成功 {len(successes)} 个")
    if failures:
        print(f"✗ 失败 {len(failures)} 个：")
        for title, error in failures:
            print(f"    - {title}.md：{error}")
    print(f"→ 跳过（已上传）{skipped} 个")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 验证脚本语法无误**

```bash
cd server
uv run python3 -c "import scripts.batch_upload; print('语法 OK')"
```

预期输出：`语法 OK`

- [ ] **Step 4: Commit**

```bash
git add server/scripts/__init__.py server/scripts/batch_upload.py
git commit -m "feat(scripts): add batch_upload.py for bulk MD file ingestion"
```

---

## Task 4: 冒烟测试

确认整体流程可跑通（需要服务已启动）。

- [ ] **Step 1: 确认服务正在运行**

```bash
curl -s http://localhost:9999/api/documents | python3 -m json.tool | head -10
```

预期：返回 JSON，包含 `documents` 数组。

- [ ] **Step 2: 运行脚本**

```bash
cd server
uv run python3 scripts/batch_upload.py
```

预期：
- 输出已跳过文件数 + 待上传文件数
- 每个文件显示 ✓ 或 ✗
- 最后打印汇总

- [ ] **Step 3: 再次运行脚本（验证幂等性）**

```bash
uv run python3 scripts/batch_upload.py
```

预期：`全部文件已上传，跳过 N 个。` — 不重复上传。

- [ ] **Step 4: 最终 Commit（如有未提交内容）**

```bash
git status
# 若有未提交内容：
git add -A
git commit -m "chore: batch upload smoke test verified"
```
