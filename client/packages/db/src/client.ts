import { drizzle } from "drizzle-orm/vercel-postgres";

import { sql } from "./db";
import * as schema from "./schema";

export const db = drizzle({
  client: sql,
  schema,
  casing: "snake_case",
});

// import { drizzle } from "drizzle-orm/node-postgres";

// const db: any = drizzle("postgres://admin:123456@localhost:5432/life-classics");

// export { db };
