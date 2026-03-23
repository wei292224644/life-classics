// web/apps/uniapp/src/store/ingredient.ts
import { defineStore } from "pinia"
import { ref } from "vue"
import type { IngredientDetail } from "../types/product"

export const useIngredientStore = defineStore("ingredient", () => {
  /** 当前查看的配料，从产品详情页点入时由上游页面写入 */
  const current = ref<IngredientDetail | null>(null)
  /** 来源产品名称（可选），用于 Header 副标题 */
  const fromProductName = ref<string | null>(null)

  function set(ingredient: IngredientDetail, productName?: string) {
    current.value = ingredient
    fromProductName.value = productName ?? null
  }

  function reset() {
    current.value = null
    fromProductName.value = null
  }

  return { current, fromProductName, set, reset }
})
