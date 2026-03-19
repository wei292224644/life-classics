/* eslint-disable @typescript-eslint/ban-ts-comment */
/* eslint-disable @typescript-eslint/restrict-plus-operands */
/* eslint-disable @typescript-eslint/no-explicit-any */
import type { InferInsertModel, InferSelectModel, SQL } from "drizzle-orm";
import type { PgColumn, PgTable, PgUpdateSetSource } from "drizzle-orm/pg-core";
import { desc, eq, getTableName } from "drizzle-orm";

import type { DbConnection } from "./client";

export interface QueryCriteria {
  limit?: number;
  offset?: number;
}

export interface IBaseRepository<
  T extends PgTable,
  ID extends keyof T["$inferSelect"],
> {
  findAll(): Promise<InferSelectModel<T>[]>;
  // findAllBy(criteria: QueryCriteria): Promise<InferSelectModel<T>[]>;
  findOne(id: T["$inferSelect"][ID]): Promise<InferSelectModel<T> | null>;
  update(
    id: T["$inferSelect"][ID],
    data: PgUpdateSetSource<T>,
  ): Promise<InferSelectModel<T>>;
  create(data: InferInsertModel<T>[]): Promise<InferSelectModel<T>[]>;
  delete(id: T["$inferSelect"][ID]): Promise<void>;
}

export abstract class BaseRepository<
  PG extends PgTable,
  ID extends keyof PG["$inferSelect"],
> implements IBaseRepository<PG, ID> {
  protected constructor(
    protected readonly db: DbConnection,
    protected readonly schema: PG,
    protected readonly primaryKey: ID & keyof PG,
    protected readonly defaultOrderColumn: keyof PG = "createdAt" as keyof PG,
    protected readonly defaultDeltedKey: keyof PG = "deleted" as keyof PG,
  ) {}

  async create(data: InferInsertModel<PG>[]): Promise<InferSelectModel<PG>[]> {
    const result = await this.db.insert(this.schema).values(data).returning();
    return result as InferSelectModel<PG>[];
  }

  async delete(id: PG["$inferSelect"][ID]): Promise<void> {
    await this.db.delete(this.schema).where(this.getWhereCondition(id));
  }

  async findAll(): Promise<InferSelectModel<PG>[]> {
    //@ts-ignore
    const query = this.db.select().from(this.schema);

    if (this.defaultOrderColumn in this.schema) {
      const orderColumn = this.schema[this.defaultOrderColumn] as PgColumn<
        any,
        any,
        any
      >;
      return query.orderBy(desc(orderColumn));
    }

    return query;
  }

  async findOne(id: PG["$inferSelect"][ID]): Promise<InferSelectModel<PG>> {
    if (!id) {
      throw new Error("id params must be presented!");
    }
    const result = await this.db
      .select()
      //@ts-ignore
      .from(this.schema)
      .where(this.getWhereCondition(id));
    if (result.length === 0) {
      throw new Error("can't find the record with id: " + id);
    }
    return result[0] as InferSelectModel<PG>;
  }

  async update(
    id: PG["$inferSelect"][ID],
    data: PgUpdateSetSource<PG>,
  ): Promise<InferSelectModel<PG>> {
    await this.findOne(id);
    const result = await this.db
      .update(this.schema)
      .set(data)
      .where(this.getWhereCondition(id))
      .returning();
    return result as InferSelectModel<PG>;
  }

  /**
   * Soft delte a record from db
   * @param id primary key id of the PGTable
   * @param userId user who is deleting the record
   */
  async softDelete(id: PG["$inferSelect"][ID], userId: number) {
    this.validateSoftDelteSetup();
    const up: PgUpdateSetSource<PG> = {
      //@ts-expect-error
      deleted: true,
      deletedAt: new Date(),
      deletedByUser: userId,
    };
    await this.db.update(this.schema).set(up).where(this.getWhereCondition(id));
  }

  public getWhereCondition(id: PG["$inferSelect"][ID]): SQL<unknown> {
    return eq(this.schema[this.primaryKey] as PgColumn<any>, id);
  }

  public getDb: () => DbConnection = () => this.db;

  /**
   * get soft delete condition
   */
  public getNonDeletedCondition(): SQL<unknown> {
    this.validateSoftDelteSetup();
    return eq(this.schema[this.defaultDeltedKey] as PgColumn<any>, false);
  }

  /**
   * initialize a softdelete filter for query
   * @param filterOutDeleted
   * @returns
   */
  public initFilter(filterOutDeleted = true) {
    return filterOutDeleted ? [this.getNonDeletedCondition()] : [];
  }

  private validateSoftDelteSetup() {
    if (!(this.defaultDeltedKey in this.schema)) {
      throw new Error(
        `current table[${getTableName(this.schema)}] is not configured with soft delete column`,
      );
    }
  }
}
