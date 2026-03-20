# start.sh tmux 分屏 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `start.sh` 改为使用 tmux 三分屏启动前后端服务，左 pane 为后端，右上为前端，右下为空闲 shell。

**Architecture:** 直接修改根目录 `start.sh`，移除原有的后台进程 + sed 前缀方案，替换为 tmux session 创建逻辑。无需新增文件。

**Tech Stack:** bash, tmux, uv, pnpm

---

### Task 1: 修改 start.sh

**Files:**
- Modify: `start.sh`

- [ ] **Step 1: 确认 tmux 已安装**

```bash
which tmux
```

预期输出：`/usr/bin/tmux` 或 `/opt/homebrew/bin/tmux`。若未安装，先执行 `brew install tmux`。

- [ ] **Step 2: 用新内容替换 start.sh**

将 `start.sh` 完整替换为以下内容：

```bash
#!/bin/bash
# 使用 tmux 三分屏启动所有 dev 服务（server + web）

ROOT="$(cd "$(dirname "$0")" && pwd)"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
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
echo -e "  ${BLUE}[server]${NC}  http://localhost:9999"
echo -e "  ${GREEN}[web]${NC}     turbo dev (nextjs + console + packages)"
echo ""

# 创建后台 session（左 pane = server）
tmux new-session -d -s "$SESSION" -x "$(tput cols)" -y "$(tput lines)"

# 向右分裂出右半区
tmux split-window -h -t "$SESSION"

# 将右半区纵向分裂（上 = web，下 = 空闲）
tmux split-window -v -t "${SESSION}:0.1"

# 向各 pane 发送命令
tmux send-keys -t "${SESSION}:0.0" "cd '$ROOT/server' && uv run python3 run.py" Enter
tmux send-keys -t "${SESSION}:0.1" "cd '$ROOT/web' && pnpm dev" Enter
tmux send-keys -t "${SESSION}:0.2" "cd '$ROOT'" Enter

# attach 时默认选中左侧 pane
tmux select-pane -t "${SESSION}:0.0"

# 进入 session
exec tmux attach -t "$SESSION"
```

- [ ] **Step 3: 验证脚本可执行**

```bash
chmod +x start.sh
bash -n start.sh
```

预期：`bash -n` 无输出无报错（语法检查通过）。

- [ ] **Step 4: 手动测试启动**

```bash
./start.sh
```

预期效果：
- 终端进入 tmux，呈现左右三分屏布局
- 左 pane 显示 server 日志（FastAPI 启动信息）
- 右上 pane 显示 turbo dev 输出
- 右下 pane 显示普通 shell 提示符，当前目录为项目根

- [ ] **Step 5: 验证 session 冲突检测**

不退出 tmux，新开一个终端窗口，再次执行：

```bash
./start.sh
```

预期输出：
```
错误：tmux session 'dev' 已存在
请先执行：tmux kill-session -t dev
```
然后脚本退出，不影响已有 session。

- [ ] **Step 6: 提交**

```bash
git add start.sh
git commit -m "feat(dev): replace start.sh with tmux 3-pane layout"
```
