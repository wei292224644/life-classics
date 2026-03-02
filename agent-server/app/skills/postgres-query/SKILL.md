---
name: postgres-query
description: 用于查询 PostgreSQL 中存储的结构化业务数据。仅当用户明确需要查询数据库中的表格数据时使用。
allowed-tools: postgres_query
---

# PostgreSQL 查询

## 概述

本技能用于执行只读 SQL 查询，获取 PostgreSQL 中的业务数据。需确保查询为只读，且使用参数化防止注入。

## 使用步骤

1. **确认数据需求**：判断用户问题是否涉及数据库中的结构化数据。
2. **调用 postgres_query 工具**：传入自然语言或结构化查询请求，工具内部负责生成安全 SQL 并执行。
3. **格式化结果**：将查询结果整理为表格或列表形式呈现给用户。
