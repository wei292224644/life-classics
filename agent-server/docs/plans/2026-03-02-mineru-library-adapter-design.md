# MinerU 库模式适配器设计

> 与 [MinerU demo](https://github.com/opendatalab/MinerU/blob/master/demo/demo.py) 对齐：使用 MinerU 库 `parse_doc`，backend 与 HTTP 由配置项控制。

## 1. 目标与范围

**目标**：将当前基于「自定义 HTTP POST /convert」的 MinerU 适配器改为完全按官方 demo 方式，通过 **MinerU 库** 的 `parse_doc` 完成 PDF→Markdown；backend 作为配置项，是否走 HTTP 由 `MINERU_SERVICE_URL` 与 backend 类型决定。

**范围**：
- **修改**：`app/core/pdf/mineru_adapter.py`（实现改为调库 + 读产出 `.md`）；`app/core/config.py`（新增/调整 MinerU 配置项）；`tests/core/pdf/test_mineru_adapter.py`（按新行为编写/更新用例）。
- **不变**：`pdf_to_markdown(pdf_path, ...)` 的对外签名仍返回 `str`（Markdown 文本）；`app/core/kb/__init__.py` 中对 `import_pdf_via_mineru` 的调用方式不变。
- **移除**：不再依赖自定义 POST /convert 接口；`MINERU_SERVICE_URL` 仅当 backend 为 `*-http-client` 时作为 MinerU 库的 `server_url` 使用。

**依赖**：在 `pyproject.toml` 中增加 `mineru`（版本约束与当前 Python 兼容，如 `>=2.0.0`）。

---

## 2. 配置项

在 `app/core/config.py` 的 Settings 中新增/调整：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `MINERU_BACKEND` | str | `"hybrid-auto-engine"` | 与 demo 一致：`pipeline`、`hybrid-auto-engine`、`vlm-auto-engine`、`vlm-http-client`、`hybrid-http-client` |
| `MINERU_SERVICE_URL` | str | `""` | 可选。非空且 backend 为 `*-http-client` 时，作为 `parse_doc(..., server_url=...)` 传入 |
| `MINERU_LANG` | str | `"ch"` | `parse_doc(..., lang=...)`，如 demo 支持 `ch`、`en` 等 |
| `MINERU_REQUEST_TIMEOUT` | int | 300 | 保留用于将来对解析过程的超时控制；当前库调用若无超时参数可先不传 |

**逻辑约定**：仅当 `MINERU_SERVICE_URL` 非空且 `MINERU_BACKEND` 为 `vlm-http-client` 或 `hybrid-http-client` 时传入 `server_url`；否则 `server_url=None`，使用本地 backend。

---

## 3. 适配器接口与实现要点

**对外接口**：保持现有签名。

- `pdf_to_markdown(pdf_path: str, service_url: Optional[str] = None, timeout: Optional[int] = None) -> str`
- `service_url` / `timeout` 仍可作为覆盖参数（实现时优先用入参，否则用 settings）。

**实现要点**：

1. **依赖**：在适配器内按需导入 `parse_doc`（如 `from mineru.demo.demo import parse_doc`，或官方推荐入口）。避免在模块顶层导入 MinerU 其它重型依赖。
2. **临时目录**：使用 `tempfile.mkdtemp()` 作为 `parse_doc(..., output_dir=...)` 的输出目录；读取完 `.md` 后用 try-finally 删除临时目录。
3. **调用参数**：`parse_doc(path_list=[Path(pdf_path)], output_dir=tmpdir, lang=..., backend=..., method="auto", server_url=...)`，其中 `server_url` 按第 2 节约定取值。
4. **取 Markdown**：在 `output_dir` 下递归查找 `**/*.md`，取与当前 PDF 文件名 stem 一致（或唯一）的 `.md`，读取内容并返回；未找到则抛出明确异常。
5. **兼容**：当前版本仅支持库模式，不保留自定义 POST /convert 分支。

---

## 4. 调用流程与输出

1. 调用方传入 `pdf_path`（及可选的 `service_url`、`timeout`）。
2. 校验 `pdf_path` 存在且为文件；否则抛出 `FileNotFoundError`。
3. 根据配置与入参确定 `backend`、`server_url`。
4. 创建临时目录，调用 `parse_doc(...)`。
5. 在 `output_dir` 下查找生成的 `.md` 文件并读取为字符串。
6. 清理临时目录，返回 Markdown 字符串。

**输出**：返回单个 `str`，即该 PDF 对应的整份 Markdown；不返回中间文件路径或其它产物。若未生成 `.md`，按第 3 节约定抛出异常。

---

## 5. 错误处理与测试

**错误处理**：
- 文件不存在：在调用 MinerU 前抛出 `FileNotFoundError`。
- `parse_doc` 异常：捕获后向上抛出，可保留 `__cause__` 或原样抛出。
- 未生成 .md：抛出明确异常（如 `FileNotFoundError` 或 `RuntimeError`）。
- 临时目录：try-finally 确保解析失败时也删除。

**测试**：
- 单元测试：mock `parse_doc`，在 mock 内于给定 `output_dir` 写入临时 `.md`，断言 `pdf_to_markdown` 返回该内容；可选断言「未生成 .md」与「文件不存在」时的异常。
- 集成/手动：在安装 MinerU 且环境满足 backend 的前提下，用真实 PDF 验证；可写在文档中，不强制 CI。

---

## 参考

- [MinerU demo](https://github.com/opendatalab/MinerU/blob/master/demo/demo.py)（含 HTTP 调用注释：`vlm-http-client` / `hybrid-http-client` + `server_url`）
