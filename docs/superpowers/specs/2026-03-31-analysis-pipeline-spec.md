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

### 2.5 对外 `status` 与内部四组件的边界

对外枚举只有三步「进行中」+ 终态，内部有四段流水线。**约定如下（实现必须遵守，避免 Stepper 与真实耗时错位）：**

| 对外 `status` | 覆盖的内部阶段 | 进入下一 `status` 的判据 |
|---------------|----------------|-------------------------|
| `ocr` | 仅组件 1（OCR） | 已得到原始 OCR 文本（或失败 → `failed`） |
| `parsing` | 仅组件 2（解析 / LLM 抽成分名） | **成分名列表已就绪**（非空；或失败 → `no_ingredients_found`） |
| `analyzing` | 组件 3（Embedding 匹配）+ 组件 4（产品缓存命中检查 + Agent 生成） | 已得到完整 `ProductAnalysis`（或失败 → `analysis_failed`） |

**含义：**

- **「解析成分」**（Stepper 第 2 步）在用户感知上对应 **拿到结构化成分名列表**，不包含向量检索耗时。
- **「生成评估报告」**（Stepper 第 3 步）对应 **从匹配配料库到产出可展示的产品分析**（含缓存直出、未命中时拉 `IngredientAnalysis` + Agent、落库或组装响应）。

观测与日志可在 Redis 或内部 metrics 中增加子阶段标签（如 `match`、`cache_lookup`、`agent`），**不新增对外 `status` 枚举**，除非产品明确要求第四档进度。

### 2.6 从图像到 `food_id`（MVP）

`product_analyses` 按 `food_id` 做缓存键（见 [Product Analysis Data Schema Design](./2026-03-31-product-analysis-schema-design.md)）。照片本身不自带主键，**必须在管道内解析出或传入 `food_id`**。MVP 约定如下：

1. **可选请求参数 `food_id`**  
   - `POST /api/analysis/start` 的 `multipart/form-data` 可增加可选字段 `food_id`（整数，与 `foods.id` 一致）。  
   - 若客户端已选品（列表进详情再拍配料表、或扫码后进入拍照页），**必须传入**，Component 4 **优先**按该 `food_id` 查 `product_analyses`，产品相似度匹配可作为校验或省略（实现选型在实现计划中写死）。  
   - 若传入但 DB 中不存在该 `food_id` → `failed`，`error` 建议扩展为 `invalid_food_id`（或在实现阶段归入 `analysis_failed` 并在文档中统一）。

2. **未传 `food_id` 时的默认策略**  
   - 在组件 2（或与解析同一次 LLM 调用）中，从 OCR 文本尝试抽取 **商品品名**（一行即可）。  
   - 在 `foods` 表上做 **模糊匹配**（规则或 embedding，实现待定）：**唯一候选且置信度 ≥ 阈值** → 采用该 `food_id`。  
   - 否则：**创建占位 `food` 记录**（例如 `name` = 抽取名或「未命名产品」，来源标记为 `photo_import` 等），分配新 `food_id`，再进入后续匹配与 `product_analyses` 读写。避免阻塞用户得到结果；后续运营可合并重复占位产品。

3. **后续迭代（非 MVP 必选）**  
   - 与 `/api/product` 条码联动：扫码得到产品后再 `POST /start` 带 `food_id`。  
   - 纯拍照无条码场景仍适用第 2 条。

**与 schema 文档的交叉引用：** 占位 `food` 的字段与唯一性约束在数据模型迁移中单独说明；本管道 spec 只要求 **每条成功完成的分析任务在逻辑上绑定唯一 `food_id`**。

### 2.7 用户上传图像的持久化留存

境内缺乏统一、可机读的权威配料数据源，产品依赖真实包装图迭代 OCR/解析/匹配能力；同时留存可用于复盘与后续重跑管道。**与 Redis 任务状态（§3，终态后约 1 小时 TTL）分离：对象为长期存储，不是任务缓存。**

**行为约定：**

- **触发时机**：`POST /api/analysis/start` 在校验通过（格式、大小）后，将本次 `image` **异步写入对象存储**（如 OSS / S3 / MinIO；具体选型在实现计划中确定）。  
- **不得阻塞主流程**：存储失败应记日志与指标，**默认仍继续** OCR → 解析 → …（若产品日后要求「无落盘则拒绝分析」，需单独变更本 spec）。  
- **键名建议**：`analysis_uploads/{yyyy}/{mm}/{task_id}.{ext}`；若已鉴权，可前缀 `user_id` 便于合规删除与审计。  
- **与任务关联**：Redis 任务 JSON 可增加可选字段 `image_object_key`（或仅 DB 侧 `analysis_tasks` 表记录 `task_id ↔ storage_key`），便于报错接口与运营溯源。  
- **留存周期**：可配置（如默认 365 天，TBD），到期生命周期删除；须在隐私政策中写明**目的**（改进服务、安全与争议处理等）、**保存期限**与用户权利。  
- **最小化与合规**：对外文案由法务/产品确认；技术上可仅存客户端已压缩图以降低体积；传输 HTTPS、存储侧加密、访问控制按公司基线执行。

**说明：** 持久化图像是**资源与合规设计**，不改变 §2.5 各 `status` 含义，也不替代 `ProductAnalysis` 的权威展示逻辑。

### 2.8 用户人工报错（反馈）接口

用户可对「识别错、结论不合理、有害内容」等提交反馈。**本接口为旁路能力，不参与、不修改、不重跑** `POST /start` → 轮询 → `ProductAnalysis` 的主流程。

```
POST /api/analysis/feedback
Content-Type: application/json
```

**请求体（示例字段，实现时可微调）：**

```json
{
  "task_id": "uuid-v4 | null",
  "food_id": 123,
  "category": "ocr_wrong" | "verdict_wrong" | "ingredient_wrong" | "other",
  "message": "用户补充说明，可选",
  "client_context": { "app_version": "1.0.0", "platform": "weapp" }
}
```

- `task_id`：若从分析结果页进入，建议带上，便于与留存图像、日志关联。  
- `category`：枚举可扩展，以产品为准。  
- **禁止**：根据本条请求**回写** `product_analyses`、**修改** Redis 中已有任务状态、**自动触发**重新分析或降级模型；后续是否人工处理、是否建工单，由运营/数据流程单独决定。  
- **实现形态**：写入**仅追加**表或异步队列即可；需限流与鉴权，防刷。

### 2.9 未来迭代：分析结果反哺 FoodDetail（非本版范围）

**产品与研发共识：** 后台**最终会**依托分析链路，把可沉淀的结论与数据**反哺到 FoodDetail（商品详情）**，用于丰富展示与**自动化纠错**（例如占位 `food` 合并、配料/别名校正、高频反馈与多任务聚合驱动的规则或配料库更新等）。  

- **不要求与单次 `POST /start` 同步**：可采用异步任务队列、定时批处理、或「人工/策略闸门通过后再写主档」；核心是**先完成分析、可追溯**（`task_id`、`food_id`、存图、`ProductAnalysis`），再谈写回。  
- **本版（MVP）不包含**：不实现自动回写 `foods` 等主数据、不把未审核照片作为详情页**权威**主图/主文案；详情页仍以 **`ProductAnalysis` + `food_id` 的读模型**为主（与 §2.7「存图为底层资产」一致）。  
- **与「我的拍摄记录」**：若产品单独要做用户维度的拍摄历史展示，另立能力与权限模型，不与本条「后台反哺主档」混为一谈。

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
| 对外 `status` 与四组件 | `parsing` = 仅解析；`analyzing` = 匹配 + 分析 | Stepper 第 2 步对齐「成分列表就绪」；第 3 步对齐「匹配到报告」 |
| `food_id` 来源（MVP） | 可选参数优先；否则 OCR 品名匹配或占位 `food` | 缓存键必须存在；不强制用户先有条码 |
| 上传图持久化 | `start` 后异步写入对象存储，与 Redis TTL 分离 | 支撑模型与规则迭代、复盘；默认不阻塞分析管道 |
| 用户报错接口 | `POST /api/analysis/feedback`，旁路仅追加 | 人工反馈不修改分析结果与管道状态，不影响现有流程 |
| 反哺 FoodDetail | 未来异步/批处理，依赖分析沉淀；MVP 不做自动写主档 | 自动化纠错与主数据治理在后续版本；当前以读侧挂载分析为主 |
