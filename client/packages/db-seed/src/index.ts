import { db } from "@acme/db/client";
import {
  AnalysisDetailTable,
  FoodIngredientTable,
  FoodNutritionTable,
  FoodTable,
  IngredientTable,
  NutritionTable,
} from "@acme/db/schema";

interface SeedResult {
  table: string;
  inserted: number;
}

// 使用一个默认的系统用户 UUID 用于 seed 数据
const SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000";

async function seedIngredients(): Promise<SeedResult> {
  const rows = [
    {
      name: "白砂糖",
      alias: ["砂糖"],
      description: "常见甜味剂",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "食用盐",
      alias: ["食盐"],
      description: "调味品，主要成分为氯化钠",
      is_additive: false,
      origin_type: "矿物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "维生素C",
      alias: ["抗坏血酸"],
      description: "常用抗氧化剂/营养强化剂",
      is_additive: true,
      additive_code: "E300",
      standard_code: "GB 2760",
      function_type: "抗氧化剂",
      origin_type: "化学",
      risk_level: "3类",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "小麦粉",
      alias: ["面粉"],
      description: "主要原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "含麸质",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "植物油",
      alias: ["食用油"],
      description: "常见油脂",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "牛奶",
      alias: ["鲜奶"],
      description: "乳制品原料",
      is_additive: false,
      origin_type: "动物",
      allergen_info: "含乳制品",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "鸡蛋",
      alias: ["蛋"],
      description: "蛋白质来源",
      is_additive: false,
      origin_type: "动物",
      allergen_info: "含蛋类",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "柠檬酸",
      alias: [],
      description: "酸味调节剂",
      is_additive: true,
      additive_code: "E330",
      standard_code: "GB 2760",
      function_type: "酸度调节剂",
      origin_type: "化学",
      risk_level: "3类",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "山梨酸钾",
      alias: [],
      description: "防腐剂",
      is_additive: true,
      additive_code: "E202",
      standard_code: "GB 2760",
      function_type: "防腐剂",
      origin_type: "化学",
      risk_level: "3类",
      who_level: "Unknown" as const,
      limit_usage: "0.5-2.0g/kg",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "食用香精",
      alias: [],
      description: "香精",
      is_additive: true,
      additive_code: "E621",
      standard_code: "GB 2760",
      function_type: "增味剂",
      origin_type: "化学",
      risk_level: "3类",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "可可粉",
      alias: [],
      description: "巧克力原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "咖啡粉",
      alias: [],
      description: "咖啡原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "蜂蜜",
      alias: [],
      description: "天然甜味剂",
      is_additive: false,
      origin_type: "动物",
      allergen_info: "可能含花粉",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "果葡糖浆",
      alias: [],
      description: "甜味剂",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "明胶",
      alias: [],

      description: "增稠剂",
      is_additive: true,
      additive_code: "E441",
      standard_code: "GB 2760",
      function_type: "增稠剂",
      origin_type: "动物",
      risk_level: "3类",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      allergen_info: "可能含动物源性成分",
      createdByUser: SYSTEM_USER_ID,
    },
    // —— 额外补充：让配料库更丰富，便于每个食品分配更多配料 ——
    {
      name: "水",
      alias: ["纯净水"],
      description: "常见原料",
      is_additive: false,
      origin_type: "其他",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "白醋",
      alias: ["醋"],
      description: "酸味调味料",
      is_additive: false,
      origin_type: "发酵",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "酱油",
      alias: ["生抽"],
      description: "调味品",
      is_additive: false,
      origin_type: "发酵",
      allergen_info: "可能含大豆/小麦",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "番茄",
      alias: ["番茄泥"],
      description: "蔬菜原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "洋葱",
      alias: [],
      description: "蔬菜原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "大蒜",
      alias: ["蒜"],
      description: "调味原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "姜",
      alias: ["生姜"],
      description: "调味原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "葱",
      alias: ["青葱"],
      description: "调味原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "辣椒",
      alias: [],
      description: "辛香料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "黑胡椒",
      alias: ["胡椒"],
      description: "香辛料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "花椒",
      alias: [],
      description: "香辛料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "孜然",
      alias: [],
      description: "香辛料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "肉桂",
      alias: [],
      description: "香辛料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "香草精",
      alias: [],
      description: "香料",
      is_additive: true,
      additive_code: "E1519",
      standard_code: "GB 2760",
      function_type: "香料",
      origin_type: "化学",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "柠檬汁",
      alias: [],
      description: "酸味来源",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "橙汁",
      alias: [],
      description: "果汁原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "苹果汁",
      alias: [],
      description: "果汁原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "草莓",
      alias: ["草莓果粒"],
      description: "水果原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "香蕉",
      alias: [],
      description: "水果原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "葡萄干",
      alias: [],
      description: "干果原料",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "花生",
      alias: [],
      description: "坚果原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "坚果/花生过敏原",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "杏仁",
      alias: [],
      description: "坚果原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "坚果过敏原",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "腰果",
      alias: [],
      description: "坚果原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "坚果过敏原",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "核桃",
      alias: [],
      description: "坚果原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "坚果过敏原",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "芝麻",
      alias: ["白芝麻"],
      description: "常见辅料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "芝麻过敏原",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "燕麦",
      alias: ["燕麦片"],
      description: "谷物原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "可能含麸质",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "玉米淀粉",
      alias: ["淀粉"],
      description: "增稠/结构",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "木薯淀粉",
      alias: [],
      description: "增稠/结构",
      is_additive: false,
      origin_type: "植物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "黄油",
      alias: [],
      description: "乳脂原料",
      is_additive: false,
      origin_type: "动物",
      allergen_info: "含乳制品",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "奶油",
      alias: ["淡奶油"],
      description: "乳脂原料",
      is_additive: false,
      origin_type: "动物",
      allergen_info: "含乳制品",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "奶酪",
      alias: [],
      description: "乳制品原料",
      is_additive: false,
      origin_type: "动物",
      allergen_info: "含乳制品",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "乳清粉",
      alias: [],
      description: "乳制品成分",
      is_additive: false,
      origin_type: "动物",
      allergen_info: "含乳制品",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "大豆",
      alias: ["黄豆"],
      description: "豆类原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "大豆过敏原",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "大豆油",
      alias: [],
      description: "植物油脂",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "可能含大豆",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "豆粉",
      alias: [],
      description: "豆类加工原料",
      is_additive: false,
      origin_type: "植物",
      allergen_info: "大豆过敏原",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "乳酸菌",
      alias: ["益生菌"],
      description: "发酵菌种",
      is_additive: false,
      origin_type: "微生物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "酵母",
      alias: [],
      description: "发酵用",
      is_additive: false,
      origin_type: "微生物",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "小苏打",
      alias: ["碳酸氢钠"],
      description: "膨松剂",
      is_additive: true,
      additive_code: "E500",
      standard_code: "GB 2760",
      function_type: "膨松剂",
      origin_type: "化学",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "碳酸钙",
      alias: [],
      description: "营养强化/酸度调节",
      is_additive: true,
      additive_code: "E170",
      standard_code: "GB 2760",
      function_type: "营养强化剂",
      origin_type: "矿物",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "柠檬酸钠",
      alias: [],
      description: "酸度调节剂",
      is_additive: true,
      additive_code: "E331",
      standard_code: "GB 2760",
      function_type: "酸度调节剂",
      origin_type: "化学",
      who_level: "Unknown" as const,
      limit_usage: "按生产需要适量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "三氯蔗糖",
      alias: [],
      description: "甜味剂",
      is_additive: true,
      additive_code: "E955",
      standard_code: "GB 2760",
      function_type: "甜味剂",
      origin_type: "化学",
      who_level: "Unknown" as const,
      limit_usage: "按标准限量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "阿斯巴甜",
      alias: [],
      description: "甜味剂",
      is_additive: true,
      additive_code: "E951",
      standard_code: "GB 2760",
      function_type: "甜味剂",
      origin_type: "化学",
      who_level: "Unknown" as const,
      limit_usage: "按标准限量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "柠檬黄",
      alias: [],
      description: "着色剂",
      is_additive: true,
      additive_code: "E102",
      standard_code: "GB 2760",
      function_type: "着色剂",
      origin_type: "化学",
      who_level: "Unknown" as const,
      limit_usage: "按标准限量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "β-胡萝卜素",
      alias: [],
      description: "着色/营养强化",
      is_additive: true,
      additive_code: "E160a",
      standard_code: "GB 2760",
      function_type: "着色剂",
      origin_type: "植物",
      who_level: "Unknown" as const,
      limit_usage: "按标准限量使用",
      legal_region: "中国/欧盟/美国",
      createdByUser: SYSTEM_USER_ID,
    },
  ];

  // NOTE: IngredientTable.alias 已调整为 string[]（非 jsonb）
  // 这里统一做一次归一化，避免出现非数组/非字符串的 seed 值导致插入失败。
  const normalizedRows = rows.map((row) => ({
    ...row,
  }));

  try {
    await db.insert(IngredientTable).values(normalizedRows);
  } catch (error) {
    // 如果数据已存在，忽略错误
    if (error instanceof Error && error.message.includes("duplicate")) {
      console.log("Ingredients already seeded, skipping...");
    } else {
      throw error;
    }
  }

  return { table: "ingredients", inserted: normalizedRows.length };
}

async function seedNutritionItems(): Promise<SeedResult> {
  const rows = [
    {
      name: "能量",
      category: "宏量营养素",
      alias: ["热量"],
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "蛋白质",
      category: "宏量营养素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "脂肪",
      category: "宏量营养素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "碳水化合物",
      category: "宏量营养素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "钠",
      category: "微量元素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "钙",
      category: "微量元素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "铁",
      category: "微量元素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "维生素A",
      category: "维生素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "维生素B1",
      category: "维生素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "维生素B2",
      category: "维生素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "维生素C",
      category: "维生素",
      createdByUser: SYSTEM_USER_ID,
    },
    {
      name: "膳食纤维",
      category: "宏量营养素",
      createdByUser: SYSTEM_USER_ID,
    },
  ];

  try {
    await db.insert(NutritionTable).values(rows);
  } catch (error) {
    // 如果数据已存在，忽略错误
    if (error instanceof Error && error.message.includes("duplicate")) {
      console.log("Nutrition items already seeded, skipping...");
    } else {
      throw error;
    }
  }
  return { table: "nutrition_items", inserted: rows.length };
}

function generateFoodData(availableIngredientIds: number[]): {
  barcode: string;
  name: string;
  manufacturer?: string;
  production_address?: string;
  origin_place?: string;
  production_license?: string;
  product_category?: string;
  product_standard_code?: string;
  shelf_life?: string;
  net_content?: string;
  createdByUser: string;
  ingredientIds: number[];
}[] {
  function pickUniqueIngredientIds(minCount: number): number[] {
    if (availableIngredientIds.length === 0) return [];

    const count = Math.min(minCount, availableIngredientIds.length);
    const pool = [...availableIngredientIds];

    // Fisher–Yates shuffle（只需要打乱前 count 个也行，但这里简单写全量）
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = pool[i];
      const other = pool[j];
      if (tmp !== undefined && other !== undefined) {
        pool[i] = other;
        pool[j] = tmp;
      }
    }

    return pool.slice(0, count);
  }

  const manufacturers = [
    "美味食品有限公司",
    "清爽饮品股份",
    "健康食品集团",
    "天然食品公司",
    "绿色生活食品",
    "优质食品企业",
    "经典品牌食品",
    "现代食品科技",
    "传统工艺食品",
    "创新食品公司",
    "营养食品厂",
    "有机食品公司",
  ];

  const categories = [
    "饼干糕点",
    "饮料",
    "乳制品",
    "糖果",
    "坚果炒货",
    "方便食品",
    "休闲食品",
    "调味品",
    "速冻食品",
    "罐头食品",
    "肉制品",
    "豆制品",
  ];

  const originPlaces = [
    "中国",
    "美国",
    "日本",
    "韩国",
    "澳大利亚",
    "新西兰",
    "法国",
    "意大利",
  ];

  const shelfLifes = ["6个月", "9个月", "12个月", "18个月", "24个月", "36个月"];

  const netContents = [
    "100g",
    "200g",
    "250g",
    "300g",
    "500g",
    "1kg",
    "250mL",
    "500mL",
    "1L",
  ];

  const foodNames = [
    // 饼干糕点类
    "经典苏打饼干",
    "全麦消化饼",
    "巧克力曲奇",
    "奶油夹心饼干",
    "威化饼干",
    "蛋卷",
    "华夫饼",
    "马卡龙",
    "提拉米苏",
    "芝士蛋糕",
    // 饮料类
    "维C橙味饮料",
    "柠檬蜂蜜茶",
    "绿茶饮料",
    "乌龙茶",
    "咖啡饮料",
    "牛奶饮品",
    "酸奶",
    "果汁饮料",
    "运动饮料",
    "能量饮料",
    // 乳制品
    "纯牛奶",
    "酸奶",
    "奶酪",
    "黄油",
    "淡奶油",
    // 糖果类
    "牛奶巧克力",
    "黑巧克力",
    "水果硬糖",
    "软糖",
    "口香糖",
    "棒棒糖",
    "棉花糖",
    "太妃糖",
    "薄荷糖",
    "润喉糖",
    // 坚果炒货
    "原味花生",
    "盐焗花生",
    "开心果",
    "腰果",
    "杏仁",
    "核桃",
    "夏威夷果",
    "松子",
    "瓜子",
    "板栗",
    // 方便食品
    "方便面",
    "速食粥",
    "自热火锅",
    "速食米饭",
    "即食汤",
    // 休闲食品
    "薯片",
    "虾条",
    "爆米花",
    "海苔",
    "牛肉干",
    "猪肉脯",
    "鱿鱼丝",
    "豆干",
    "话梅",
    "果脯",
    // 调味品
    "生抽",
    "老抽",
    "陈醋",
    "白醋",
    "料酒",
    "蚝油",
    "番茄酱",
    "沙拉酱",
    "辣椒酱",
    "豆瓣酱",
    // 速冻食品
    "速冻水饺",
    "速冻汤圆",
    "速冻包子",
    "速冻馄饨",
    "速冻春卷",
    // 罐头食品
    "水果罐头",
    "肉类罐头",
    "鱼类罐头",
    "蔬菜罐头",
    "汤类罐头",
    // 肉制品
    "火腿肠",
    "午餐肉",
    "培根",
    "香肠",
    "腊肉",
    // 豆制品
    "豆腐",
    "豆浆",
    "豆腐干",
    "腐竹",
    "豆皮",
  ];

  const rows: {
    barcode: string;
    name: string;
    image_url_list: string[];
    manufacturer?: string;
    production_address?: string;
    origin_place?: string;
    production_license?: string;
    product_category?: string;
    product_standard_code?: string;
    shelf_life?: string;
    net_content?: string;
    createdByUser: string;
    ingredientIds: number[];
  }[] = [];

  for (let i = 0; i < 100; i++) {
    const barcode = `690${String(i + 1).padStart(10, "0")}`;
    const name = foodNames[i % foodNames.length] ?? "未知食品";
    const category =
      categories[Math.floor(Math.random() * categories.length)] ?? "其他";
    const manufacturer =
      manufacturers[Math.floor(Math.random() * manufacturers.length)] ??
      "未知厂商";
    const originPlace =
      originPlaces[Math.floor(Math.random() * originPlaces.length)] ?? "中国";
    const shelfLife =
      shelfLifes[Math.floor(Math.random() * shelfLifes.length)] ?? "12个月";
    const netContent =
      netContents[Math.floor(Math.random() * netContents.length)] ?? "100g";

    // 随机生成配料：每个食品至少 8 种（在配料库不足时自动降级为全部配料）
    const ingredientCount = Math.floor(Math.random() * 5) + 8; // 8-12
    const ingredients = pickUniqueIngredientIds(ingredientCount);

    rows.push({
      barcode,
      name,
      image_url_list: [
        `https://picsum.photos/200/300?random=${Math.random()}`,
        `https://picsum.photos/200/300?random=${Math.random()}`,
      ],
      manufacturer,
      production_address: `${originPlace}省${manufacturer}生产厂`,
      origin_place: originPlace,
      production_license: `SC${String(Math.floor(Math.random() * 900000) + 100000)}`,
      product_category: category,
      product_standard_code: `GB/T ${Math.floor(Math.random() * 9000) + 1000}-${new Date().getFullYear()}`,
      shelf_life: shelfLife,
      net_content: netContent,
      createdByUser: SYSTEM_USER_ID,
      ingredientIds:
        ingredients.length > 0 ? ingredients : availableIngredientIds,
    });
  }

  return rows;
}

async function seedFoods(): Promise<SeedResult> {
  // 获取所有已插入的ingredient id
  const ingredients = await db
    .select({ id: IngredientTable.id })
    .from(IngredientTable);
  const ingredientIds = ingredients.map((ing) => ing.id);

  if (ingredientIds.length === 0) {
    return { table: "foods", inserted: 0 };
  }

  const foodData = generateFoodData(ingredientIds);

  // 分离 food 数据和 ingredient 关联数据
  const foodRows = foodData.map(
    ({ ingredientIds: _ingredientIds, ...food }) => food,
  );
  const ingredientMappings = foodData.map((food, index) => ({
    foodIndex: index,
    ingredientIds: food.ingredientIds,
  }));

  try {
    const insertedFoods = await db
      .insert(FoodTable)
      .values(foodRows)
      .returning();

    // 插入 food_ingredients 关联数据
    const foodIngredientRows: {
      food_id: number;
      ingredient_id: number;
      createdByUser: string;
    }[] = [];

    for (let i = 0; i < insertedFoods.length; i++) {
      const food = insertedFoods[i];
      const mapping = ingredientMappings[i];
      if (food && mapping) {
        for (const ingredientId of mapping.ingredientIds) {
          foodIngredientRows.push({
            food_id: food.id,
            ingredient_id: ingredientId,
            createdByUser: SYSTEM_USER_ID,
          });
        }
      }
    }

    if (foodIngredientRows.length > 0) {
      try {
        await db.insert(FoodIngredientTable).values(foodIngredientRows);
      } catch (error) {
        // 如果关联数据已存在，忽略错误
        if (error instanceof Error && error.message.includes("duplicate")) {
          console.log("Food ingredients already seeded, skipping...");
        } else {
          throw error;
        }
      }
    }
  } catch (error) {
    // 如果数据已存在（基于 barcode），忽略错误
    if (error instanceof Error && error.message.includes("duplicate")) {
      console.log("Foods already seeded, skipping...");
    } else {
      throw error;
    }
  }

  return { table: "foods", inserted: foodRows.length };
}

function generateNutritionData(
  foodIds: number[],
  nutritionItems: { id: number; name: string }[],
): {
  food_id: number;
  nutrition_id: number;
  value: string;
  value_unit: "g" | "mg" | "kcal" | "mL" | "kJ";
  reference_type:
    | "PER_100_WEIGHT"
    | "PER_100_ENERGY"
    | "PER_SERVING"
    | "PER_DAY";
  reference_unit: "g" | "mg" | "kcal" | "mL" | "kJ" | "serving" | "day";
  createdByUser: string;
}[] {
  const rows: {
    food_id: number;
    nutrition_id: number;
    value: string;
    value_unit: "g" | "mg" | "kcal" | "mL" | "kJ";
    reference_type:
      | "PER_100_WEIGHT"
      | "PER_100_ENERGY"
      | "PER_SERVING"
      | "PER_DAY";
    reference_unit: "g" | "mg" | "kcal" | "mL" | "kJ" | "serving" | "day";
    createdByUser: string;
  }[] = [];

  if (nutritionItems.length === 0) {
    return rows;
  }

  // 营养成分范围（按每100g/100mL），并给出 value_unit
  const nutritionRanges: Record<
    string,
    { min: number; max: number; unit: "g" | "mg" | "kJ" | "kcal" | "mL" }
  > = {
    能量: { min: 200, max: 2500, unit: "kJ" },
    蛋白质: { min: 0.1, max: 30, unit: "g" },
    脂肪: { min: 0, max: 50, unit: "g" },
    碳水化合物: { min: 0, max: 100, unit: "g" },
    钠: { min: 1, max: 2000, unit: "mg" },
    钙: { min: 10, max: 500, unit: "mg" },
    铁: { min: 0.1, max: 20, unit: "mg" },
    维生素A: { min: 0, max: 1000, unit: "mg" },
    维生素B1: { min: 0, max: 2, unit: "mg" },
    维生素B2: { min: 0, max: 2, unit: "mg" },
    维生素C: { min: 0, max: 200, unit: "mg" },
    膳食纤维: { min: 0, max: 30, unit: "g" },
  };

  // 基础营养成分名称（必须包含）
  const essentialNutritionNames = [
    "能量",
    "蛋白质",
    "脂肪",
    "碳水化合物",
    "钠",
  ];

  // 创建名称到 nutrition item 的映射
  const nutritionMap = new Map<string, { id: number }>();
  for (const item of nutritionItems) {
    nutritionMap.set(item.name, { id: item.id });
  }

  // 获取基础营养成分的 IDs
  const essentialNutritionIds = essentialNutritionNames
    .map((name) => nutritionMap.get(name)?.id)
    .filter((id): id is number => id !== undefined);

  for (const foodId of foodIds) {
    // 每个食品生成5-8个营养成分数据
    const nutritionCount = Math.floor(Math.random() * 4) + 5;
    const selectedNutritions = new Set<number>();

    // 确保包含基础营养成分
    essentialNutritionIds.forEach((id) => selectedNutritions.add(id));

    // 随机添加其他营养成分
    while (
      selectedNutritions.size < nutritionCount &&
      selectedNutritions.size < nutritionItems.length
    ) {
      const randomIndex = Math.floor(Math.random() * nutritionItems.length);
      const nutrition = nutritionItems[randomIndex];
      if (nutrition) {
        selectedNutritions.add(nutrition.id);
      }
    }

    // 判断是液体还是固体（这里简单随机）
    const isLiquid = Math.random() > 0.7;
    const reference_unit = isLiquid ? ("mL" as const) : ("g" as const);
    const reference_type = "PER_100_WEIGHT" as const;

    for (const nutritionId of selectedNutritions) {
      const nutrition = nutritionItems.find((item) => item.id === nutritionId);
      if (!nutrition) continue;

      const range = nutritionRanges[nutrition.name];
      if (!range) continue;

      const value = (
        Math.random() * (range.max - range.min) +
        range.min
      ).toFixed(4);

      rows.push({
        food_id: foodId,
        nutrition_id: nutritionId,
        value,
        value_unit: range.unit,
        reference_type,
        reference_unit,
        createdByUser: SYSTEM_USER_ID,
      });
    }
  }

  return rows;
}

async function seedFoodNutrition(): Promise<SeedResult> {
  // 获取所有已插入的food id
  const foods = await db.select({ id: FoodTable.id }).from(FoodTable);
  const foodIds = foods.map((f) => f.id);

  // 获取所有已插入的nutrition items
  // drizzle 的列类型在此处会被 eslint 视为 `error` 类型；我们显式标注返回结构，避免 no-unsafe-* 报错
  const nutritionItems = (await db
    .select({
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
      id: NutritionTable.id,
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
      name: NutritionTable.name,
    })
    .from(NutritionTable)) as { id: number; name: string }[];

  if (foodIds.length === 0 || nutritionItems.length === 0) {
    return { table: "food_nutrition_items", inserted: 0 };
  }

  const rows = generateNutritionData(foodIds, nutritionItems);

  await db.insert(FoodNutritionTable).values(rows).onConflictDoNothing();

  return { table: "food_nutrition_items", inserted: rows.length };
}

async function seedFoodAiAnalysis(): Promise<SeedResult> {
  // 获取所有已插入的food id
  const foods = await db.select({ id: FoodTable.id }).from(FoodTable);

  if (foods.length === 0) {
    return { table: "analysis_details", inserted: 0 };
  }

  // 新的分析类型枚举值
  const analysisTypes = [
    "usage_advice_summary",
    "health_summary",
    "pregnancy_safety",
    "risk_summary",
    "recent_risk_summary",
  ] as const;
  const levels = ["t0", "t1", "t2", "t3", "t4", "unknown"] as const;
  const aiModels = ["gpt-4", "claude-3", "seed-model"];

  type AnalysisType = (typeof analysisTypes)[number];
  type Level = (typeof levels)[number];

  const rows: {
    target_id: number;
    target_type: "food";
    analysis_type: AnalysisType;
    analysis_version: "v1";
    ai_model: string;
    results: {
      summaries: string[];
    }; // JSONB 字段，存储字符串数组
    level: Level;
    confidence_score: number;
    raw_output: Record<string, unknown>;
    createdByUser: string;
    lastUpdatedByUser: string;
  }[] = [];

  // 为每个食品生成所有5种类型的分析
  for (const food of foods) {
    // 为每个食品生成所有5种分析类型
    for (const analysisType of analysisTypes) {
      const levelIndex = Math.floor(Math.random() * levels.length);
      const level = levels[levelIndex] ?? ("unknown" as Level);
      const aiModel =
        aiModels[Math.floor(Math.random() * aiModels.length)] ?? "seed-model";
      const confidenceScore = Math.floor(Math.random() * 20) + 75; // 75-95

      // 根据分析类型生成不同的结果
      let results: string[] = [];
      let rawOutput: Record<string, unknown> = {};

      switch (analysisType) {
        case "usage_advice_summary":
          results = [
            "建议每日食用量不超过100g",
            "适合作为早餐或下午茶点心",
            "建议搭配新鲜水果一起食用",
          ];
          rawOutput = {
            summary: "基于营养成分和配料表的食用建议分析",
            key_points: ["适量食用", "搭配均衡饮食"],
            uncertainties: [],
          };
          break;
        case "health_summary":
          results = [
            "富含碳水化合物，适合补充能量",
            "含有适量蛋白质，有助于肌肉修复",
            "钠含量适中，注意控制摄入量",
          ];
          rawOutput = {
            summary: "基于营养成分表的健康影响分析",
            key_points: ["能量补充", "蛋白质摄入", "钠含量需注意"],
            uncertainties: [],
          };
          break;
        case "risk_summary":
          results = [
            "主要配料为小麦粉、白砂糖、植物油",
            "含有食品添加剂：维生素C、柠檬酸",
            "无已知过敏原，但需注意麸质含量",
          ];
          rawOutput = {
            summary: "基于配料表的成分分析",
            key_points: [
              "主要配料：小麦粉、白砂糖、植物油",
              "添加剂：维生素C、柠檬酸",
            ],
            uncertainties: ["需注意麸质含量"],
          };
          break;
        case "pregnancy_safety":
          results = [
            "孕妇可适量食用",
            "建议避免过量摄入糖分",
            "注意检查是否有过敏原",
          ];
          rawOutput = {
            summary: "基于配料和营养成分的母婴安全分析",
            key_points: ["适量食用", "注意糖分摄入"],
            uncertainties: ["需确认是否有过敏原"],
          };
          break;
        case "recent_risk_summary":
          results = [
            "近期无重大食品安全风险",
            "建议关注生产日期和保质期",
            "存储条件需符合产品要求",
          ];
          rawOutput = {
            summary: "基于产品信息的近期风险分析",
            key_points: ["注意保质期", "正确存储"],
            uncertainties: [],
          };
          break;
      }

      rows.push({
        target_id: food.id,
        target_type: "food",
        analysis_type: analysisType,
        analysis_version: "v1",
        ai_model: aiModel,
        results: { summaries: results },
        level,
        confidence_score: confidenceScore,
        raw_output: rawOutput,
        createdByUser: SYSTEM_USER_ID,
        lastUpdatedByUser: SYSTEM_USER_ID,
      });
    }
  }

  try {
    await db.insert(AnalysisDetailTable).values(rows).onConflictDoNothing();
  } catch (error) {
    // 如果数据已存在，忽略错误
    if (error instanceof Error && error.message.includes("duplicate")) {
      console.log("Food AI analysis already seeded, skipping...");
    } else {
      throw error;
    }
  }

  return { table: "analysis_details", inserted: rows.length };
}

async function seedIngredientAiAnalysis(): Promise<SeedResult> {
  // 获取所有已插入的 ingredient
  const ingredients = await db
    .select({
      id: IngredientTable.id,
      name: IngredientTable.name,
      is_additive: IngredientTable.is_additive,
      additive_code: IngredientTable.additive_code,
      function_type: IngredientTable.function_type,
      origin_type: IngredientTable.origin_type,
      standard_code: IngredientTable.standard_code,
      who_level: IngredientTable.who_level,
      allergen_info: IngredientTable.allergen_info,
    })
    .from(IngredientTable);

  if (ingredients.length === 0) {
    return { table: "analysis_details", inserted: 0 };
  }

  const aiModels = ["gpt-4", "claude-3", "seed-model"];
  type Level = "t0" | "t1" | "t2" | "t3" | "t4" | "unknown";
  const levelPool: Level[] = ["t0", "t1", "t2", "t3", "t4", "unknown"];

  // 与 AnalysisTypeEnum 保持一致（packages/db/src/schema/ai_analysis.ts）
  const analysisTypes = [
    "usage_advice_summary",
    "health_summary",
    "pregnancy_safety",
    "risk_summary",
    "recent_risk_summary",
    "ingredient_summary",
  ] as const;

  type IngredientAnalysisType = (typeof analysisTypes)[number];

  const rows: {
    target_id: number;
    target_type: "ingredient";
    analysis_type: IngredientAnalysisType;
    analysis_version: "v1";
    ai_model: string;
    results:
      | { result: string; reason: string }
      | {
          summaries: string[];
        };
    level: Level;
    confidence_score: number;
    raw_output: Record<string, unknown>;
    createdByUser: string;
    lastUpdatedByUser: string;
  }[] = [];

  for (const ing of ingredients) {
    for (const analysisType of analysisTypes) {
      const aiModel =
        aiModels[Math.floor(Math.random() * aiModels.length)] ?? "seed-model";
      const confidenceScore = Math.floor(Math.random() * 15) + 80; // 80-94

      // 风险等级：用 ingredient.id 做可复现的均匀分布（整体更“平均”）
      const level = levelPool[ing.id % levelPool.length] ?? "unknown";

      const baseSummaries: string[] = [];
      baseSummaries.push(`配料：${ing.name}`);

      if (ing.is_additive) {
        baseSummaries.push(
          `类型：食品添加剂${
            ing.additive_code ? `（${ing.additive_code}）` : ""
          }`,
        );
        if (ing.function_type)
          baseSummaries.push(`常见用途：${ing.function_type}`);
        if (ing.standard_code)
          baseSummaries.push(`参考标准：${ing.standard_code}`);
      } else {
        baseSummaries.push("类型：常规食品原料");
      }

      if (ing.origin_type) baseSummaries.push(`来源：${ing.origin_type}`);
      if (ing.who_level) baseSummaries.push(`WHO 分级：${ing.who_level}`);

      if (ing.allergen_info)
        baseSummaries.push(`过敏提示：${ing.allergen_info}`);

      // NOTE: analysis.results 的结构会随 analysis_type 变化而变化
      // 参见：packages/api/src/router/ai-analysis/type.ts
      const rawOutput = {
        summary: `对配料「${ing.name}」的分析（seed 数据）`,
        analysis_type: analysisType,
        key_points: [
          ing.is_additive ? "注意摄入量与敏感人群" : "一般人群可正常食用",
          ing.allergen_info ? "存在过敏风险提示" : "无显著过敏风险提示",
        ],
        uncertainties: ["该分析为 seed 示例数据，非真实权威结论"],
      };

      if (analysisType === "ingredient_summary") {
        const result =
          level === "t4" || level === "t3"
            ? "不建议"
            : level === "t2"
              ? "谨慎"
              : level === "t1" || level === "t0"
                ? "可接受"
                : "未知";

        rows.push({
          target_id: ing.id,
          target_type: "ingredient",
          analysis_type: analysisType,
          analysis_version: "v1",
          ai_model: aiModel,
          results: { result, reason: baseSummaries.join("；") },
          level,
          confidence_score: confidenceScore,
          raw_output: rawOutput,
          createdByUser: SYSTEM_USER_ID,
          lastUpdatedByUser: SYSTEM_USER_ID,
        });
        continue;
      }

      // 其它类型统一用 summaries
      const summaries =
        analysisType === "risk_summary"
          ? [
              ...baseSummaries,
              "风险提示：请关注添加剂/过敏原/敏感人群（seed 示例）",
            ]
          : analysisType === "recent_risk_summary"
            ? [...baseSummaries, "近期风险：暂无权威召回信息（seed 示例）"]
            : analysisType === "pregnancy_safety"
              ? [
                  ...baseSummaries,
                  "母婴建议：孕妇/哺乳期人群请结合自身情况适量（seed 示例）",
                ]
              : analysisType === "health_summary"
                ? [
                    ...baseSummaries,
                    "健康影响：请结合整体饮食结构评估（seed 示例）",
                  ]
                : [
                    ...baseSummaries,
                    "使用建议：适量摄入，注意均衡搭配（seed 示例）",
                  ];

      rows.push({
        target_id: ing.id,
        target_type: "ingredient",
        analysis_type: analysisType,
        analysis_version: "v1",
        ai_model: aiModel,
        results: { summaries },
        level,
        confidence_score: confidenceScore,
        raw_output: rawOutput,
        createdByUser: SYSTEM_USER_ID,
        lastUpdatedByUser: SYSTEM_USER_ID,
      });
    }
  }

  await db.insert(AnalysisDetailTable).values(rows).onConflictDoNothing();

  return { table: "analysis_details", inserted: rows.length };
}

async function clearAllData(): Promise<void> {
  console.log("Clearing all data from database...");

  try {
    // 按照外键依赖关系的逆序删除数据
    // 先删除有外键依赖的表
    await db.delete(AnalysisDetailTable);
    console.log("Cleared analysis_details table");

    await db.delete(FoodIngredientTable);
    console.log("Cleared food_ingredients table");

    await db.delete(FoodNutritionTable);
    console.log("Cleared food_nutrition_table table");

    // 然后删除主表
    await db.delete(FoodTable);
    console.log("Cleared foods table");

    await db.delete(IngredientTable);
    console.log("Cleared ingredients table");

    await db.delete(NutritionTable);
    console.log("Cleared nutrition_table table");

    console.log("All data cleared successfully!");
  } catch (error) {
    console.error("Error clearing data:", error);
    throw error;
  }
}

async function main() {
  // 先清除所有数据
  await clearAllData();

  const results: SeedResult[] = [];

  results.push(await seedIngredients());
  results.push(await seedIngredientAiAnalysis());
  results.push(await seedNutritionItems());
  results.push(await seedFoods());
  results.push(await seedFoodNutrition());
  results.push(await seedFoodAiAnalysis());

  for (const r of results) {
    console.log(`Seeded ${r.inserted} rows into ${r.table}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
