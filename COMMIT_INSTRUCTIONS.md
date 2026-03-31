# Final Commit Instructions

## Step 1: Install Dependencies and Run Tests

Execute from `/Users/wwj/Desktop/self/life-classics/.worktrees/feature/product-analysis-pipeline/server`:

```bash
cd server
uv sync
uv run pytest tests/workflow_product_analysis/test_redis_store.py -v
```

Expected result: All 6 tests passing

## Step 2: Stage Files

Execute from `/Users/wwj/Desktop/self/life-classics/.worktrees/feature/product-analysis-pipeline`:

```bash
git add server/workflow_product_analysis/redis_store.py
git add server/tests/workflow_product_analysis/__init__.py
git add server/tests/workflow_product_analysis/test_redis_store.py
git add server/pyproject.toml
```

If you ran `uv sync`, also add:
```bash
git add server/uv.lock
```

## Step 3: Create Commit

```bash
git commit -m "feat(analysis): add Redis task state store

- Implement redis_store module for managing product analysis task lifecycle
- Add create_task, get_task, update_task_status, set_task_done, set_task_failed
- Implement get_redis_client for FastAPI dependency injection
- Add comprehensive test suite using fakeredis for mocking
- Update asyncio_mode to 'auto' in pytest configuration
- Add redis>=5.0.0 and fakeredis>=2.19.0 dependencies

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## Implementation Details

### Files Created:
- `server/workflow_product_analysis/redis_store.py` (84 lines)
  - _task_key() - Helper function
  - create_task() - Initialize task with status="ocr"
  - get_task() - Read task from Redis
  - update_task_status() - Update status field only
  - set_task_done() - Set to done state with TTL
  - set_task_failed() - Set to failed state with TTL
  - get_redis_client() - FastAPI dependency

- `server/tests/workflow_product_analysis/__init__.py` (empty)

- `server/tests/workflow_product_analysis/test_redis_store.py` (67 lines)
  - 6 async test functions using fakeredis
  - Test fixtures for Redis mock

### Files Modified:
- `server/pyproject.toml`
  - Added "redis>=5.0.0" to dependencies
  - Added "fakeredis>=2.19.0" to dev dependencies
  - Changed asyncio_mode from "strict" to "auto"

## Verification Checklist

- [ ] All 6 tests pass
- [ ] No import errors
- [ ] All functions have proper type hints
- [ ] Redis configuration uses settings.REDIS_URL
- [ ] FakeRedis fixture properly closes connections
- [ ] pytest-asyncio is configured correctly

## Notes

1. The redis_store module uses JSON serialization for easy debugging and protocol compliance
2. TTL is only set on terminal states (done/failed), not on intermediate states
3. All operations are async-compatible for FastAPI integration
4. Type safety is maintained through TypedDict throughout
5. The implementation follows the existing codebase patterns
