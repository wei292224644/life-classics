/**
 * 从嵌套对象中提取文本值
 * @param results 对象
 * @param keys 按顺序查找的 key 列表，返回第一个找到的字符串值
 */
export function extractText(results: unknown, ...keys: string[]): string {
  if (!results || typeof results !== "object") return "";
  const r = results as Record<string, unknown>;
  for (const key of keys) {
    if (typeof r[key] === "string") return r[key] as string;
  }
  return "";
}
