import { and, eq } from "@acme/db";
import { BaseRepository } from "@acme/db/baseRepository";
import { db } from "@acme/db/client";
import { AnalysisDetailTable } from "@acme/db/schema";

import type { AnalysisTargetType, AnalysisType } from "./type";

class AnalysisDetailRepository extends BaseRepository<
  typeof AnalysisDetailTable,
  "id"
> {
  constructor() {
    super(db, AnalysisDetailTable, "id");
  }

  public fetchDetailByTargetId(targetId: number) {
    return this.db.query.AnalysisDetailTable.findMany({
      where: and(eq(AnalysisDetailTable.target_id, targetId)),
    });
  }

  public fetchDetailByTargetIdAndTargetTypeAndAnalysisType(
    targetId: number,
    targetType: AnalysisTargetType,
    analysisType: AnalysisType,
  ) {
    return this.db.query.AnalysisDetailTable.findFirst({
      where: and(
        eq(AnalysisDetailTable.target_id, targetId),
        eq(AnalysisDetailTable.target_type, targetType),
        eq(AnalysisDetailTable.analysis_type, analysisType),
      ),
    });
  }
}
export const analysisDetailRepository = new AnalysisDetailRepository();
