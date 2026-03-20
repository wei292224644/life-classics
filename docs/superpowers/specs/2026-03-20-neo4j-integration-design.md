# Neo4j GB2760 知识图谱集成设计

**日期：** 2026-03-20
**状态：** 已确认
**范围：** 仅实现查询层（不含数据导入）

---

## 背景

`server/agent/tools/neo4j_query.py` 目前是占位符，调用后直接返回 "not implemented"。
`pdf_test` 项目已将 GB2760_2024 食品添加剂国标数据完整导入 Neo4j（节点、关系、向量索引均就绪）。
本次集成目标：补全查询工具，让 Agent 能通过自然语言查询 GB2760_2024 知识图谱。

---

## 架构

### 文件变更（仅 3 处）

```
server/
├── agent/
│   ├── tools/
│   │   └── neo4j_query.py          ← 补全实现
│   └── skills/
│       └── neo4j_gb2760.md         ← 新建 skill 文件
└── config.py                       ← 新增 NEO4J_DATABASE 字段
```

`factory.py` 无需修改——`neo4j_query` 已注册在默认工具列表，skill 注入机制已存在。

### 数据流

```
用户问题
  → Agent 读取 neo4j_gb2760.md（system prompt 中的 skill）
  → Agent 根据 schema 速查表和模板构建 Cypher
  → 调用 neo4j_query(cypher)
  → neo4j driver 在只读事务中执行（连接 gb2760_2024 database）
  → 返回 JSON 结果（最多 50 条）
  → Agent 组织自然语言回答
```

---

## 组件设计

### 1. `neo4j_query.py`

**函数签名：**
```python
@tool
def neo4j_query(cypher: str) -> str:
    """对 GB2760_2024 知识图谱执行只读 Cypher 查询，返回 JSON 结果"""
```

**约束：**
- **只读事务**：使用 `session.execute_read()`，从驱动层拒绝写操作
- **结果截断**：若 Cypher 中未包含 `LIMIT`，自动追加 `LIMIT 50`
- **超时**：driver 层设置 10 秒 query timeout
- **连接复用**：driver 实例使用模块级懒初始化单例，避免每次调用重建连接

**返回格式（JSON 字符串）：**
```json
{
  "columns": ["name_zh", "max_usage", "unit"],
  "rows": [["山梨酸", "1.0", "g/kg"]],
  "count": 1
}
```

**错误处理：**
- 连接失败 → 返回可读错误字符串（不抛异常，让 Agent 能理解并告知用户）
- Cypher 语法错误 → 将 Neo4j 原始报错返回给 Agent，让其自行修正并重试

### 2. `neo4j_gb2760.md` Skill 文件

文件分 4 块，总长控制在 150 行以内：

**块 1：何时使用**
声明在查询食品添加剂限量、功能分类、食品分类层级、香料许可、加工助剂、酶制剂时调用此工具。

**块 2：节点速查表**
列出全部 9 种节点类型及其关键属性（紧凑格式）：
- `Chemical`：`id`, `name_zh`, `name_en`
- `AdditiveCode`：`code`, `code_type`（CNS/INS）
- `Function`：`name`
- `FoodCategory`：`code`, `name`, `level`
- `FoodCategoryGroup`：`code`, `name`, `description`
- `Flavoring`：`code`, `name_zh`, `name_en`, `flavoring_type`
- `ProcessingAid`：`code`, `name_zh`, `type`, `function`, `usage_scope`
- `Enzyme`：`code`, `name_zh`, `name_en`
- `Organism`：`name_zh`, `name_en`

**块 3：关系速查表**

| 关系 | 方向 | 关键属性 |
|------|------|---------|
| `REFERS_TO` | AdditiveCode → Chemical | — |
| `HAS_FUNCTION` | Chemical → Function | — |
| `PERMITTED_IN` | Chemical/Flavoring → FoodCategory | `max_usage`, `unit`, `note` |
| `PERMITTED_IN_GROUP` | Chemical → FoodCategoryGroup | `max_usage`, `exclude_group` |
| `CONTAINS` | FoodCategoryGroup → FoodCategory | — |
| `HAS_SUBCATEGORY` | FoodCategory → FoodCategory | — |
| `HAS_SOURCE` | Enzyme → EnzymeSource | — |
| `FROM_ORGANISM` / `USES_DONOR` | EnzymeSource → Organism | — |

**块 4：查询模板（5 个）**
1. 查某添加剂在某食品分类下的限量
2. 查某添加剂的所有功能
3. 查某食品分类下允许使用的所有添加剂（带限量）
4. 查某香料是否允许用于某食品
5. 查食品分类的层级结构（父子关系）

### 3. `config.py` 变更

新增字段：
```python
NEO4J_DATABASE: str = "gb2760_2024"
```

### 4. 依赖

`pyproject.toml` 新增：
```
neo4j>=5.0
```

---

## 测试策略

文件：`server/tests/core/test_neo4j_query.py`

**单元测试（mock driver，无需真实 Neo4j）：**
- `test_readonly_transaction`：验证使用 `execute_read` 而非 `execute_write`
- `test_limit_injection`：无 LIMIT 时自动追加，有 LIMIT 时不覆盖
- `test_connection_error_returns_string`：连接失败返回字符串而非抛异常
- `test_cypher_error_returns_string`：语法错误返回原始报错字符串
- `test_result_json_format`：验证返回 JSON 格式正确

**集成测试（标记 `@pytest.mark.integration`，默认跳过）：**
- 需要真实 Neo4j 实例，验证端到端查询 gb2760_2024 database

---

## 不在本次范围内

- 数据导入（由 `pdf_test` 手动执行）
- 多数据库支持（gb2760_2014 等）
- Text→Cypher 自动转换工具
- Neo4j 向量相似度查询
