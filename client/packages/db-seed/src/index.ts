import { db } from "@acme/db/client";
import {
  foodNutritionItems,
  FoodTable,
  IngredientTable,
  NutritionItemTable,
} from "@acme/db/schema";

interface SeedResult {
  table: string;
  inserted: number;
}

async function seedIngredients(): Promise<SeedResult> {
  const rows = [
    {
      id: 1,
      name: "白砂糖",
      alias: ["砂糖"],
      description: "常见甜味剂",
      is_additive: false,
      origin_type: "植物",
    },
    {
      id: 2,
      name: "食用盐",
      alias: ["食盐"],
      description: "调味品，主要成分为氯化钠",
      is_additive: false,
      origin_type: "矿物",
    },
    {
      id: 3,
      name: "维生素C",
      alias: ["抗坏血酸"],
      description: "常用抗氧化剂/营养强化剂",
      is_additive: true,
      additive_code: "E300",
      origin_type: "化学",
    },
  ];

  await db
    .insert(IngredientTable)
    .values(rows)
    .onConflictDoNothing({ target: IngredientTable.id });

  return { table: "ingredients", inserted: rows.length };
}

async function seedNutritionItems(): Promise<SeedResult> {
  const rows = [
    {
      id: 1,
      name: "能量",
      category: "宏量营养素",
      unit: "kJ",
      alias: ["热量"],
    },
    {
      id: 2,
      name: "蛋白质",
      category: "宏量营养素",
      unit: "g",
    },
    {
      id: 3,
      name: "脂肪",
      category: "宏量营养素",
      unit: "g",
    },
    {
      id: 4,
      name: "碳水化合物",
      category: "宏量营养素",
      unit: "g",
    },
    {
      id: 5,
      name: "钠",
      category: "微量元素",
      unit: "mg",
    },
  ];

  await db
    .insert(NutritionItemTable)
    .values(rows)
    .onConflictDoNothing({ target: NutritionItemTable.id });

  return { table: "nutrition_items", inserted: rows.length };
}

async function seedFoods(): Promise<SeedResult> {
  const rows = [
    {
      id: "6901234567890",
      name: "经典苏打饼干",
      ingredients: [2, 3],
      manufacturer: "美味食品有限公司",
      origin_place: "中国",
      shelf_life: "12个月",
      net_content: "200g",
    },
    {
      id: "6900987654321",
      name: "维C 橙味饮料",
      ingredients: [1, 3],
      manufacturer: "清爽饮品股份",
      origin_place: "中国",
      shelf_life: "9个月",
      net_content: "500mL",
    },
  ];

  await db
    .insert(FoodTable)
    .values(rows)
    .onConflictDoNothing({ target: FoodTable.id });

  return { table: "foods", inserted: rows.length };
}

async function seedFoodNutrition(): Promise<SeedResult> {
  const rows = [
    // 经典苏打饼干
    {
      food_id: "6901234567890",
      nutrition_id: 1,
      amount: "1900",
      unit: "kJ",
      per: "100g",
    },
    {
      food_id: "6901234567890",
      nutrition_id: 2,
      amount: "7.0",
      unit: "g",
      per: "100g",
    },
    {
      food_id: "6901234567890",
      nutrition_id: 3,
      amount: "12.0",
      unit: "g",
      per: "100g",
    },
    {
      food_id: "6901234567890",
      nutrition_id: 4,
      amount: "70.0",
      unit: "g",
      per: "100g",
    },
    {
      food_id: "6901234567890",
      nutrition_id: 5,
      amount: "320",
      unit: "mg",
      per: "100g",
    },

    // 维C 橙味饮料
    {
      food_id: "6900987654321",
      nutrition_id: 1,
      amount: "170",
      unit: "kJ",
      per: "100mL",
    },
    {
      food_id: "6900987654321",
      nutrition_id: 2,
      amount: "0.3",
      unit: "g",
      per: "100mL",
    },
    {
      food_id: "6900987654321",
      nutrition_id: 3,
      amount: "0",
      unit: "g",
      per: "100mL",
    },
    {
      food_id: "6900987654321",
      nutrition_id: 4,
      amount: "9.5",
      unit: "g",
      per: "100mL",
    },
    {
      food_id: "6900987654321",
      nutrition_id: 5,
      amount: "10",
      unit: "mg",
      per: "100mL",
    },
  ];

  await db.insert(foodNutritionItems).values(rows).onConflictDoNothing();

  return { table: "food_nutrition_items", inserted: rows.length };
}

async function main() {
  const results: SeedResult[] = [];

  results.push(await seedIngredients());
  results.push(await seedNutritionItems());
  results.push(await seedFoods());
  results.push(await seedFoodNutrition());

  for (const r of results) {
    console.log(`Seeded ${r.inserted} rows into ${r.table}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
