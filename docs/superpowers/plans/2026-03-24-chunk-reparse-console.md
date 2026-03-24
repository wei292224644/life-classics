# Chunk 列表重解析按钮 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在控制台 Chunk 列表为每条记录提供“重解析”按钮，调用 `POST /api/chunks/{chunk_id}/reparse`，并在处理中禁止该条编辑、完成后刷新列表并反馈结果。

**Architecture:** 在 `api/client.ts` 增加 `chunks.reparse` API；在 `ChunkList` 维护 `reparsingIds`（按 chunk_id 追踪处理中状态），并把状态/事件透传到 `ChunkCard` 负责展示。成功后重拉当前页并根据返回集判断“该条是否因筛选不可见”；失败走统一错误兜底，不改动 `ChunkEditDrawer` 的既有保存流程。

**Tech Stack:** React 19 + TypeScript + Vite + shadcn/ui + fetch API（现有 `request<T>` 封装）

---

## Execution Rules

- Node 命令统一在仓库 `web/` 目录执行（`cd web && pnpm ...`）。
- Git 命令统一在仓库根目录执行（不要在子目录执行 `git add/commit`）。
- 每个 Task 提交前需再次确认 `cd web && pnpm --filter @acme/console build` 可通过，并且仅 stage 本 Task 相关文件。

---

## File Structure

- Modify: `web/apps/console/src/api/client.ts`
  - 增加 `api.chunks.reparse(chunk_id)`，统一走现有 `request<T>`。
- Modify: `web/apps/console/src/components/ChunkCard.tsx`
  - 增加 `重解析` 按钮与处理中禁用态展示。
- Modify: `web/apps/console/src/components/ChunkList.tsx`
  - 增加 `reparsingIds` 状态与 `handleReparse` 业务逻辑；
  - 透传 `isReparsing/onReparse` 给 `ChunkCard`；
  - 处理成功/失败 toast、刷新与“当前筛选下不可见”提示。
- Optional Test: `web/apps/console/src/components/__tests__/ChunkList.reparse.test.tsx`
  - 若现有测试基础可快速接入，补最小行为测试；若成本过高，保留手测用例。
- Doc Reference: `docs/superpowers/specs/2026-03-24-chunk-reparse-console-design.md`

---

### Task 1: API Client 增加重解析接口

**Files:**
- Modify: `web/apps/console/src/api/client.ts`
- Test: `web/apps/console/src/api/client.ts`（类型检查 + 构建验证）

- [ ] **Step 1: 写一个最小失败验证（调用点预检查）**

Run: `rg "chunks:\\s*\\{" "web/apps/console/src/api/client.ts"`
Expected: 仅存在 `list/update`，无 `reparse`。

- [ ] **Step 2: 增加 `reparse` 方法（最小实现）**

实现：
- 在 `api.chunks` 下新增：
  - `reparse: (chunk_id: string) => request<Chunk>(\`/chunks/${chunk_id}/reparse\`, { method: 'POST' })`

- [ ] **Step 3: 运行构建验证 API 层改动**

Run: `cd web && pnpm --filter @acme/console build`
Expected: PASS，无 TypeScript 错误。

- [ ] **Step 4: Commit**

```bash
git add web/apps/console/src/api/client.ts
git commit -m "feat(console): add chunk reparse api client"
```

---

### Task 2: 列表项增加重解析按钮与禁用态

**Files:**
- Modify: `web/apps/console/src/components/ChunkCard.tsx`
- Test: `web/apps/console/src/components/ChunkCard.tsx`（UI 构建校验）

- [ ] **Step 1: 失败验证（确认当前无重解析入口）**

Run: `rg "重解析|reparse" "web/apps/console/src/components/ChunkCard.tsx"`
Expected: 无匹配。

- [ ] **Step 2: 扩展 `ChunkCard` Props 并渲染按钮**

实现：
- 新增 props：
  - `isReparsing: boolean`
  - `onReparse: () => void`
- 增加 `重解析` 按钮；
- `isReparsing=true` 时：
  - 重解析按钮文案显示 `重解析中...`；
  - `编辑` 与 `重解析` 均 `disabled`。

- [ ] **Step 3: 运行构建验证组件改动**

Run: `cd web && pnpm --filter @acme/console build`
Expected: PASS，无 props 类型报错。

- [ ] **Step 4: Commit**

```bash
git add web/apps/console/src/components/ChunkCard.tsx
git commit -m "feat(console): add reparse action in chunk card"
```

---

### Task 3: ChunkList 接入重解析状态机与刷新逻辑

**Files:**
- Modify: `web/apps/console/src/components/ChunkList.tsx`
- Test: `web/apps/console/src/components/ChunkList.tsx`（行为验证 + 构建）

- [ ] **Step 1: 写失败验证（当前无重解析状态）**

Run: `rg "reparsingIds|handleReparse|onReparse|isReparsing" "web/apps/console/src/components/ChunkList.tsx"`
Expected: 无匹配。

- [ ] **Step 2: 增加 toast、处理中状态与不可变 Set 更新**

实现：
- 引入 `useToast`；
- 新增状态：
  - `const [reparsingIds, setReparsingIds] = useState<Set<string>>(new Set())`
- 约束：只用不可变更新（新建 `Set`），禁止原地修改。

- [ ] **Step 3: 实现 `handleReparse(chunkId)`**

逻辑：
1. 若已在处理中，直接 return；
2. 加入 `reparsingIds`；
3. 调用 `api.chunks.reparse(chunkId)`；
4. 调用 `loadAndReturn()` 重拉当前页并拿到最新 `res.chunks`（不要依赖 state 立即更新）；
5. 判断 `res.chunks` 中是否还存在该 `chunkId`：
   - 不存在：toast 提示“重解析完成，该条在当前筛选条件下不可见”；
   - 存在：toast 提示“重解析成功”；
6. 若 `editingChunk?.id === chunkId` 且重解析成功，额外 toast 提示“当前抽屉内容可能过期，请关闭后重新打开再编辑”；
7. catch：展示 `e.message`，若空则兜底“重解析失败，请稍后重试”；
8. finally：移除 `chunkId`。

- [ ] **Step 4: 透传状态/事件到 `ChunkCard`**

实现：
- `isReparsing={reparsingIds.has(chunk.id)}`
- `onReparse={() => handleReparse(chunk.id)}`

- [ ] **Step 5: 运行构建验证列表逻辑**

Run: `cd web && pnpm --filter @acme/console build`
Expected: PASS，无 hook/类型错误。

- [ ] **Step 6: 手工验证关键行为**

Run: `cd web && pnpm dev:console`
Manual checks:
1. 点击某条“重解析”后，该条按钮变为 `重解析中...`，且该条“编辑”禁用；
2. 成功后提示成功，并恢复可操作；
3. 失败后提示失败，并恢复可重试；
4. 同一条重复点击不会发起多次请求；
5. 不同条可并行重解析且互不影响。
6. 若对应抽屉已打开，重解析成功后出现“抽屉内容可能过期”提示。
7. 打开抽屉后执行一次常规“保存”，确认保存链路无回归。

- [ ] **Step 7: Commit**

```bash
git add web/apps/console/src/components/ChunkList.tsx
git commit -m "feat(console): wire chunk reparse flow in list"
```

---

### Task 4: 联合回归与文档同步

**Files:**
- Modify: `docs/superpowers/specs/2026-03-24-chunk-reparse-console-design.md`（仅当实现与文档细节不一致时）

- [ ] **Step 1: 运行最终回归构建**

Run: `cd web && pnpm build:console`
Expected: PASS。

- [ ] **Step 2: 运行静态检查（若项目可用）**

Run: `cd web && pnpm --filter @acme/console lint`
Expected: PASS；若存在历史遗留错误，记录并区分“非本次引入”。

- [ ] **Step 3: 核对 spec 与实现一致性**

检查项：
- 入口在列表（非抽屉）；
- 处理中该条不可编辑；
- 成功/失败反馈齐全；
- “当前筛选下不可见”提示已实现；
- 抽屉不做联动刷新，但在已打开且重解析成功时有“可能过期”提示。

- [ ] **Step 4: 结束标准核对（不新增收尾 commit）**

完成定义（DoD）：
- `cd web && pnpm --filter @acme/console build` 通过；
- 关键手测 1/2/3/4/5/6/7 全部通过；
- 已覆盖边界：重解析后该条可能因当前筛选/分页条件不可见；
- 若有 lint 历史遗留，已明确标注“非本次引入”。

---

## Test Plan Summary

- Build: `cd web && pnpm --filter @acme/console build`
- Optional lint: `cd web && pnpm --filter @acme/console lint`
- Manual E2E in console page:
  - 单条触发 loading + 禁用编辑；
  - 成功刷新、失败可重试；
  - 同条防重、不同条并行。

## Risks & Mitigations

- **风险：** `Set` 原地修改导致 UI 不更新。  
  **规避：** 强制不可变更新写法并在 code review 检查。
- **风险：** 刷新后目标不在当前筛选导致用户误判“没成功”。  
  **规避：** 增加专门 toast 文案说明。
- **风险：** 并行请求状态混乱。  
  **规避：** 按 chunk_id 粒度管理 `reparsingIds`，不做全局锁。
