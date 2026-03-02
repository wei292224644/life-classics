# MinerU 图片 VLM 描述追加 — 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 MinerU 产出 Markdown 后、入库前，用多模态 LLM 对每张图生成一段描述并追加在图片引用后，使图片语义可被检索。

**Architecture:** 新增模块从 Markdown 解析 `![](...)`、在给定 base_path 下解析图片路径并读图，调用 VLM 得到描述后按出现顺序在原引用后追加「图注：...」；该步骤在 MinerU 适配器内、在读取到 .md 之后且删除临时目录之前执行，以保证能访问图片文件；配置项控制是否启用、模型与超时。

**Tech Stack:** Python 3.10+，正则解析 Markdown 图片，多模态 LLM（DashScope/OpenAI/Ollama 等 vision API）。设计文档：`docs/plans/2026-03-02-mineru-image-description-design.md`。

---

## Task 1：新增图片描述配置项

**Files:**
- Modify: `app/core/config.py`

**Step 1：添加配置**

在 Settings 中新增：
- `MINERU_IMAGE_DESCRIPTION_ENABLED: bool = True`
- `MINERU_IMAGE_DESCRIPTION_MODEL: str = ""`（为空时复用 CHAT_MODEL 或约定不调用 VLM）
- `MINERU_IMAGE_DESCRIPTION_TIMEOUT: int = 30`
- `MINERU_IMAGE_DESCRIPTION_MAX_IMAGES: int = 50`（单文档最多处理图片数，可选）

**Step 2：Commit**

```bash
git add app/core/config.py
git commit -m "config: add MinerU image description (VLM) settings"
```

---

## Task 2：实现 Markdown 图片解析与描述追加模块

**Files:**
- Create: `app/core/pdf/markdown_image_describe.py`

**Step 1：写失败用例**

在 `tests/core/pdf/test_markdown_image_describe.py` 中：  
- 用例 1：输入无图片的 Markdown，断言 `enrich_markdown_with_image_descriptions(md, base_path)` 返回原字符串。  
- 用例 2：输入含 `![](subdir/a.png)` 的 Markdown，mock VLM 返回 "图内容简述"，mock 在 base_path 下存在 `subdir/a.png`，断言输出中该引用后追加了描述（如「图注：图内容简述」或约定格式）。

**Step 2：运行测试确认失败**

Run: `pytest tests/core/pdf/test_markdown_image_describe.py -v`  
Expected: FAIL（模块或函数不存在）。

**Step 3：最小实现**

在 `markdown_image_describe.py` 中：
- 函数 `enrich_markdown_with_image_descriptions(md_content: str, images_base_path: str) -> str`。
- 用正则匹配 Markdown 中所有 `![alt](path)` / `![](path)`，得到 path 列表；若 `MINERU_IMAGE_DESCRIPTION_ENABLED` 为 False 或无匹配，直接返回 `md_content`。
- 对每个 path（可选：限制为前 `MINERU_IMAGE_DESCRIPTION_MAX_IMAGES` 个）：在 `images_base_path` 下解析为绝对路径，若文件存在则读入 bytes；不存在则打日志并跳过。
- 调用「VLM 描述单图」的封装（见 Task 3），传入图片 bytes 与固定 prompt（如「请用一两句话描述图中内容，便于检索」），得到文本；超时或异常则该图不追加或追加占位，打日志。
- 按图片在 Markdown 中出现的顺序，将每个 `![](...)` 替换为「原引用 + 换行 + 图注：描述」；返回新字符串。

**Step 4：运行测试通过**

Run: `pytest tests/core/pdf/test_markdown_image_describe.py -v`  
Expected: PASS（在 Task 3 提供 VLM mock 或 stub 前提下）。

**Step 5：Commit**

```bash
git add app/core/pdf/markdown_image_describe.py tests/core/pdf/test_markdown_image_describe.py
git commit -m "feat(pdf): enrich markdown with VLM image descriptions"
```

---

## Task 3：VLM 视觉调用封装（单图 → 描述文本）

**Files:**
- Create: `app/core/llm/vision.py`（或并入现有 llm 模块）

**Step 1：实现最小接口**

- 函数 `describe_image(image_bytes: bytes, prompt: str = "...", timeout: int = 30) -> str`。
- 根据配置（如 `CHAT_PROVIDER` 或 `MINERU_IMAGE_DESCRIPTION_MODEL`）调用对应 vision API（DashScope 多模态、OpenAI vision、Ollama 视觉模型等）；若无可用 vision 配置则返回占位字符串或抛明确异常，便于测试时 mock。
- 超时与重试按配置处理；失败返回空字符串或占位，由调用方决定是否追加。

**Step 2：在 markdown_image_describe 中接入**

在 `markdown_image_describe.py` 中调用 `describe_image(image_bytes, prompt, timeout)`，不再内联 API 调用。

**Step 3：Commit**

```bash
git add app/core/llm/vision.py app/core/pdf/markdown_image_describe.py
git commit -m "feat(llm): add vision describe_image for MinerU image captions"
```

---

## Task 4：在 MinerU 适配器内接入图片描述步骤

**Files:**
- Modify: `app/core/pdf/mineru_adapter.py`

**Step 1：在「读取 .md 之后、删除临时目录之前」插入逻辑**

在现有流程中，当已从 `output_dir` 读取到 `md_content` 且即将删除临时目录前：  
- 若 `settings.MINERU_IMAGE_DESCRIPTION_ENABLED` 为 True，则 `md_content = enrich_markdown_with_image_descriptions(md_content, output_dir)`（或当前表示 MinerU 输出根目录的变量）。  
- 然后再删除临时目录并返回 `md_content`。

**Step 2：验证**

Run: 单元测试 `tests/core/pdf/test_markdown_image_describe.py` 及现有 MinerU 适配器测试；若有含图 PDF 可做一次手动导入验证。  
Expected: 行为符合设计，无回归。

**Step 3：Commit**

```bash
git add app/core/pdf/mineru_adapter.py
git commit -m "feat(pdf): run image description in mineru adapter before cleanup"
```

---

## Task 5：单元测试完善与 README（可选）

**Files:**
- Modify: `tests/core/pdf/test_markdown_image_describe.py`
- Modify: `README.md`

**Step 1：补充用例**

- 某张图 path 在 base_path 下不存在，断言该处不追加或占位、其余正常。  
- Mock VLM 抛异常，断言该图不追加或占位、不抛异常。

**Step 2：README**

在 README 中简述：MinerU 解析出的图片会经多模态 LLM 生成图注并追加到 Markdown，便于检索；配置项见 `MINERU_IMAGE_DESCRIPTION_*`。

**Step 3：Commit**

```bash
git add tests/core/pdf/test_markdown_image_describe.py README.md
git commit -m "test(pdf): image describe edge cases; docs: README image description"
```

---

## 执行方式说明

**Plan saved to `docs/plans/2026-03-02-mineru-image-description-implementation-plan.md`.**

1. **本会话内按任务推进** — 从 Task 1 起逐项实现并提交。  
2. **新会话中执行** — 在新会话中按本计划使用 executing-plans 逐 Task 执行并在检查点 review。

若 MinerU 适配器尚未改为库模式（无临时目录与 output_dir），需先完成 `2026-03-02-mineru-library-adapter-implementation-plan.md`，再执行本计划中依赖 `output_dir` 的 Task 2、4。
