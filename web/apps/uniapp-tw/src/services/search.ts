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
  /** 食品：产品图片 URL */
  imageUrl?: string;
  /** 风险等级 t4/t3/t2/t1/t0/unknown */
  riskLevel: string;
  /** 食品：高风险配料数量 */
  highRiskCount?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export async function fetchSearch(
  keyword: string,
  type: FilterType = "all",
  offset = 0,
  limit = 20,
): Promise<PaginatedResponse<SearchResultItem>> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/api/search`,
      method: "GET",
      data: { q: keyword, type, offset, limit },
      success(res: any) {
        if (res.statusCode === 200) {
          resolve(res.data as PaginatedResponse<SearchResultItem>);
        } else {
          reject(new Error(`Unexpected status: ${res.statusCode}`));
        }
      },
      fail(err) {
        reject(new Error(err.errMsg ?? "Network request failed"));
      },
    });
  });
}
