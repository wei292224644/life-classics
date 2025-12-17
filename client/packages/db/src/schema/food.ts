import {
  integer,
  numeric,
  pgEnum,
  pgTable,
  varchar,
} from "drizzle-orm/pg-core";

import { IngredientTable } from "./ingredients";
import { NutritionTable } from "./nutritions";
import { FullyAuditedColumns } from "./share-schema";

export const FoodTable = pgTable("foods", {
  // --- 基础信息 ---
  // id: varchar("id", { length: 32 }).primaryKey(), // 采用商品码（条形码）为主键

  id: integer().generatedAlwaysAsIdentity().primaryKey(),

  barcode: varchar("barcode", { length: 32 }).notNull().unique(),

  name: varchar("name", { length: 255 }).notNull(), // 商品名称

  image_url_list: varchar("image_url_list", { length: 255 })
    .array()
    .default([]),

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

export const UnitEnum = pgEnum("unit", ["g", "mg", "kcal", "mL", "kJ"]);
export const ReferenceUnitEnum = pgEnum("reference_unit", [
  "g",
  "mg",
  "kcal",
  "mL",
  "kJ",
  "serving",
  "day",
]);

export const ReferenceTypeEnum = pgEnum("reference_type", [
  "PER_100_WEIGHT", // 每100g
  "PER_100_ENERGY", // 每100kcal
  "PER_SERVING", // 每份
  "PER_DAY", // 每日
]);

export const FoodNutritionTable = pgTable("food_nutrition_table", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  food_id: integer()
    .references(() => FoodTable.id)
    .notNull(),
  nutrition_id: integer()
    .references(() => NutritionTable.id)
    .notNull(),

  // 单位与说明
  value: numeric("value", { precision: 10, scale: 4 }).notNull(),
  value_unit: UnitEnum("value_unit").notNull(), // g / mg / kJ / kcal
  reference_type: ReferenceTypeEnum("reference_type").notNull(),
  reference_unit: ReferenceUnitEnum("reference_unit").notNull(),

  // --- 审计字段 ---
  ...FullyAuditedColumns,
});
