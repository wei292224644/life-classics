"use client";
export default function DateFormat({ date }: { date: Date | null }) {
  return date?.toString();
}
