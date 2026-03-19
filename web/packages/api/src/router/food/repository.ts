import { and, eq } from "@acme/db";
import { BaseRepository } from "@acme/db/baseRepository";
import { db } from "@acme/db/client";
import { AnalysisDetailTable, FoodTable } from "@acme/db/schema";

class FoodRepository extends BaseRepository<typeof FoodTable, "id"> {
  constructor() {
    super(db, FoodTable, "id");
  }

  public async fetchDetailByBarcode(barcode: string) {
    const res = await this.db.query.FoodTable.findFirst({
      where: eq(FoodTable.barcode, barcode),
      with: {
        ingredients: {
          with: {
            ingredient: {
              with: {
                analysis: {
                  where: and(
                    eq(AnalysisDetailTable.target_type, "ingredient"),
                    eq(AnalysisDetailTable.analysis_type, "ingredient_summary"),
                  ),
                  columns: {
                    id: true,
                    analysis_type: true,
                    results: true,
                    level: true,
                  },
                },
              },
            },
          },
        },
        analysis: {
          where: eq(AnalysisDetailTable.target_type, "food"),
          columns: {
            id: true,
            target_id: true,
            target_type: true,
            analysis_type: true,
            results: true,
            level: true,
          },
        },
        nutritions: {
          with: {
            nutrition: true,
          },
        },
      },
    });

    if (!res) return res;

    // ------------------------------------------------------------
    // 把 relations 的 many 结果“压扁”为业务更好用的 shape：
    // - ingredient.analysis: Analysis[] -> Analysis | undefined（只取 ingredient_summary）
    // - food.analysis: Analysis[] -> 保留数组，同时派生出 5 个单条字段（供前端直接使用）
    // ------------------------------------------------------------
    const analysis = res.analysis;
    const byType = Object.fromEntries(
      analysis.map((a) => [a.analysis_type, a] as const),
    );

    const ingredients = res.ingredients.map((row) => {
      const ingredient = row.ingredient;
      const first = ingredient.analysis[0];
      return {
        ...ingredient,
        analysis: first,
      };
    });

    return {
      ...res,
      ingredients,
      analysis,
      foodUsageAdviceSummaryAnalysis: byType.usage_advice_summary,
      foodHealthSummaryAnalysis: byType.health_summary,
      foodIngredientRiskSummaryAnalysis: byType.risk_summary,
      foodPregnancySafetyAnalysis: byType.pregnancy_safety,
      foodSafetyRiskSummaryAnalysis: byType.recent_risk_summary,
    };
  }
  public async fetchDetailById(id: number) {
    return this.db.query.FoodTable.findFirst({
      where: eq(FoodTable.id, id),
      with: {
        ingredients: {
          with: {
            ingredient: true,
          },
        },
        analysis: {
          with: {
            food: true,
          },
        },
      },
    });
  }
}

export const foodRepository = new FoodRepository();
