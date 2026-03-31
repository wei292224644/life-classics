# Analysis Pipeline Spec

**Date:** 2026-03-31  
**Status:** Approved  
**Scope:** 从用户拍照到结果页的完整分析管道——接口设计与内部架构

---

## 1. 概述

分析管道对客户端呈现为**一个任务**：提交图片，轮询进度，拿到结果。内部由四个独立组件串联，各自可单独替换或升级。

```
客户端视角：  POST /start  →  轮询 GET /status  →  拿到 ProductAnalysis
内部架构：    OCR → 解析 → 匹配 → 分析
```

---

## 2. 接口设计

### 2.1 启动分析

```
POST /api/analysis/start
Content-Type: multipart/form-data

image: <压缩后的图片字节流>
```

**响应：**
```json
{ "task_id": "uuid-v4" }
```

客户端收到 `task_id` 后立即开始轮询。

### 2.2 查询任务状态

```
GET /api/analysis/{task_id}/status
```

**响应结构：**
```json
{
  "task_id": "string",
  "status": "ocr" | "parsing" | "analyzing" | "done" | "failed",
  "error": null | "ocr_failed" | "no_ingredients_found" | "analysis_failed",
  "result": null | <ProductAnalysis>
}
```

- `status` 表示当前正在执行的阶段，`done` / `failed` 为终态
- `result` 仅在 `status: "done"` 时非 null
- `error` 仅在 `status: "failed"` 时非 null

### 2.3 轮询协议

- 客户端每 **1.5 秒**轮询一次
- 收到 `done` 或 `failed` 后停止轮询，跳转结果页或展示错误
- Redis 任务记录在终态后保留 **1 小时**（避免最后一次轮询 404）

### 2.4 任务状态与前端 Stepper 的映射

| status | 前端 Stepper 显示 |
|--------|-----------------|
| `ocr` | 第 1 步：识别配料表 |
| `parsing` | 第 2 步：解析成分 |
| `analyzing` | 第 3 步：生成评估报告 |
| `done` | 完成，跳转结果页 |
| `failed` | 展示错误提示 |

---

## 3. Redis 任务结构

Key: `analysis:{task_id}`，TTL：任务完成后 1 小时。

```json
{
  "task_id": "uuid",
  "status": "ocr",
  "error": null,
  "result": null,
  "created_at": "2026-03-31T10:00:00Z"
}
```

任务执行过程中直接更新 `status` 字段；完成时将完整 `ProductAnalysis` 写入 `result`。

---

## 4. 内部架构

四个组件顺序执行，每个组件只关心自己的输入输出，互相不耦合。

```
图片字节流
  │
  ▼
┌─────────────────────────────────┐
│ 组件 1：OCR                      │
│ 输入：图片字节流                   │
│ 输出：原始 OCR 文字                │
│ 实现：PaddleOCR-VL-1.5           │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 组件 2：解析                      │
│ 输入：原始 OCR 文字                │
│ 输出：成分名列表（轻度规范化）        │
│ 实现：LLM                        │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 组件 3：匹配                      │
│ 输入：成分名列表                   │
│ 输出：{ingredient_id, level}[] + 未知成分列表 │
│ 实现：Embedding 向量检索            │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 组件 4：分析                      │
│ 输入：匹配结果                     │
│ 输出：ProductAnalysis             │
│ 实现：产品缓存命中检查 + Agent       │
└─────────────────────────────────┘
```

### 4.1 组件 1：OCR

- **输入**：图片字节流（客户端已压缩，长边 ≤ 1024px）
- **输出**：原始 OCR 文字字符串（包含配料表、产品名称、营养成分表等所有内容）
- **实现**：PaddleOCR-VL-1.5，独立部署，主 FastAPI 通过内部 HTTP 调用
- **失败**：更新 Redis `status: "failed", error: "ocr_failed"`，终止管道

### 4.2 组件 2：解析

- **输入**：原始 OCR 文字
- **输出**：成分名列表，如 `["燕麦粉", "麦芽糊精", "阿斯巴甜", ...]`
- **实现**：LLM，定位配料表区域，提取成分名，去掉括号内功能说明（`"阿斯巴甜（甜味剂）"` → `"阿斯巴甜"`），不做深度标准化
- **失败**：OCR 文字中找不到配料表 → `status: "failed", error: "no_ingredients_found"`

### 4.3 组件 3：匹配

- **输入**：成分名列表
- **输出**：
  ```json
  {
    "matched": [{ "ingredient_id": 1, "name": "燕麦粉", "level": "t0" }],
    "unmatched": ["某未知成分"]
  }
  ```
- **实现**：每个成分名向量化后在配料库做 Embedding 检索，相似度低于阈值则归入 `unmatched`
- **降级**：`unmatched` 成分以 `level: "unknown"` 占位传入下一组件，不中断管道

### 4.4 组件 4：分析

- **输入**：匹配结果（matched + unmatched）
- **输出**：`ProductAnalysis`
- **实现**：
  1. 用 matched 的 `ingredient_id` 列表做产品相似度匹配，查 `product_analyses`
  2. 命中且未过期 → 直接返回缓存，`source: "db_cache"`
  3. 命中但过期 → 返回缓存，后台异步触发重新分析
  4. 未命中 → 读取各成分的 `IngredientAnalysis`，喂给 Agent，生成并存储新的 `ProductAnalysis`，`source: "agent_generated"`
- **失败**：Agent 调用失败 → `status: "failed", error: "analysis_failed"`

---

## 5. 错误处理

| 错误码 | 触发条件 | 前端展示 |
|--------|---------|---------|
| `ocr_failed` | PaddleOCR 无法处理图片 | "识别失败，请重新拍摄" |
| `no_ingredients_found` | OCR 文字中找不到配料表 | "未找到配料表，请对准配料表拍摄" |
| `analysis_failed` | Agent 调用失败 | "分析失败，请稍后重试" |

部分成分匹配不到（`unmatched`）不触发失败，正常返回结果，未知成分在结果页以 `level: "unknown"` 展示。

---

## 6. 设计决策记录

| 决策 | 结论 | 原因 |
|------|------|------|
| 接口与架构的关系 | 接口一体，架构分离 | 客户端不感知内部阶段；内部组件独立可替换 |
| 轮询 vs SSE | 短轮询（1.5s 间隔） | UniApp 微信小程序不支持 SSE；轮询对 10s 内任务完全够用 |
| 任务状态存储 | Redis | 临时状态无需持久化；快速读写；与 PostgreSQL 职责分离 |
| OCR 部署 | PaddleOCR-VL-1.5 独立服务 | 与主 FastAPI 解耦，可单独扩容或替换 |
| 成分匹配策略 | Embedding 检索 + 相似度阈值 | 处理 OCR 噪声和成分名变体；alias 字段无法穷举所有写法 |
| 客户端图片压缩 | 长边 ≤ 1024px | 足够 OCR 精度，减少传输体积和推理时间 |
| unmatched 成分降级 | level: "unknown" 占位，不中断管道 | 部分未知成分不应阻断整体分析 |
