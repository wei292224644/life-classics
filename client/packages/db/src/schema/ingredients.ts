import { sql } from "drizzle-orm";
import {
  boolean,
  integer,
  jsonb,
  pgEnum,
  pgTable,
  text,
  varchar,
} from "drizzle-orm/pg-core";

export const WhoLevelEnum = pgEnum("who_level", [
  "Group 1", // 1类致癌物
  "Group 2A", // 2A类致癌物
  "Group 2B", // 2B类致癌物
  "Group 3", // 3类致癌物
  "Group 4", // 4类致癌物
]);

export const IngredientTable = pgTable("ingredients", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),

  // 基本信息
  name: varchar({ length: 255 }).notNull(),
  alias: varchar({ length: 255 }).array().notNull().default([]), // 别名数组

  description: text("description"),

  // 添加剂信息
  is_additive: boolean().default(false),
  additive_code: varchar({ length: 50 }), // 如 E330

  // 国家执行标准
  standard_code: varchar({ length: 255 }), // 如 GB 2760

  // 风险管理信息
  who_level: WhoLevelEnum("who_level"), // WHO 致癌等级
  pregnancy_level: varchar({ length: 50 }), // 母婴等级
  allergen_info: varchar({ length: 255 }), // 过敏信息

  function_type: varchar({ length: 100 }), // 功能来源，如防腐剂/增稠剂
  origin_type: varchar({ length: 100 }), // 来源类型，如植物/动物/化学
  limit_usage: varchar({ length: 255 }), // 使用限量
  legal_region: varchar({ length: 255 }), // 法律适用区域，如中国/欧盟/美国

  metadata: jsonb("metadata").default(sql`'{}'::jsonb`), // 扩展字段
});
