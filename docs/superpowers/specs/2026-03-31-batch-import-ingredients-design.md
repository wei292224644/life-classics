# 批量配料导入脚本 — 设计规格

## 概述

读取指定文件夹中的所有 `.json` 文件，解析出配料数据，通过 `POST /api/ingredients` 接口逐条写入数据库。遇到重复（409）或任何错误时**立即中止**，打印详细报告。

## 输入规格

### JSON 文件格式

每个 `.json` 文件包含单个配料对象或配料对象数组：

```json
{
  "name": "(+/-)-1-环己基乙醇",
  "alias": ["1-环己基乙醇", "α-环己基乙醇"],
  "english_name": "1-Cyclohexylethanol",
  "description": "...",
  "is_additive": true,
  "additive_code": "S1502",
  "standard_code": null,
  "who_level": "Unknown",
  "allergen_info": [],
  "function_type": ["香料"],
  "origin_type": "合成",
  "limit_usage": null,
  "legal_region": "中国",
  "cas": "1193-81-3",
  "applications": "...",
  "notes": "...",
  "safety_info": "...",
  "natural_source": null,
  "molecular_formula": "C8H16O",
  "meta": { "cns_codes": ["S1502"] },
  "path": "https://..."
}
```

**类型兼容：** `alias` 字段可能为数组 `["A", "B"]` 或字符串 `"A"`。解析时统一做规范化，脚本本身不提交 alias。

### 字段映射

| JSON 字段 | 接口字段 | 说明 |
|---|---|---|
| `name` | `name` | 必需 |
| `description` | `description` | |
| `is_additive` | `is_additive` | |
| `additive_code` | `additive_code` | |
| `standard_code` | `standard_code` | |
| `who_level` | `who_level` | |
| `allergen_info` | `allergen_info` | |
| `function_type` | `function_type` | |
| `origin_type` | `origin_type` | |
| `limit_usage` | `limit_usage` | |
| `legal_region` | `legal_region` | |
| `cas` | `cas` | |
| `applications` | `applications` | |
| `notes` | `notes` | |
| `safety_info` | `safety_info` | |

### 忽略字段

以下字段存在但本脚本不处理：`alias`（走独立接口）、`path`、`english_name`、`molecular_formula`、`natural_source`、`meta`。

## 处理流程

1. 接收文件夹路径参数
2. 递归查找所有 `.json` 文件
3. 逐文件解析 JSON（单个对象 → 包装为数组；数组 → 展开）
4. 逐条构造请求体并调用 `POST /api/ingredients`
5. 实时打印每条记录的处理结果
6. 遇 409 或其他错误立即中止

## 去重策略

调用接口后若返回 HTTP 409 Conflict，立即中止整次导入，不继续处理后续记录。

## 错误处理

- **409 Conflict**：立即中止
- **其他 HTTP 错误**：立即中止
- **JSON 解析错误**：记录文件名和行号，中止
- **文件读写错误**：中止

## 报告输出

脚本结束后打印：

```
=== 批量导入报告 ===
总计：N 条
成功：X 条
失败：Y 条
中止原因：Z（若适用）

--- 逐条详情 ---
[1/3] ✅ "配料名称A" → 导入成功
[2/3] ❌ "配料名称B" → 409 Conflict（已存在）
[3/3] 未执行（已中止）
```

## 依赖

- `httpx.AsyncClient`（HTTP 请求）
- 标准库：`pathlib`、`json`、`argparse`、`sys`

## 并发

单线程逐条顺序请求，不并发，以保证错误中止的有效性。
