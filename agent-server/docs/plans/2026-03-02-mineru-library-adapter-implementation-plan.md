# MinerU 库模式适配器 — 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 MinerU 适配器从「自定义 HTTP POST /convert」改为使用 MinerU 库的 `parse_doc`，与官方 demo 一致；backend 与 HTTP 由配置项控制。

**Architecture:** 在 `mineru_adapter` 内按需导入 `parse_doc`，用临时目录作为 `output_dir`，解析后在目录下查找生成的 `.md` 并读取返回；配置项决定 `backend` 与 `server_url`，调用方接口 `pdf_to_markdown(...)` 签名不变。

**Tech Stack:** Python 3.10+，mineru 库，tempfile，pathlib。设计文档：`docs/plans/2026-03-02-mineru-library-adapter-design.md`。

---

## Task 1：添加 mineru 依赖

**Files:**
- Modify: `pyproject.toml`

**Step 1：添加依赖**

在 `dependencies` 中增加一行：

```toml
"mineru>=2.0.0",
```

**Step 2：验证安装（可选）**

Run: `uv sync` 或 `pip install -e .`  
Expected: 安装成功，无冲突。

**Step 3：Commit**

```bash
git add pyproject.toml
git commit -m "deps: add mineru for PDF to Markdown (library mode)"
```

---

## Task 2：新增/调整 MinerU 配置项

**Files:**
- Modify: `app/core/config.py`

**Step 1：修改配置**

在 Settings 中：
- 将 `MINERU_SERVICE_URL` 默认值改为 `""`（或保留原默认，在文档中说明空则不用 HTTP）。
- 新增 `MINERU_BACKEND: str = "hybrid-auto-engine"`。
- 新增 `MINERU_LANG: str = "ch"`。
- 保留 `MINERU_REQUEST_TIMEOUT: int = 300`。

**Step 2：Commit**

```bash
git add app/core/config.py
git commit -m "config: add MINERU_BACKEND, MINERU_LANG for library adapter"
```

---

## Task 3：实现库模式适配器逻辑

**Files:**
- Modify: `app/core/pdf/mineru_adapter.py`

**Step 1：写失败用例（可选，用于 TDD）**

在 `tests/core/pdf/test_mineru_adapter.py` 中新增：mock `parse_doc`，在 mock 内于传入的 `output_dir` 下创建 `{stem}.md` 并写入固定内容，断言 `pdf_to_markdown` 返回该内容。若当前测试仍依赖 `requests.post`，先改为对「库模式」的测试。

**Step 2：运行测试确认失败**

Run: `pytest tests/core/pdf/test_mineru_adapter.py -v`  
Expected: 失败（如仍调用 requests 或返回与 mock 写入内容不一致）。

**Step 3：最小实现**

在 `mineru_adapter.py` 中：
- 移除对 `requests` 的依赖；按需导入：`from mineru.demo.demo import parse_doc`（若导入路径不同，以 MinerU 官方为准）。
- 实现：校验 `Path(pdf_path).exists()` 且为文件，否则 `raise FileNotFoundError(...)`。
- 根据 `settings.MINERU_BACKEND` 与 `settings.MINERU_SERVICE_URL`（或入参 `service_url`）决定 `backend` 与 `server_url`：仅当 `*_SERVICE_URL` 非空且 backend 为 `vlm-http-client` 或 `hybrid-http-client` 时传 `server_url`，否则 `server_url=None`。
- 使用 `tmpdir = tempfile.mkdtemp()`，在 `try` 中调用 `parse_doc(path_list=[Path(pdf_path)], output_dir=tmpdir, lang=..., backend=..., method="auto", server_url=...)`。
- 在 `output_dir` 下递归查找 `**/*.md`，取与 `Path(pdf_path).stem` 匹配（或唯一）的 `.md` 文件，读取内容并返回；未找到则 `raise FileNotFoundError` 或 `RuntimeError` 并说明未生成 md。
- 在 `finally` 中删除临时目录（如 `shutil.rmtree(tmpdir, ignore_errors=True)`）。

**Step 4：运行测试通过**

Run: `pytest tests/core/pdf/test_mineru_adapter.py -v`  
Expected: PASS（或跳过依赖 MinerU 的用例时仅确认无回归）。

**Step 5：Commit**

```bash
git add app/core/pdf/mineru_adapter.py tests/core/pdf/test_mineru_adapter.py
git commit -m "feat(pdf): MinerU adapter via library parse_doc, configurable backend"
```

---

## Task 4：单元测试完善（mock parse_doc）

**Files:**
- Modify: `tests/core/pdf/test_mineru_adapter.py`

**Step 1：编写 mock parse_doc 的测试**

- 使用 `@patch` 将适配器内使用的 `parse_doc` 替换为 mock。
- Mock 行为：在调用时获取 `output_dir`（即 `parse_doc` 的第二个位置参数或关键字参数），在该目录下创建子目录（若 MinerU 会创建子目录则模拟），并写入 `{pdf_stem}.md`，内容为固定字符串（如 `"## 测试\n内容"`）。
- 断言：`pdf_to_markdown("/tmp/test.pdf")` 返回包含该固定字符串。
- 可选：测试「文件不存在」时抛出 `FileNotFoundError`；测试「parse_doc 未生成 .md」时抛出预期异常。

**Step 2：运行测试**

Run: `pytest tests/core/pdf/test_mineru_adapter.py -v`  
Expected: PASS.

**Step 3：Commit**

```bash
git add tests/core/pdf/test_mineru_adapter.py
git commit -m "test(pdf): MinerU adapter tests with mocked parse_doc"
```

---

## Task 5：README 与设计引用（可选）

**Files:**
- Modify: `README.md`

**Step 1：更新说明**

在 README 中补充或调整 MinerU 相关说明：当前使用 MinerU 库模式；配置项 `MINERU_BACKEND`、`MINERU_SERVICE_URL`、`MINERU_LANG`；使用远程推理时配置 `*-http-client` 与 `MINERU_SERVICE_URL`。可注明设计文档路径：`docs/plans/2026-03-02-mineru-library-adapter-design.md`。

**Step 2：Commit**

```bash
git add README.md
git commit -m "docs: README MinerU library mode and config"
```

---

## 执行方式说明

**Plan complete and saved to `docs/plans/2026-03-02-mineru-library-adapter-implementation-plan.md`.**

两种执行方式：

1. **本会话内按任务推进（Subagent-Driven）** — 按 Task 1 → Task 5 顺序执行，每完成一个 Task 做一次 commit，适合边做边改。
2. **新会话中批量执行（Parallel Session）** — 在新会话中打开本仓库，使用 executing-plans 技能按计划逐项执行，并在检查点做 review。

你更倾向哪一种？若选 1，我将从 Task 1 开始在本会话内逐步实现并提交。
