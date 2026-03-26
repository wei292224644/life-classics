export interface RelatedProduct {
  id: number;
  name: string;
  barcode: string;
  emoji: string;
  riskTag?: string;
  image_url_list?: string[];
}

export const MOCK_RESULTS: Record<string, unknown> = {
  summary:
    "香草精是一种广泛使用的食品香料，主要成分为香兰素（vanillin），可天然提取自香草豆荚，也可人工合成。常用于烘焙食品、甜点、饮料、冰淇淋等中增香。天然香草精含有超过200种风味化合物，香气更为复杂细腻。",
  risk_factors: [
    "市售香草精多为人工合成香兰素，与天然香草精成分存在差异",
    "长期大量摄入人工合成香兰素可能对肝脏产生轻微影响",
    "极少数人群可能出现过敏反应，表现为皮肤瘙痒或消化不适",
  ],
  suggestions: [
    { text: "正常烹饪用量（每次数滴）在成人中是安全的", type: "positive" },
    {
      text: "购买时注意区分天然香草精（vanilla extract）与人工香草精（artificial vanilla）",
      type: "conditional",
    },
    { text: "婴幼儿辅食建议使用天然来源香料并控制用量", type: "conditional" },
  ],
};

export const MOCK_RELATED_PRODUCTS: RelatedProduct[] = [
  {
    id: 1,
    name: "午餐肉罐头",
    barcode: "6901234567890",
    emoji: "🥫",
    riskTag: "t4",
  },
  {
    id: 2,
    name: "火腿肠",
    barcode: "6901234567891",
    emoji: "🌭",
    riskTag: "t4",
  },
  {
    id: 3,
    name: "培根片",
    barcode: "6901234567892",
    emoji: "🥩",
    riskTag: "t3",
  },
  {
    id: 4,
    name: "烤肠",
    barcode: "6901234567893",
    emoji: "🍖",
    riskTag: "t4",
  },
];
