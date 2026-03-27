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

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

/** 真实 API 调用 */
export async function fetchSearch(
  keyword: string,
  _type: FilterType = "all",
): Promise<SearchResultItem[]> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/api/search`,
      method: "GET",
      data: {
        q: keyword,
        type: _type,
        offset: 0,
        limit: 50,
      },
      success(res: any) {
        if (res.statusCode === 200) {
          const data = res.data as PaginatedResponse<SearchResultItem>;
          resolve(data.items);
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
