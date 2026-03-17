# Spec 06：RulesStore.get_transform_params 查找逻辑变更

## 问题现象

`RulesStore.get_transform_params` 按 `content_type_id` 在旧 `content_types` 数组中查找 transform 策略。重构后 `content_types` 数组不再存在，该方法将对所有输入返回默认的 `plain_embed` 策略，transform 策略的差异化配置失效。

## 根因

当前实现：

```python
# rules.py
def get_transform_params(self, content_type_id: str) -> dict:
    for ct in self._ct.get("content_types", []):   ← 旧 key，重构后为空
        if ct["id"] == content_type_id:
            return ct.get("transform", self._PLAIN_EMBED_PARAMS)
    return self._PLAIN_EMBED_PARAMS                 ← 所有输入都走到这里
```

旧设计将 transform 策略**内嵌**在每个 content_type 条目中：

```json
{ "id": "table", "description": "...", "transform": { "strategy": "...", "prompt_template": "..." } }
```

新设计将 transform 策略**集中**到顶层 `transform.by_semantic_type` 字典，按 `semantic_type` 查找（因为 transform 策略取决于内容语义，而非结构形式）。

同时，`get_content_type_rules()` 返回整个 dict，其调用方（`classify_node.py`、`escalate_node.py`）读取其中的 `content_types` key，重构后均需调整。

## 发现方式

查看 `rules.py` 第 55-58 行：

```python
def get_transform_params(self, content_type_id: str) -> dict:
    for ct in self._ct.get("content_types", []):
```

再查看调用方：

```bash
grep -n "get_transform_params\|get_content_type_rules" app/core/parser_workflow/nodes/*.py
```

输出：
- `classify_node.py:70-71` — 读取 `content_types` key，用于构造 prompt 和查找 transform_params
- `escalate_node.py:68` — 读取 `content_types` key，传递给 LLM prompt

## 方案

### 1. 修改 `get_transform_params` 签名和查找逻辑

```python
# 修改前
def get_transform_params(self, content_type_id: str) -> dict:
    for ct in self._ct.get("content_types", []):
        if ct["id"] == content_type_id:
            return ct.get("transform", self._PLAIN_EMBED_PARAMS)
    return self._PLAIN_EMBED_PARAMS

# 修改后
def get_transform_params(self, semantic_type: str) -> dict:
    by_semantic = self._ct.get("transform", {}).get("by_semantic_type", {})
    return by_semantic.get(semantic_type, self._PLAIN_EMBED_PARAMS)
```

### 2. 新增两个 getter 方法，替代旧的 `content_types` 读取

```python
def get_structure_types(self) -> list:
    return self._ct.get("structure_types", [])

def get_semantic_types(self) -> list:
    return self._ct.get("semantic_types", [])
```

### 3. `append_content_type` 方法处理

旧的 `append_content_type` 用于 escalate_node 动态扩展类型。重构后 escalate_node 的处理方式见 Spec 07，本方法可暂时保留签名但内部逻辑待 Spec 07 确定后再更新。

## 依赖关系

- 前置：Spec 01（新 JSON 结构确定后，getter 方法才能确定 key 名）
- 后置：Spec 05（classify_node 需改用 `get_structure_types` / `get_semantic_types`）
- 后置：Spec 07（escalate_node 需改用新 getter）

## 受影响文件

- `app/core/parser_workflow/rules.py`（修改 `get_transform_params`，新增 `get_structure_types`、`get_semantic_types`）
