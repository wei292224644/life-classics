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

export const IngredientTable = pgTable("ingredients", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),

  // 基本信息
  name: varchar({ length: 255 }).notNull(),
  alias: jsonb("alias").default(sql`'[]'::jsonb`), // 别名数组

  description: text("description"),

  // 添加剂信息
  is_additive: boolean().default(false),
  additive_code: varchar({ length: 50 }), // 如 E330

  // 国家执行标准
  standard_code: varchar({ length: 255 }), // 如 GB 2760

  // 风险管理信息
  risk_level: varchar({ length: 100 }), // WHO 致癌等级
  pregnancy_level: varchar({ length: 50 }), // 母婴等级
  allergen_info: varchar({ length: 255 }),

  function_type: varchar({ length: 100 }), // 防腐剂/增稠剂
  origin_type: varchar({ length: 100 }), // 植物/动物/化学

  limit_usage: varchar({ length: 255 }), // 使用限量
  legal_region: varchar({ length: 255 }), // 中国/欧盟/美国

  metadata: jsonb("metadata").default(sql`'{}'::jsonb`), // 扩展字段

  // --- 审计字段 ---
  ...FullyAuditedColumns,
});
