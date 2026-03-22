#!/bin/bash
tmux kill-session -t dev 2>/dev/null && echo "已关闭 dev session" || echo "没有正在运行的 dev session"
