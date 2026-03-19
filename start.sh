#!/bin/bash
# 同时启动后端和前端服务

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "启动后端服务 (http://localhost:9999)..."
cd "$ROOT/agent-server"
uv run uvicorn app.main:app --host 0.0.0.0 --port 9999 --reload &
BACKEND_PID=$!

echo "启动 admin 前端服务 (http://localhost:5173)..."
cd "$ROOT/agent-server/admin"
pnpm dev &
FRONTEND_PID=$!

trap "echo '正在关闭服务...'; kill $BACKEND_PID $FRONTEND_PID; exit 0" INT TERM

wait $BACKEND_PID $FRONTEND_PID
