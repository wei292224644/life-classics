# Spec: 健康检查接口

## 背景

服务目前没有 `/health` 端点，运维和负载均衡器无法探测服务存活状态。

## 需求

为 FastAPI 应用新增 `GET /health` 端点，返回服务基本状态。

## 响应格式

```json
{
  "status": "ok",
  "service": "life-classics-api"
}
```

## 约束

- 不需要鉴权
- 响应时间需在 200ms 以内（无数据库查询）
- 端点注册在 `/health`（不在 `/api/` 前缀下）
