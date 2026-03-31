#!/bin/bash
cd /Users/wwj/Desktop/self/life-classics/.worktrees/feature/product-analysis-pipeline/server
uv sync
uv run pytest tests/workflow_product_analysis/test_redis_store.py -v
