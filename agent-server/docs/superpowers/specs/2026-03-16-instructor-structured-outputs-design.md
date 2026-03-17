# Parser Workflow 引入 Instructor 结构化输出设计

**日期**：2026-03-16  
**状态**：设计已确认，待进入 implementation plan  
**范围**：`app/core/parser_workflow` 的四个结构化节点（`classify_node`、`escalate_node`、`transform_node`、`structure_node`）统一改造为基于 Instructor 的 Structured Outputs 调用。

---

## 1. 目标与边界

### 1.1 目标
- 引入 [Instructor](https://github.com/jxnl/instructor) 作为 parser_workflow 的结构化输出核心能力。
- 统一四个节点的结构化调用路径，消除分散的 provider 细节和解析策略。
- 在 `openai`、`dashscope`、`ollama` 三类 provider 下都提供稳定的 schema 约束输出。

### 1.2 关键约束（已确认）
- 覆盖范围：四个结构化节点全覆盖，不做局部试点。
- provider 范围：`openai + dashscope + ollama` 全支持。
- 失败策略：`fail-fast`，重试耗尽后直接抛错并终止当前流程，不做降级兜底。
- 集成方向：Instructor 为核心，LangChain 在 parser_workflow 的结构化输出角色逐步退出。

### 1.3 非目标
- 本次不改造 parser_workflow 外的其他业务模块。
- 本次不引入“失败后自动降级 unknown”策略。
- 本次不做 prompt 语义规则大改，仅做结构化输出链路重构。

---

## 2. 架构设计（方案A）

### 2.1 新增模块
在 `app/core/parser_workflow/` 下新增统一网关目录：

`structured_llm/`

- `client_factory.py`：按 provider 构建 Instructor 客户端
- `invoker.py`：统一执行结构化请求（response_model、重试、超时、参数注入）
- `errors.py`：定义统一异常 `StructuredOutputError`
- `types.py`：定义调用参数与通用类型（可选）

### 2.2 调用边界
- **节点职责**：构造 prompt、指定 `response_model`、显式传入 `node_name`、消费强类型结果。
- **网关职责**：provider 适配、重试控制、异常包装、日志上下文。
- **配置职责**：统一从 `settings` 读取，不在节点散落 provider 连接细节。

### 2.3 与现有 `llm.py` 的关系
- 迁移期允许 `llm.py` 与 `structured_llm` 并存。
- 四个结构化节点切换后，`llm.py` 中结构化输出能力逐步收敛或移除。
- 保留 `resolve_provider` 逻辑语义（node > global > openai），避免行为突变。

---

## 3. 数据流与错误传播

### 3.1 统一调用时序
四个节点统一采用：

1. 解析 provider（节点级覆盖优先）
2. 准备 prompt + `response_model`
3. 调用 `invoke_structured(..., node_name="classify_node|escalate_node|transform_node|structure_node")`
4. 成功返回 Pydantic 对象
5. 失败抛 `StructuredOutputError`

### 3.1.1 `node_name` 到配置映射
`invoke_structured` 接收 `node_name` 后，按以下映射解析 provider/model：

- `classify_node` → `CLASSIFY_LLM_PROVIDER` / `CLASSIFY_MODEL`
- `escalate_node` → `ESCALATE_LLM_PROVIDER` / `ESCALATE_MODEL`
- `transform_node` → `TRANSFORM_LLM_PROVIDER` / `TRANSFORM_MODEL`（为空则 fallback 到 `ESCALATE_MODEL`）
- `structure_node` → `DOC_TYPE_LLM_PROVIDER` / `DOC_TYPE_LLM_MODEL`

provider 解析优先级统一为：节点覆盖 > `PARSER_LLM_PROVIDER` > `"openai"`。

### 3.2 Fail-fast 策略
- 节点内不再执行 raw JSON 清洗或手工补救解析。
- `invoke_structured` 内进行有限重试（默认 2 次），仅对可恢复错误重试：
  - 网络抖动/连接错误
  - 请求超时
  - provider 侧 5xx 或限流等短暂错误
- 对不可恢复错误不重试，直接失败：
  - `response_model` 校验失败（Pydantic 验证错误）
  - 参数错误（如模型名为空、请求参数非法）
- 超过重试上限后统一抛错并上抛至 workflow 调用层。

### 3.3 错误上下文标准
`StructuredOutputError` 至少包含：
- `provider`
- `model`
- `node_name`
- `response_model`
- `retry_count`
- 原始异常摘要（截断）

该上下文用于快速判断是 provider 兼容问题、schema 过严、还是 prompt 质量问题。

### 3.4 Workflow 层异常约定
- `StructuredOutputError` 默认由 LangGraph 向上传播。
- `run_parser_workflow` 负责在最外层捕获并转换为统一错误输出（例如写入 `errors` 并终止返回），避免节点层吞错。

---

## 4. 配置设计

### 4.1 新增配置项（`app/core/config.py`）
- `PARSER_STRUCTURED_MAX_RETRIES: int = 2`
- `PARSER_STRUCTURED_TIMEOUT_SECONDS: int = 60`
- `PARSER_STRUCTURED_TEMPERATURE: float = 0.0`
- `PARSER_STRUCTURED_LOG_PROMPT_PREVIEW: bool = False`

### 4.2 保留并复用现有字段
- provider 选择：`PARSER_LLM_PROVIDER` + `CLASSIFY_LLM_PROVIDER`、`ESCALATE_LLM_PROVIDER`、`TRANSFORM_LLM_PROVIDER`、`DOC_TYPE_LLM_PROVIDER`
- 模型字段：`CLASSIFY_MODEL`、`ESCALATE_MODEL`、`TRANSFORM_MODEL`、`DOC_TYPE_LLM_MODEL`
- `TRANSFORM_MODEL` 为空时沿用现有语义：fallback 到 `ESCALATE_MODEL`，由 invoker 在调用前统一解析。

### 4.3 Provider 适配约定
- `openai`：`LLM_API_KEY` + `LLM_BASE_URL`
- `dashscope`：`DASHSCOPE_API_KEY` + `DASHSCOPE_BASE_URL`（OpenAI-compatible）
  - 不依赖 Instructor 原生 provider 名称，统一通过 OpenAI-compatible client 接入（`base_url` 指向 DashScope 兼容端点）。
- `ollama`：`OLLAMA_BASE_URL`（本地 OpenAI-compatible 端点）

### 4.4 Provider 特殊参数注入（保持现有稳定性语义）
- `dashscope`：默认注入 `extra_body={"enable_thinking": False}`，避免 thinking 模式干扰结构化输出。
- `ollama`：默认注入 `reasoning=False`，并维持低温度（默认 `temperature=0.0`）以提升 schema 稳定性。
- `openai`：无额外特殊参数，使用统一 temperature/timeout/retry 策略。

---

## 5. 测试与验收

### 5.1 测试调整
- 新增 `tests/core/parser_workflow/test_structured_llm.py`：
  - client_factory 路径覆盖
  - response_model 绑定验证
  - 重试耗尽后异常验证
  - 异常上下文字段验证
  - 不可恢复错误（如 Pydantic 校验失败）直接抛错且不重试验证
- 改造 `test_llm.py`：
  - 保留 `resolve_provider` 相关测试（行为不变）
  - 移除/迁移 `with_structured_output` 相关断言到 `test_structured_llm.py`
- 改造 `test_classify_node_fallback.py`：由“fallback 成功”改为“解析失败即抛统一异常”。

### 5.2 集成测试范围
针对 `classify/escalate/transform/structure`：
- 成功路径：返回强类型对象并完成节点输出。
- 失败路径：不吞异常，统一上抛。
- 明确更新现有节点测试中的 mock 目标：由 `create_chat_model` 迁移为 `invoke_structured`。
- `structure_node` 需覆盖“规则命中不调 LLM / 规则未命中才调 LLM”两条路径，且 LLM 失败时保持 fail-fast。
- 现有 real-llm 测试（`test_classify_node_real_llm.py`、`test_escalate_node_real_llm.py`、`test_transform_node_real_llm.py`、`test_structure_node_real_llm.py`）保留，但去除 fallback 预期并打 marker 分层执行。

### 5.3 验收标准（Definition of Done）
- 四个结构化节点全部通过 Instructor 网关调用。
- 节点内 raw JSON fallback 逻辑全部移除。
- 失败路径全部 `fail-fast`，抛 `StructuredOutputError`。
- 单测/集成测试通过，real-llm 测试按 marker 独立执行。
- 文档更新完成并可指导后续实现。

---

## 6. 迁移与回滚

### 6.1 迁移步骤
**阶段1：并行接入**
- 引入 `instructor` 依赖与 `structured_llm` 模块。
- 节点完成可切换接入，保留过渡兼容能力。
- 跑通测试，确认功能等价。

**阶段2：主路径切换**
- 四节点默认切到 Instructor。
- 删除节点内 fallback/raw JSON 清洗路径。
- 收敛旧结构化调用代码与文档说明。

### 6.2 回滚策略
- 发现异常升高时，回退到切换前提交。
- 或临时切回兼容路径（若阶段1保留开关）。
- 保留结构化失败日志上下文用于定位。

---

## 7. 风险与缓解

- **provider 行为差异**：通过 `client_factory` 层做参数隔离与统一封装。
- **严格 schema 导致失败率上升**：靠有限重试与 prompt 校正缓解；不牺牲 fail-fast 原则。
- **迁移期测试波动**：单测与 real-llm 测试分层执行，避免混跑误判。

---

## 8. 里程碑

- **M1**：`structured_llm` 模块与单元测试落地
- **M2**：四节点全接入 Instructor
- **M3**：旧 fallback 清理 + 文档与测试基线更新

---

## 9. 参考

- Instructor 项目：<https://github.com/jxnl/instructor>
