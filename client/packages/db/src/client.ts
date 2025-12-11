// import { sql } from "./db";
// export const db = drizzle({
//   client: sql,
//   schema,
//   casing: "snake_case",
// });

// import { sql } from "@vercel/postgres";
// import { drizzle } from "drizzle-orm/vercel-postgres";

import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";

import { env } from "./env";
import * as schema from "./schema";

console.log("POSTGRES_URL:", env.POSTGRES_URL);
const client = new Pool({
  connectionString: env.POSTGRES_URL,
});

export const db = drizzle({
  client: client,
  schema,
});

// const db = drizzle({
//   client: sql,
//   schema,
// });
// export { db };
