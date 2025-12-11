import { sql } from "drizzle-orm";
import {
  boolean,
  jsonb,
  pgTable,
  serial,
  text,
  varchar,
} from "drizzle-orm/pg-core";

export const IngredientTable = pgTable("ingredients", {
  id: serial("id").primaryKey(),

  // 基本信息
  name: varchar("name", { length: 255 }).notNull(),
  alias: jsonb("alias").default(sql`'[]'::jsonb`), // 别名数组

  description: text("description"),

  // 添加剂信息
  is_additive: boolean("is_additive").default(false),
  additive_code: varchar("additive_code", { length: 50 }), // 如 E330

  // 国家执行标准
  standard_code: varchar("standard_code", { length: 255 }), // 如 GB 2760

  // 风险管理信息
  risk_level: varchar("risk_level", { length: 100 }), // WHO 致癌等级
  pregnancy_level: varchar("pregnancy_level", { length: 50 }), // 母婴等级
  allergen_info: varchar("allergen_info", { length: 255 }),

  function_type: varchar("function_type", { length: 100 }), // 防腐剂/增稠剂
  origin_type: varchar("origin_type", { length: 100 }), // 植物/动物/化学

  limit_usage: varchar("limit_usage", { length: 255 }), // 使用限量
  legal_region: varchar("legal_region", { length: 255 }), // 中国/欧盟/美国

  metadata: jsonb("metadata").default(sql`'{}'::jsonb`), // 扩展字段
});
