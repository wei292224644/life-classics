import { cn } from "@acme/ui";

export function AIBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "bg-primary/10 text-primary inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold",
        className,
      )}
    >
      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm1.875-10.5h-3.75a.625.625 0 00-.625.625v1.25c0 .345.28.625.625.625h1.25v3.125c0 .345.28.625.625.625h1.25c.345 0 .625-.28.625-.625V8.125a.625.625 0 00-.625-.625z" />
      </svg>
      AI
    </span>
  );
}
