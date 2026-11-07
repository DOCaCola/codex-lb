import type { ReactNode } from "react";

/** Title row of a dashboard section, with an optional hint and controls on the right. */
export function SectionHeader({ title, hint, children }: { title: string; hint?: string; children?: ReactNode }) {
  return (
    <div className="flex min-h-[30px] flex-wrap items-center gap-2.5">
      <h2 className="text-sm font-semibold">{title}</h2>
      {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
      <span className="flex-1" />
      {children}
    </div>
  );
}
