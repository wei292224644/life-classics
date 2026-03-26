import type { IngredientDetail } from "../types/ingredient";

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

export class IngredientNotFoundError extends Error {
  constructor(id: number) {
    super(`Ingredient not found: ${id}`);
    this.name = "IngredientNotFoundError";
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

export async function fetchIngredientById(id: number): Promise<IngredientDetail> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/api/ingredient/${id}`,
      method: "GET",
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data as IngredientDetail);
        } else if (res.statusCode === 404) {
          reject(new IngredientNotFoundError(id));
        } else {
          reject(new NetworkError(`Unexpected status: ${res.statusCode}`));
        }
      },
      fail(err) {
        reject(new NetworkError(err.errMsg ?? "Network request failed"));
      },
    });
  });
}
