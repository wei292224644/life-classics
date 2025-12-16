import { eq } from "@acme/db";
import { BaseRepository } from "@acme/db/baseRepository";
import { db } from "@acme/db/client";
import { IngredientTable } from "@acme/db/schema";

class IngredientRepository extends BaseRepository<typeof IngredientTable, "id"> {
  constructor() {
    super(db, IngredientTable, "id");
  }

  public async fetchDetailById(id: number) {
    return this.db.query.IngredientTable.findFirst({
      where: eq(IngredientTable.id, id),
    });
  }
}

export const ingredientRepository = new IngredientRepository();
