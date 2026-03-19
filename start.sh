#!/bin/bash
# 同时启动所有 dev 服务（server + web）

ROOT="$(cd "$(dirname "$0")" && pwd)"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

for cmd in uv pnpm; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}错误：未找到 $cmd，请先安装${NC}"
    exit 1
  fi
done

PIDS=()

cleanup() {
  echo ""
  echo -e "${BOLD}正在关闭服务...${NC}"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null
  done
  wait "${PIDS[@]}" 2>/dev/null
  echo -e "${BOLD}已关闭${NC}"
  exit 0
}

trap cleanup INT TERM

echo -e "${BOLD}🚀 启动 dev 服务...${NC}"
echo -e "  ${BLUE}[server]${NC}  http://localhost:9999"
echo -e "  ${GREEN}[web]${NC}     turbo dev (nextjs + console + packages)"
echo ""

cd "$ROOT/server"
uv run python3 run.py 2>&1 | sed "s/^/$(printf "${BLUE}[server]${NC} ")/" &
PIDS+=($!)

cd "$ROOT/web"
pnpm dev 2>&1 | sed "s/^/$(printf "${GREEN}[web]${NC}    ")/" &
PIDS+=($!)

wait "${PIDS[@]}"
