#!/bin/bash
# 使用 tmux 三分屏启动所有 dev 服务（server + web）

ROOT="$(cd "$(dirname "$0")" && pwd)"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

SESSION="dev"

# 检查依赖
for cmd in tmux uv pnpm; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}错误：未找到 $cmd，请先安装${NC}"
    exit 1
  fi
done

# 检查 session 是否已存在
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo -e "${RED}错误：tmux session '$SESSION' 已存在${NC}"
  echo -e "请先执行：${BOLD}tmux kill-session -t $SESSION${NC}"
  exit 1
fi

echo -e "${BOLD}启动 dev 服务（tmux session: $SESSION）...${NC}"
echo -e "  ${BLUE}[server]${NC}   http://localhost:9999"
echo -e "  ${GREEN}[uniapp]${NC}  http://localhost:5173 (H5)"
echo -e "  ${CYAN}[console]${NC} 管理后台"
echo ""

# 创建后台 session（左 pane = server）
tmux new-session -d -s "$SESSION"

# 向右分裂出右半区
tmux split-window -h -t "$SESSION"

# 将右半区纵向分裂（上 = uniapp，下 = console）
tmux split-window -v -t "${SESSION}:0.1"

# 向各 pane 发送命令
tmux send-keys -t "${SESSION}:0.0" "cd '$ROOT/server' && uv run python3 run.py" Enter
tmux send-keys -t "${SESSION}:0.1" "cd '$ROOT/web/apps/uniapp' && pnpm dev:h5" Enter
tmux send-keys -t "${SESSION}:0.2" "cd '$ROOT/web/apps/console' && pnpm dev" Enter

# attach 时默认选中左侧 pane
tmux select-pane -t "${SESSION}:0.0"

# 进入 session
exec tmux attach -t "$SESSION"
