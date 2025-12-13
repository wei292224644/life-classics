import { timestamp, uuid } from "drizzle-orm/pg-core";

export const FullyAuditedColumns = {
  createdAt: timestamp({ mode: "date", withTimezone: true })
    .notNull()
    .defaultNow(),
  lastUpdatedAt: timestamp({ mode: "date", withTimezone: true })
    .notNull()
    .defaultNow(),
  createdByUser: uuid().notNull(),
  lastUpdatedByUser: uuid(),
  deletedAt: timestamp({ mode: "date", withTimezone: true }),
};
