import { integer, pgEnum, pgTable, text, varchar } from "drizzle-orm/pg-core";

import { FullyAuditedColumns } from "./share-schema";

export const IarcAgentGroupEnum = pgEnum("iarc_agent_group", [
  "1", // 1类致癌物
  "2A", // 2A类致癌物
  "2B", // 2B类致癌物
  "3", // 3类致癌物
  "unknown", // 未知
]);

export const IarcAgentsTable = pgTable("iarc_agents", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  cas_no: varchar("cas_no", { length: 255 }).notNull(),
  agent_name: varchar("agent_name", { length: 255 }).notNull(),
  zh_agent_name: varchar("zh_agent_name", { length: 255 }),
  group: IarcAgentGroupEnum("group").notNull(),
  volume: varchar("volume", { length: 255 }).notNull(),
  volume_publication_year: varchar("volume_publication_year", {
    length: 255,
  }).notNull(),
  evaluation_year: varchar("evaluation_year", { length: 255 }).notNull(),
  additional_information: text("additional_information"),

  ...FullyAuditedColumns,
});

export const IarcAgentLinkTypeEnum = pgEnum("iarc_agent_link_type", [
  "see",
  "see_also",
]);

export const IarcAgentLinkTable = pgTable("iarc_agent_links", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  from_agent_id: integer()
    .references(() => IarcAgentsTable.id)
    .notNull(),
  to_agent_id: integer()
    .references(() => IarcAgentsTable.id)
    .notNull(),
  link_type: IarcAgentLinkTypeEnum("link_type").notNull(),
  ...FullyAuditedColumns,
});

export const IarcCancerSiteTable = pgTable("iarc_cancer_sites", {
  id: integer().generatedAlwaysAsIdentity().primaryKey(),
  name: varchar("name", { length: 255 }).notNull(),
  zh_name: varchar("zh_name", { length: 255 }),
  description: text("description"),

  sufficient_evidence_agents: integer()
    .references(() => IarcAgentsTable.id)
    .array(),
  limited_evidence_agents: integer()
    .references(() => IarcAgentsTable.id)
    .array(),
  ...FullyAuditedColumns,
});
