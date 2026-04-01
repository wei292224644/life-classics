# 架构红线与白皮书

**版本**: v1.0
**归档日期**: 2026-04-01
**范围**: `server/` Python FastAPI 后端
**层级模型**: 4 层 + 1 基础设施

---

## 层级定义

| 层级 | 包名 | 职责 | 边界约束 |
|------|------|------|----------|
| **L1** | `api/` | HTTP 入口、路由、参数校验、响应序列化 | **禁止**执行业务逻辑、**禁止**直接操作 DB |
| **L2** | `services/` | 业务编排、跨 Repository 协调、事务边界 | **禁止**直接操作基础设施（ChromaDB/Redis），**禁止**管理 Session |
| **L3** | `db_repositories/` | 单表/单实体的 CRUD 操作 | **禁止**跨域查询、**禁止**业务判断 |
| **L4** | `database/` | ORM 模型、Session 工厂 | 仅定义结构，**禁止**业务逻辑 |
| **Infra** | `kb/`、`llm/`、`workflow_*/` | 外部依赖封装（ChromaDB、FTS、LLM、Workflow Engine） | 通过接口隔离，**禁止**被 L1 直接引用 |

---

## 一、禁忌 (Hard Taboos)

### T1. 禁止 API 层执行业务逻辑

```
❌ api/xxx/service.py 中的方法做：
   - 跨模块 Service 调用
   - Session 手动创建 (get_async_session_cm)
   - SQL/Hybrid 查询构造

✅ 正确：API Service 只做参数组装和委托
```

### T2. 禁止跨层逆向调用

```
❌ L2 Service 调用 L1 (api/*)
❌ L3 Repository 调用 L2 Service
❌ Infra 层被 L1 直接引用

✅ 允许的调用方向：L1 → L2 → L3 → L4
              L1/L2 → Infra（通过接口）
```

### T3. 禁止循环依赖

```
❌ api.a → api.b → api.a
❌ services.x → services.y → services.x
```

### T4. 禁止 Assembler/Serializer 访问 DB

```
❌ api/*/assembler.py 中执行 SQL 查询
✅ Assembler 只接收已查询的数据模型做序列化
```

### T5. 禁止 Session 在 Service 层自管理

```
❌ async with get_async_session_cm() as session: ...

✅ Session 由 Router 层通过 Depends 注入，Service 接收 Session 参数
```

---

## 二、最佳实践 (Golden Paths)

### G1. 请求生命周期

```
Request → Router (L1)
        → Service (L2, 接收 injected session)
        → Repository (L3, 接收 session)
        → DB (L4)
        ← Serializable Model ←
Response
```

### G2. Session 注入标准

```python
# Router
@router.post("/")
async def create_item(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    service: Annotated[MyService, Depends(get_my_service)],
):
    return await service.create(session, data)

# Service
class MyService:
    async def create(self, session: AsyncSession, data: DTO) -> Response:
        repo = MyRepo(session)  # Repository 接收 session
        entity = await repo.insert(data)
        return self._to_response(entity)
```

### G3. DTO 转换标准

```
Repository 返回 Entity (database/models.py)
Service 做 Entity → DTO 转换
Assembler 仅在需要聚合多个 Service 结果时使用（且不查 DB）
```

### G4. 跨模块调用规范

```
当 L2 Service 需要另一个 L2 Service 的能力时：
1. 若仅为数据查询 → 通过 Repository 层暴露
2. 若为业务编排 → 通过接口抽象（Protocol）解耦
3. 禁止直接 import 另一个 Service
```

### G5. 错误处理契约

```
Service 层抛出业务异常 (DomainError)
Router 层捕获并转换为 HTTP 响应
禁止在 Service 层直接 raise HTTPException
```

---

## 三、Workspaces 约束（包间引用权限矩阵）

| 从 → 到 | api/ | services/ | db_repositories/ | database/ | infra (kb/llm/workflow) |
|---------|------|-----------|-----------------|-----------|--------------------------|
| **api/** | 🔵 内部 | ✅ 可引用 | ❌ 禁止 | ❌ 禁止 | ❌ 禁止（通过 services） |
| **services/** | ❌ 禁止 | 🔵 内部 | ✅ 可引用 | ✅ 可引用 Model | ✅ 可引用（接口） |
| **db_repositories/** | ❌ 禁止 | ❌ 禁止 | 🔵 内部 | ✅ 可引用 Model | ❌ 禁止 |
| **database/** | ❌ 禁止 | ❌ 禁止 | ❌ 禁止 | 🔵 内部 | ❌ 禁止 |
| **infra/** | ❌ 禁止 | ✅ 可引用 | ❌ 禁止 | ❌ 禁止 | 🔵 内部 |

🔵 = 同包内自由引用

---

## 四、事务边界 (Transaction Boundary)

```
- 事务在 L1 (Router) 开启，在 L1 关闭
- L2/L3 禁止提交或回滚事务（只能操作）
- 所有 commit/rollback 必须显式且唯一地在 L1 层
```

---

## 五、数据模型所有权 (Data Model Ownership)

```
- database/models.py 中的 ORM Model → L4 所有，L1/L2 只能读取属性，禁止直接实例化
- DTO (api/*/models.py) → L1 所有，用于请求/响应序列化
- Domain Model / Entity → 若有，应在 L2 或独立 domain/ 包
```

---

## 六、错误传播契约 (Error Propagation Contract)

```
- L2 禁止抛出 HTTPException（那是 L1 的职责）
- L2 抛出业务异常，L1 负责转换为 HTTP 响应
- L3 禁止抛出任何异常类型（只能传播 L2 的异常）
- 禁止在 L1 之外的任何层级记录异常栈（异常应传播）
```

---

## 七、异步边界 (Async Boundary)

```
- L3 (db_repositories/) 所有方法必须是 async
- L2 调用 L3 时必须 await
- Infra 层（kb/llm/）接口须与 L2 异步对齐
- 禁止在 async 函数中直接调用同步基础设施（如 fts_writer 的某些方法）
```

---

## 八、配置访问权 (Configuration Access)

```
- 只有 L1 和 L2 可以读取 config
- L3 禁止直接 import config（配置值由 L2 传入）
- Infra 层通过接口接收配置，不直接读 .env
```

---

## 九、日志规范 (Logging Standards)

```
- L1 记录请求入口/出口日志（含 request_id）
- L2 记录业务操作日志（不记录 HTTP 上下文）
- L3 禁止记录日志（Repository 是纯数据操作）
- 禁止在 L1 之外的任何层级记录异常栈（异常应传播）
```

---

## 十、命名契约 (Naming Contract)

```
- Service 类名：XxxService
- Repository 类名：XxxRepository
- Assembler/Serializer 类名：XxxAssembler / XxxSerializer
- 禁止在 api/*/ 下创建与 db_repositories/* 同名的类
```
