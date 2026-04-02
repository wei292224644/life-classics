# Handoff: T1

## 版本
v1

## 完成情况
- [x] 在 `server/api/main.py` 新增 `GET /health` 路由，返回 `{"status": "ok", "service": "life-classics-api"}`，挂载在根路径（非 /api/ 前缀）

## 做了什么 / 没做什么
在 `/swagger` 路由定义前插入了 `/health` 端点，挂载于根路径。

## 已知问题
无

## 修改的文件
- `server/api/main.py`: 新增 `GET /health` 路由，返回 `{"status": "ok", "service": "life-classics-api"}`

## 验证命令
```bash
cd server
uv run uvicorn api.main:app --host 0.0.0.0 --port 9999 &
curl http://localhost:9999/health
# 预期输出: {"status":"ok","service":"life-classics-api"}
```
