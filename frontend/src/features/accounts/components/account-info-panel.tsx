import type { ReactNode } from "react";

export function AccountInfoPanel({ title, rows }: {
  title: string;
  rows: { label: string; value: ReactNode }[];
}) {
  return <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</h3>
    <dl className="space-y-2 text-xs">
      {rows.map(({ label, value }) => <div key={label} className="flex min-w-0 items-center justify-between gap-2">
        <dt className="text-muted-foreground">{label}</dt>
        <dd className="min-w-0 break-words text-right font-medium">{value}</dd>
      </div>)}
    </dl>
  </div>;
}
