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

export const LevelEnum = pgEnum("level", [
  "t0", // 低风险
  "t1", // 中风险
  "t2", // 高风险
  "t3", // 中高风险
  "t4", // 高风险
  "unknown", // 信息不足
]);

export const AnalysisTypeEnum = pgEnum("analysis_type", [
  "usage", // 食用建议
  "health", // 健康分析
  "ingredient", // 配料分析
  "pregnancy", // 母婴分析
  "risk", //近期风险分析
]);

export const FoodAiAnalysisTable = pgTable("food_ai_analysis", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  food_id: integer()
    .references(() => FoodTable.id)
    .notNull(),

  analysis_type: varchar("analysis_type", { length: 255 }).notNull(), // 分析类型
  analysis_version: AnalysisVersionEnum("analysis_version").notNull(), // 分析版本
  ai_model: varchar("ai_model", { length: 255 }).notNull(), // 使用的AI模型

  results: text("results").array().default([]).notNull(), // 分析结果，数组类型，每个元素为一条分析结果，每条分析结果的结构必须完全一致。
  level: LevelEnum("level").notNull(), // 风险等级
  confidence_score: integer("confidence_score").notNull(), // 置信度
  raw_output: jsonb("raw_output").notNull(), // 原始输出

  ...FullyAuditedColumns,
});
