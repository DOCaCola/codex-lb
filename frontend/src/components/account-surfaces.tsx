import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function AccountCardSurface({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      className={cn("card-hover rounded-xl border bg-card p-4", className)}
      {...props}
    />
  );
}

export function AccountSelectionSurface({
  selected,
  className,
  ...props
}: ComponentProps<"button"> & { selected: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(
        "relative min-w-0 w-full rounded-lg px-3 py-2.5 text-left transition-colors",
        selected ? "bg-primary/8 ring-1 ring-primary/25" : "hover:bg-muted/50",
        className,
      )}
      {...props}
    />
  );
}
