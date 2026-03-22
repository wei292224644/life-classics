export interface IngredientAnalysis {
  id: number;
  analysis_type: string;
  results: unknown;
  level: "t0" | "t1" | "t2" | "t3" | "t4" | "unknown";
}

export interface IngredientDetail {
  id: number;
  name: string;
  alias: string[];
  is_additive: boolean;
  additive_code: string | null;
  who_level: "Group 1" | "Group 2A" | "Group 2B" | "Group 3" | "Group 4" | "Unknown" | null;
  allergen_info: string | null;
  function_type: string | null;
  standard_code: string | null;
  analysis?: IngredientAnalysis;
}

export interface NutritionDetail {
  name: string;
  alias: string[];
  value: string;
  value_unit: "g" | "mg" | "kJ" | "kcal" | "mL";
  reference_type: "PER_100_WEIGHT" | "PER_100_ENERGY" | "PER_SERVING" | "PER_DAY";
  reference_unit: string;
}

export interface AnalysisSummary {
  id: number;
  analysis_type: string;
  results: unknown;
  level: "t0" | "t1" | "t2" | "t3" | "t4" | "unknown";
}

export interface ProductDetail {
  id: number;
  barcode: string;
  name: string;
  manufacturer: string | null;
  origin_place: string | null;
  shelf_life: string | null;
  net_content: string | null;
  image_url_list: string[];
  nutritions: NutritionDetail[];
  ingredients: IngredientDetail[];
  analysis: AnalysisSummary[];
}
