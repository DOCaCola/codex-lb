import type { ReactNode } from "react";

export type PageHeaderProps = {
  title: ReactNode;
  /** Page controls placed right after the title, such as a view switch or range presets. */
  controls?: ReactNode;
  /** Short muted context shown next to the title, such as a summary or status line. */
  meta?: ReactNode;
  /** Page-level actions, aligned to the right edge. */
  actions?: ReactNode;
};

/** The one title row every top-level page starts with. */
export function PageHeader({ title, controls, meta, actions }: PageHeaderProps) {
  return (
    <div className="flex min-h-8 shrink-0 flex-wrap items-center gap-x-4 gap-y-2" data-testid="page-header">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      {controls ? <div className="flex flex-wrap items-center gap-3">{controls}</div> : null}
      <div className="min-w-0 flex-1 text-sm text-muted-foreground">{meta}</div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}
