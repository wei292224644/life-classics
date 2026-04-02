# Plan: 健康检查接口

## T1：新增 GET /health 端点

- workspace: server
- 依赖: none
- 规模: 小（单文件改动，无新接口依赖）
- 描述: 在 `server/api/main.py` 新增 `GET /health` 路由，返回 `{"status": "ok", "service": "life-classics-api"}`
- 验收标准: 启动服务后，`curl http://localhost:9999/health` 返回 HTTP 200，body 为 `{"status":"ok","service":"life-classics-api"}`
