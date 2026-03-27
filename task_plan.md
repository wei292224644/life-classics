# Task Plan

> 最后更新：2026-03-27

## 当前活跃任务

### 1. 配料 Overall Risk 重构 ✅ 已完成
**计划文件：** `docs/superpowers/plans/2026-03-27-ingredient-overall-risk.md`

**已完成：**
- [x] 后端 `IngredientDetail` dataclass 修改（`analysis → analyses`）
- [x] 后端 `fetch_by_id()` 返回全部分析记录
- [x] 后端 `IngredientResponse` model 更新
- [x] 后端 `IngredientService._to_ingredient_response()` 构建 analyses 列表
- [x] 前端 `types/ingredient.ts` 更新（`analyses: AnalysisSummary[]`）
- [x] 前端 `pages/ingredient-detail/index.vue` 修复 `riskLevel` computed
- [x] 前端 `pages/product/index.vue` 修复 `overallRiskLevel` computed
- [x] 提交：`b136cbc` - fix(ingredient): read riskLevel from analyses.overall_risk, display tags

---

### 2. 配料详情页「含此配料的产品」✅ 已完成
**计划文件：** `docs/superpowers/plans/2026-03-27-ingredient-related-products.md`

**已完成：**
- [x] 后端 `RelatedProductSimple` Pydantic model
- [x] 后端 `IngredientDetail.related_products` dataclass
- [x] 后端 JOIN 查询获取关联产品
- [x] 后端 Service 层转换
- [x] 前端 `IngredientDetail.related_products` 类型
- [x] 前端页面 `relatedProducts` 从接口获取

---

### 3. 搜索页重设计 ✅ 已完成
**计划文件：** `docs/superpowers/plans/2026-03-27-search-page-redesign.md`

**已完成：**
- [x] `services/search.ts` 创建（mock fallback）
- [x] `pages/search/index.vue` 完整重写
  - 搜索框 + 筛选 chip
  - 搜索历史（本地存储）
  - 热门搜索
  - 最近查看
  - 搜索结果列表
- [x] 提交：`e1fc86c` - feat(search): complete search page redesign with TW classes

**待办：**
- [ ] 联调真实搜索 API（后端 `/api/search` 就绪后替换 mock）

---

## 遇到的错误

| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| 无 | - | - |

---

## 已完成但未提交的文件

无 - 所有变更已提交
