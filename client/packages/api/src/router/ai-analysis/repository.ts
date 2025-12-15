import { and, eq } from "@acme/db";
import { BaseRepository } from "@acme/db/baseRepository";
import { db } from "@acme/db/client";
import { FoodAiAnalysisTable } from "@acme/db/schema";

class FoodAiAnalysisRepository extends BaseRepository<
  typeof FoodAiAnalysisTable,
  "id"
> {
  constructor() {
    super(db, FoodAiAnalysisTable, "id");
  }

  public async fetchDetailByFoodId(foodId: number) {
    return this.db.query.FoodAiAnalysisTable.findFirst({
      where: and(eq(FoodAiAnalysisTable.food_id, foodId)),
    });
  }
}
export const foodAiAnalysisRepository = new FoodAiAnalysisRepository();
