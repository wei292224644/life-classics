import { integer, jsonb, pgEnum, pgTable, varchar } from "drizzle-orm/pg-core";

import { FoodTable } from "./food";
import { FullyAuditedColumns } from "./share-schema";

export const AnalysisTypeEnum = pgEnum("analysis_type", [
  "nutrition", // 营养分析
  "ingredient", // 成分分析
  "risk", // 风险分析，如致癌物分析，重金属分析等
  "pregnancy", // 母婴分析，如孕妇禁忌物分析，婴幼儿禁忌物分析等
  "dietary", // 饮食分析，如饮食禁忌分析，饮食推荐分析等
  "allergen", // 过敏分析
  "other", // 其他分析，如包装材料分析，添加剂分析等
]);

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

  analysis_type: AnalysisTypeEnum("analysis_type").notNull(), // 分析类型：nutrition, ingredient, risk, pregnancy, etc.
  analysis_version: AnalysisVersionEnum("analysis_version").notNull(), // 分析版本
  ai_model: varchar("ai_model", { length: 255 }).notNull(), // 使用的AI模型
  summary: varchar("summary", { length: 255 }).notNull(), // 分析摘要
  risk_level: RiskLevelEnum("risk_level").notNull(), // 风险等级
  pregnancy_level: PregnancyLevelEnum("pregnancy_level").notNull(), // 母婴等级
  confidence_score: integer("confidence_score").notNull(), // 置信度
  raw_output: jsonb("raw_output").notNull(), // 原始输出

  ...FullyAuditedColumns,
});
