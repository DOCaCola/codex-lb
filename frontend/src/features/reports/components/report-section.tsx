import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

/** Card with a title row; actions sit on the same row. */
export function ReportSection({
  title,
  hint,
  actions,
  testId,
  className,
  children,
}: {
  title: string;
  hint?: ReactNode;
  actions?: ReactNode;
  testId?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cn("rounded-xl border bg-card", className)} data-testid={testId} aria-label={title}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 pt-3.5">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
        {actions}
      </div>
      {children}
    </section>
  );
}

export function ReportEmptyState() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-4 py-12 text-center" data-testid="reports-empty">
      <div className="text-sm font-medium text-foreground">{t("reports.empty.title")}</div>
      <div className="text-xs text-muted-foreground">{t("reports.empty.description")}</div>
    </div>
  );
}
