export const UNIT_LABELS: Record<string, string> = {
  g: "克",
  mg: "毫克",
  kJ: "千焦",
  kcal: "千卡",
  mL: "毫升",
};

export function formatNutritionUnit(item: {
  value_unit: string;
  reference_unit?: string;
}): string {
  const unit = UNIT_LABELS[item.value_unit] ?? item.value_unit;
  return item.reference_unit ? `${unit} / ${item.reference_unit}` : unit;
}
