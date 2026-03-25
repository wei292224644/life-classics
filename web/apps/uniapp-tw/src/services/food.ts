import type { ProductDetail } from "../types/product";

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

console.log(BASE_URL);

export class ProductNotFoundError extends Error {
  constructor(barcode: string) {
    super(`Product not found: ${barcode}`);
    this.name = "ProductNotFoundError";
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

export async function fetchProductByBarcode(barcode: string): Promise<ProductDetail> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/api/product`,
      method: "GET",
      data: { barcode },
      success(res) {

        console.log(res);
        if (res.statusCode === 200) {
          resolve(res.data as ProductDetail);
        } else if (res.statusCode === 404) {
          reject(new ProductNotFoundError(barcode));
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
