import { eq } from "@acme/db";
import { BaseRepository } from "@acme/db/baseRepository";
import { db } from "@acme/db/client";
import { FoodTable } from "@acme/db/schema";

class FoodRepository extends BaseRepository<typeof FoodTable, "id"> {
  constructor() {
    super(db, FoodTable, "id");
  }

  public async fetchDetailByBarcode(barcode: string) {
    return this.db.query.FoodTable.findFirst({
      where: eq(FoodTable.barcode, barcode),
      with: {
        foodIngredients: {
          with: {
            ingredient: true,
          },
        },
      },
    });
  }
}

export const foodRepository = new FoodRepository();
