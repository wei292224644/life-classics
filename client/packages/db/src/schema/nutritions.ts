import { sql } from "drizzle-orm";
import {
  boolean,
  integer,
  jsonb,
  pgTable,
  text,
  varchar,
} from "drizzle-orm/pg-core";

import { FullyAuditedColumns } from "./share-schema";

export const NutritionTable = pgTable("nutrition_table", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),

  // 基本信息
  name: varchar("name", { length: 255 }).notNull(),
  alias: varchar({ length: 255 }).array().default([]), // 别名数组

  // 分类
  category: varchar("category", { length: 255 }), // 如：维生素
  sub_category: varchar("sub_category", { length: 255 }), // 如：维生素B族

  description: text("description"),

  // 营养指南
  daily_value: varchar("daily_value", { length: 255 }), // 推荐摄入
  upper_limit: varchar("upper_limit", { length: 255 }), // 上限 UL
  is_essential: boolean("is_essential").default(false), // 是否必需

  // 风险信息
  risk_info: text("risk_info"),
  pregnancy_note: text("pregnancy_note"),

  // 功能性
  metabolism_role: varchar("metabolism_role", { length: 255 }), // 抗氧化/免疫等

  metadata: jsonb("metadata").default(sql`'{}'::jsonb`),

  // --- 审计字段 ---
  ...FullyAuditedColumns,
});
