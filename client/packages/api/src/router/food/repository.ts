import { and, eq } from "@acme/db";
import { BaseRepository } from "@acme/db/baseRepository";
import { db } from "@acme/db/client";
import { AnalysisDetailTable, FoodTable } from "@acme/db/schema";

class FoodRepository extends BaseRepository<typeof FoodTable, "id"> {
  constructor() {
    super(db, FoodTable, "id");
  }

  public async fetchDetailByBarcode(barcode: string) {
    return this.db.query.FoodTable.findFirst({
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
