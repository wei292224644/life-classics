import type { RiskLevel } from "./enums";

export interface IngredientAnalysis {
  id: number;
  analysis_type: string;
  results: unknown;
  level: RiskLevel;
}

export interface IngredientDetail {
  id: number;
  name: string;
  alias: string[];
  is_additive: boolean;
  additive_code: string | null;
  who_level: string | null;
  allergen_info: string | null;
  function_type: string | null;
  standard_code: string | null;
  analysis?: IngredientAnalysis;
  related_products: RelatedProductSimple[];
}

export interface RelatedProductSimple {
  id: number;
  name: string;
  barcode: string;
  image_url: string | null;
  category: string | null;
}
