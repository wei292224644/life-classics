# Findings

> 最后更新：2026-03-27

## 代码架构发现

### 后端配料 API 重构已完成
- `IngredientDetail` dataclass 现在返回 `analyses: list[dict]`（所有分析类型）
- `related_products` 通过 JOIN `FoodIngredient -> Food` 查询，最多返回 6 个
- `IngredientResponse` 复用 `AnalysisResponse` model

### 前端配料详情页
- `riskLevel` 通过 `analyses.find(a => a.analysis_type === "overall_risk")?.level` 获取
- `relatedProducts` 直接从 `ingredient.value?.related_products ?? []` 获取

### 前端产品页
- `overallRiskLevel` 通过 `store.product?.analysis.find(a => a.analysis_type === "overall_risk")?.level` 获取

### 搜索页
- 使用 mock 数据，`fetchSearch` 函数匹配 name 字段
- 搜索历史和最近查看使用 `uni.getStorageSync` 本地存储
- 筛选在客户端通过 `filteredResults` computed 完成

## 待解决
- 搜索 API 后端已实现（commit `751306f`），前端 `services/search.ts` 需取消 mock 注释替换为真实 API 调用
