import { defineStore } from "pinia";
import { ref } from "vue";
import type { ProductDetail } from "../types/product";
import { fetchProductByBarcode, ProductNotFoundError, NetworkError } from "../services/food";

type LoadingState = "idle" | "loading" | "success" | "not_found" | "error";

export const useProductStore = defineStore("product", () => {
  const product = ref<ProductDetail | null>(null);
  const state = ref<LoadingState>("idle");
  const errorMessage = ref<string>("");

  async function loadProduct(barcode: string) {
    state.value = "loading";
    product.value = null;
    errorMessage.value = "";

    try {
      product.value = await fetchProductByBarcode(barcode);
      state.value = "success";
    } catch (err) {
      if (err instanceof ProductNotFoundError) {
        state.value = "not_found";
      } else if (err instanceof NetworkError) {
        state.value = "error";
        errorMessage.value = err.message;
      } else {
        state.value = "error";
        errorMessage.value = "Unknown error";
      }
    }
  }

  function reset() {
    product.value = null;
    state.value = "idle";
    errorMessage.value = "";
  }

  return { product, state, errorMessage, loadProduct, reset };
});
