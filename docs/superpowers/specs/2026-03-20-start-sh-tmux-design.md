# start.sh tmux 分屏设计

**日期：** 2026-03-20
**状态：** 已批准

## 背景

原 `start.sh` 将前端（turbo watch dev）与后端（uv run python3 run.py）输出通过 sed 前缀混流到同一终端，turborepo 产生大量日志，与后端日志相互干扰，难以阅读。

## 目标

将前后端输出分离到 tmux 独立 pane，互不干扰。

## 布局

```
+------------------+------------------+
|                  |   [web]          |
|   [server]       |   pnpm dev       |
|   uv run run.py  +------------------+
|                  |   (空闲 shell)   |
+------------------+------------------+
```

- **左 pane（pane 0）**：后端服务 `uv run python3 run.py`
- **右上 pane（pane 1）**：前端服务 `pnpm dev`
- **右下 pane（pane 2）**：空闲 shell，供手动操作

## 行为规格

### 启动流程

1. 检查依赖：`tmux`、`uv`、`pnpm` 均需存在，缺失则打印错误退出
2. 检查 session：若 tmux session `dev` 已存在，打印错误并提示用户执行 `tmux kill-session -t dev`，然后退出（不自动 kill）
3. 后台创建 tmux session `dev`：
   - pane 0（左）：`cd $ROOT/server && uv run python3 run.py`
   - pane 1（右上）：`cd $ROOT/web && pnpm dev`
   - pane 2（右下）：`cd $ROOT`，空闲 shell
4. 执行 `tmux attach -t dev`，用户直接进入分屏界面

### Cleanup

- 各 pane 内 Ctrl-C 独立终止对应进程，由 tmux 自然处理
- 移除原有的 `PIDS` 数组、`cleanup()` 函数和 `trap` 逻辑

## 不在范围内

- 自动 kill 已有 session
- 日志持久化到文件
- turborepo 日志过滤
