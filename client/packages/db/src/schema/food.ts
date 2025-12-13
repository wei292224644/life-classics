import { integer, pgTable, varchar } from "drizzle-orm/pg-core";

import { IngredientTable } from "./ingredients";
import { NutritionItemTable } from "./nutrition-items";
import { FullyAuditedColumns } from "./share-schema";

export const FoodTable = pgTable("foods", {
  // --- 基础信息 ---
  // id: varchar("id", { length: 32 }).primaryKey(), // 采用商品码（条形码）为主键

  id: integer().generatedAlwaysAsIdentity().primaryKey(),

  barcode: varchar("barcode", { length: 32 }).notNull().unique(),

  name: varchar("name", { length: 255 }).notNull(), // 商品名称

  // --- 工商生产类信息 ---
  manufacturer: varchar("manufacturer", { length: 255 }), // 委托商
  production_address: varchar("production_address", { length: 255 }),
  origin_place: varchar("origin_place", { length: 255 }), // 产地

  production_license: varchar("production_license", { length: 255 }), // 食品生产许可编号
  product_category: varchar("product_category", { length: 255 }),
  product_standard_code: varchar("product_standard_code", { length: 255 }),

  // --- 产品规格 ---
  shelf_life: varchar("shelf_life", { length: 100 }), // 保质期（一般有格式差异，用字符串更好）
  net_content: varchar("net_content", { length: 100 }), // 净含量（例如："500g", "1L"）

  // --- 审计字段 ---
  ...FullyAuditedColumns,
});

export const FoodIngredientTable = pgTable("food_ingredients", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  food_id: integer()
    .references(() => FoodTable.id)
    .notNull(),
  ingredient_id: integer()
    .references(() => IngredientTable.id)
    .notNull(),

  // --- 审计字段 ---
  ...FullyAuditedColumns,
});

export const FoodNutritionItemTable = pgTable("food_nutrition_items", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  food_id: integer()
    .references(() => FoodTable.id)
    .notNull(),
  nutrition_id: integer()
    .references(() => NutritionItemTable.id)
    .notNull(),
  amount: varchar("amount", { length: 100 }).notNull(), // 如 "3.1"
  unit: varchar("unit", { length: 50 }), // g / kJ
  per: varchar("per", { length: 50 }).default("100g"), // 每份/每100g等

  // --- 审计字段 ---
  ...FullyAuditedColumns,
});
