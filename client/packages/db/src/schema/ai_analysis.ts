import { integer, jsonb, pgEnum, pgTable, varchar } from "drizzle-orm/pg-core";

import { FullyAuditedColumns } from "./share-schema";

export const AnalysisVersionEnum = pgEnum("analysis_version", [
  "v1", // 分析版本1
]);

export const LevelEnum = pgEnum("level", [
  "t0", // 低风险
  "t1", // 中风险
  "t2", // 高风险
  "t3", // 中高风险
  "t4", // 高风险
  "unknown", // 信息不足
]);

export const AnalysisTypeEnum = pgEnum("analysis_type", [
  "ingredient_usage_advice", // 食用建议
  "ingredient_health_summary", // 健康分析
  "ingredient_risk_summary", // 风险分析
  "ingredient_pregnancy_safety", // 母婴安全分析
  "food_risk_summary", // 食品安全风险分析
]);

export const AnalysisTargetEnum = pgEnum("analysis_target", [
  "food",
  "ingredient",
  // 未来可扩展
  // "brand",
  // "diet_group",
]);

export const AnalysisDetailTable = pgTable("analysis_details", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  target_id: integer().notNull(),
  target_type: AnalysisTargetEnum("analysis_target").notNull(),

  analysis_type: varchar("analysis_type", { length: 255 }).notNull(), // 分析类型
  analysis_version: AnalysisVersionEnum("analysis_version").notNull(), // 分析版本
  ai_model: varchar("ai_model", { length: 255 }).notNull(), // 使用的AI模型

  results: jsonb("results").notNull(), // 分析结果，数组类型，每个元素为一条分析结果，每条分析结果的结构必须完全一致。
  level: LevelEnum("level").notNull(), // 风险等级
  confidence_score: integer("confidence_score").notNull(), // 置信度
  raw_output: jsonb("raw_output").notNull(), // 原始输出

  ...FullyAuditedColumns,
});
