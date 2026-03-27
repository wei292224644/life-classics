// web/apps/uniapp-tw/src/services/search.ts

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

export type FilterType = "all" | "product" | "ingredient";

export interface SearchResultItem {
  type: "product" | "ingredient";
  id: number;
  /** 食品：条形码（用于导航）；配料：undefined */
  barcode?: string;
  name: string;
  /** 食品：品类；配料：功能类型 */
  subtitle: string;
  /** 风险等级 t4/t3/t2/t1/t0/unknown */
  riskLevel: string;
  /** 食品：高风险配料数量 */
  highRiskCount?: number;
}

// ── Mock data（后端接口就绪后替换为真实 API 调用）──────────────
const MOCK_ITEMS: SearchResultItem[] = [
  { type: "ingredient", id: 1, name: "苯甲酸钠", subtitle: "防腐剂", riskLevel: "t4" },
  { type: "ingredient", id: 2, name: "香兰素", subtitle: "香料", riskLevel: "t2" },
  { type: "ingredient", id: 3, name: "谷氨酸钠", subtitle: "增味剂", riskLevel: "t1" },
  { type: "ingredient", id: 4, name: "阿斯巴甜", subtitle: "甜味剂", riskLevel: "t3" },
  { type: "ingredient", id: 5, name: "亚硝酸钠", subtitle: "防腐剂 / 护色剂", riskLevel: "t4" },
  { type: "product", id: 101, barcode: "6920152420245", name: "康师傅红烧牛肉面", subtitle: "方便食品", riskLevel: "t3", highRiskCount: 3 },
  { type: "product", id: 102, barcode: "6901939620763", name: "可口可乐（330ml）", subtitle: "碳酸饮料", riskLevel: "unknown" },
  { type: "product", id: 103, barcode: "6902083886455", name: "奥利奥夹心饼干", subtitle: "饼干", riskLevel: "t2", highRiskCount: 1 },
];

// ── 真实 API（后端就绪后取消注释，删除 mock 分支）────────────────
// export async function fetchSearch(
//   keyword: string,
//   _type: FilterType = "all",
// ): Promise<SearchResultItem[]> {
//   return new Promise((resolve, reject) => {
//     uni.request({
//       url: `${BASE_URL}/api/search`,
//       method: "GET",
//       data: { q: keyword },
//       success(res) {
//         if (res.statusCode === 200) {
//           resolve(res.data as SearchResultItem[]);
//         } else {
//           reject(new Error(`Unexpected status: ${res.statusCode}`));
//         }
//       },
//       fail(err) {
//         reject(new Error(err.errMsg ?? "Network request failed"));
//       },
//     });
//   });
// }

/** Mock 实现：关键词匹配 name 字段，忽略大小写 */
export async function fetchSearch(
  keyword: string,
  _type: FilterType = "all",
): Promise<SearchResultItem[]> {
  await new Promise((r) => setTimeout(r, 300)); // 模拟网络延迟
  const kw = keyword.trim().toLowerCase();
  if (!kw) return [];
  return MOCK_ITEMS.filter((item) => item.name.toLowerCase().includes(kw));
}
