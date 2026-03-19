import { TRPCError } from "@trpc/server";

import { createMiddleware } from "../trpc";

type IdempotencyKeyFn<TInput> = (params: {
  path: string;
  input: TInput;
}) => string;

interface IdempotencyOptions<TInput> {
  /**
   * 生成幂等键的方法，不同接口可以自定义，避免相互影响
   */
  key: IdempotencyKeyFn<TInput>;
  /**
   * 同一幂等键的拦截窗口（毫秒）
   */
  windowMs?: number;
}

// 简单的内存存储，适用于单实例；如需跨实例，请替换为 Redis 等
const idempotencyWindow = new Map<string, number>();

export const createIdempotencyWindow = <TInput>({
  key,
  windowMs = 60_000,
}: IdempotencyOptions<TInput>) =>
  createMiddleware(async ({ path, input, next }) => {
    if (input == null) {
      // 无输入时跳过幂等拦截，避免读取 undefined
      return next();
    }

    const now = Date.now();
    const composedKey = `${path}::${key({
      path,
      input: input as TInput,
    })}`;

    const expiresAt = idempotencyWindow.get(composedKey);
    if (expiresAt && expiresAt > now) {
      throw new TRPCError({
        code: "TOO_MANY_REQUESTS",
        message: "请求过于频繁，请稍后再试。",
      });
    }

    // 清理过期键
    if (expiresAt && expiresAt <= now) {
      idempotencyWindow.delete(composedKey);
    }

    idempotencyWindow.set(composedKey, now + windowMs);
    return next();
  });
