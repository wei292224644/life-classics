import {
  integer,
  jsonb,
  pgEnum,
  pgTable,
  text,
  varchar,
} from "drizzle-orm/pg-core";

import { FoodTable } from "./food";
import { FullyAuditedColumns } from "./share-schema";

export const AnalysisVersionEnum = pgEnum("analysis_version", [
  "v1", // 分析版本1
]);

export const RiskLevelEnum = pgEnum("risk_level", [
  "low", // 低风险
  "medium", // 中风险
  "high", // 高风险
]);

export const PregnancyLevelEnum = pgEnum("pregnancy_level", [
  "low", // 低风险
  "medium", // 中风险
  "high", // 高风险
]);

export const FoodAiAnalysisTable = pgTable("food_ai_analysis", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  food_id: integer()
    .references(() => FoodTable.id)
    .notNull(),

  analysis_version: AnalysisVersionEnum("analysis_version").notNull(), // 分析版本
  ai_model: varchar("ai_model", { length: 255 }).notNull(), // 使用的AI模型

  //食用建议
  usage_suggestion_results: text("usage_suggestion_results")
    .array()
    .default([])
    .notNull(),

  //健康益处
  health_benefit_results: text("health_benefit_results")
    .array()
    .default([])
    .notNull(),

  //配料分析结果
  ingredient_analysis_results: text("ingredient_analysis_results")
    .array()
    .default([])
    .notNull(),

  //针对母婴分析结果
  pregnancy_analysis_results: text("pregnancy_analysis_results")
    .array()
    .default([])
    .notNull(),

  risk_level: RiskLevelEnum("risk_level").notNull(), // 风险等级
  pregnancy_level: PregnancyLevelEnum("pregnancy_level").notNull(), // 母婴等级
  confidence_score: integer("confidence_score").notNull(), // 置信度
  raw_output: jsonb("raw_output").notNull(), // 原始输出

  ...FullyAuditedColumns,
});
