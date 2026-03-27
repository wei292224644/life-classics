import type { AnalysisSummary } from "./product";

export interface IngredientDetail {
  id: number;
  name: string;
  alias: string[];
  description: string | null;
  is_additive: boolean;
  additive_code: string | null;
  standard_code: string | null;
  who_level: string | null;
  allergen_info: string[];
  function_type: string[];
  origin_type: string | null;
  limit_usage: string | null;
  legal_region: string | null;
  cas: string | null;
  applications: string | null;
  notes: string | null;
  safety_info: string | null;
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
