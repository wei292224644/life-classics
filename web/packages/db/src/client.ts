// import { drizzle } from "drizzle-orm/vercel-postgres";

// import { sql } from "./db";
// import * as schema from "./schema";

// export const db = drizzle({
//   client: sql,
//   schema,
//   casing: "snake_case",
// });

import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";

import { env } from "./env";
import * as schema from "./schema";
import * as relations from "./schema/relations";

const client = new Pool({
  connectionString: env.POSTGRES_URL,
});

export const db = drizzle({
  client: client,
  schema: {
    ...schema,
    ...relations,
  },
  casing: "snake_case",
});

export type DbConnection = typeof db;
