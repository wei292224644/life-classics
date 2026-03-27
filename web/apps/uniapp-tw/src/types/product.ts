import type { RiskLevel, UnitValue } from "./enums";

export interface NutritionDetail {
  name: string;
  value: string;
  value_unit: UnitValue;
  reference_unit: string;
}

export interface ProductIngredient {
  id: number;
  name: string;
  level: RiskLevel;
  reason: string | null;
}

export interface AnalysisSummary {
  analysis_type: string;
  result: unknown;
  source: string | null;
  level: RiskLevel;
  confidence_score: number;
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
  ingredients: ProductIngredient[];
  analysis: AnalysisSummary[];
}
