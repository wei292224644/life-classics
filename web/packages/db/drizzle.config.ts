import type { Config } from "drizzle-kit";

const nonPoolingUrl = process.env.POSTGRES_URL ?? "";

export default {
  schema: "./src/schema/index.ts",
  dialect: "postgresql",
  dbCredentials: { url: nonPoolingUrl },
  casing: "snake_case",
} satisfies Config;
