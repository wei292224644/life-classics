import type { AnalysisSummary } from "./product";

export interface IngredientDetail {
  id: number;
  name: string;
  alias: string[];
  is_additive: boolean;
  additive_code: string | null;
  who_level: string | null;
  allergen_info: string[];
  function_type: string[];
  standard_code: string | null;
  analyses: AnalysisSummary[];
  related_products: RelatedProductSimple[];
}

export interface RelatedProductSimple {
  id: number;
  name: string;
  barcode: string;
  image_url: string | null;
  category: string | null;
}
