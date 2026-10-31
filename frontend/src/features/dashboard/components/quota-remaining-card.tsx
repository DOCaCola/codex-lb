import { useTranslation } from "react-i18next";

import type { AccountProvider } from "@/components/brand/account-provider";
import { ProviderLogo } from "@/components/brand/provider-account-name";
import type { RemainingItem, SafeLineView } from "@/features/dashboard/utils";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatDateTimeInline, formatResetCountdown } from "@/utils/formatters";

/** One pooled window: the accounts' remaining amounts as ring segments. */
export type RemainingPool = {
  items: RemainingItem[];
  total: number;
  remaining: number;
  /** Even-usage marker; shown only when the window is at risk. */
  safeLine?: SafeLineView | null;
};

export type RemainingCell = { value: number; resetAt: string | null } | { missing: string };

export type RemainingRow = {
  id: string;
  name: string;
  blurName: boolean;
  provider: AccountProvider;
  color: string | undefined;
  fiveHour: RemainingCell;
  weekly: RemainingCell;
};

export type QuotaRemainingCardProps = {
  title: string;
  subtitle: string;
  format: (value: number) => string;
  fiveHour: RemainingPool;
  weekly: RemainingPool;
  rows: RemainingRow[];
  /** Muted notes under the table, for example accounts left out of the pools. */
  notes: string[];
};

const RING_SIZE = 108;
const RING_STROKE = 10;
const SEGMENT_GAP = 1.5;

function QuotaRing({ pool, format, testId }: { pool: RemainingPool; format: (value: number) => string; testId: string }) {
  const { t } = useTranslation();
  const center = RING_SIZE / 2;
  const radius = center - RING_STROKE / 2 - 4;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  const segments = pool.total > 0
    ? pool.items
        .filter((item) => item.value > 0)
        .map((item) => {
          const length = (circumference * Math.min(item.value, pool.total)) / pool.total;
          const segment = { id: item.accountId, color: item.color, length, offset };
          offset += length;
          return segment;
        })
    : [];
  const safeLine = pool.safeLine && pool.safeLine.riskLevel !== "safe" ? pool.safeLine : null;
  const safeAngle = safeLine ? ((100 - safeLine.safePercent) / 100) * 2 * Math.PI - Math.PI / 2 : 0;
  return (
    <svg width={RING_SIZE} height={RING_SIZE} aria-hidden="true" data-testid={testId} className="shrink-0">
      <circle r={radius} cx={center} cy={center} fill="none" stroke="var(--muted)" strokeWidth={RING_STROKE} />
      {segments.map((segment) => (
        <circle
          key={segment.id}
          r={radius}
          cx={center}
          cy={center}
          fill="none"
          stroke={segment.color ?? "var(--muted-foreground)"}
          strokeWidth={RING_STROKE}
          strokeDasharray={Math.max(0, segment.length - SEGMENT_GAP) + " " + circumference}
          strokeDashoffset={-segment.offset}
          transform={"rotate(-90 " + center + " " + center + ")"}
        />
      ))}
      {safeLine ? (
        <line
          data-testid="safe-line-tick"
          x1={center + (radius - RING_STROKE / 2 - 2) * Math.cos(safeAngle)}
          y1={center + (radius - RING_STROKE / 2 - 2) * Math.sin(safeAngle)}
          x2={center + (radius + RING_STROKE / 2 + 2) * Math.cos(safeAngle)}
          y2={center + (radius + RING_STROKE / 2 + 2) * Math.sin(safeAngle)}
          stroke="var(--foreground)"
          strokeWidth={2}
          strokeLinecap="round"
        />
      ) : null}
      <text x="50%" y="48%" textAnchor="middle" className="fill-foreground text-[15px] font-semibold tabular-nums">
        {format(pool.remaining)}
      </text>
      <text x="50%" y="62%" textAnchor="middle" className="fill-muted-foreground text-[10.5px] tabular-nums">
        {t("dashboard.remaining.of", { total: format(pool.total) })}
      </text>
    </svg>
  );
}

function RingFigure({
  label,
  pool,
  format,
  rowCount,
  testId,
}: {
  label: string;
  pool: RemainingPool;
  format: (value: number) => string;
  rowCount: number;
  testId: string;
}) {
  const { t } = useTranslation();
  const percent = pool.total > 0 ? Math.round((pool.remaining / pool.total) * 100) : 0;
  const pooled = pool.items.length;
  return (
    <figure className="m-0 flex flex-col items-center gap-1.5">
      <QuotaRing pool={pool} format={format} testId={testId} />
      <figcaption className="text-center text-xs leading-snug">
        <b className="block font-semibold">{label}</b>
        <span className="tabular-nums text-muted-foreground">
          {pool.total > 0 ? t("dashboard.remaining.percentLeft", { percent }) : t("dashboard.remaining.noData")}
          {pooled < rowCount ? " · " + t("dashboard.remaining.accountsOf", { count: pooled, total: rowCount }) : null}
        </span>
      </figcaption>
    </figure>
  );
}

function Cell({ cell, format }: { cell: RemainingCell; format: (value: number) => string }) {
  const { t } = useTranslation();
  const dateDisplayFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  if ("missing" in cell) {
    return (
      <td className="py-1.5 pl-4 text-right whitespace-nowrap">
        <span className="text-muted-foreground">—</span>
        <span className="block text-[11px] leading-tight text-muted-foreground">{cell.missing}</span>
      </td>
    );
  }
  const countdown = formatResetCountdown(cell.resetAt);
  return (
    <td className="py-1.5 pl-4 text-right whitespace-nowrap">
      <span className={cn("font-semibold tabular-nums", cell.value <= 0 && "text-destructive")}>{format(cell.value)}</span>
      {countdown ? (
        <span
          className="block text-[11px] leading-tight text-muted-foreground tabular-nums"
          title={t("dashboard.remaining.resetsAt", { time: formatDateTimeInline(cell.resetAt, dateDisplayFormat) })}
        >
          {countdown}
        </span>
      ) : null}
    </td>
  );
}

/** Remaining quota of one provider: the pooled 5-hour and weekly rings beside a per-account table. */
export function QuotaRemainingCard({ title, subtitle, format, fiveHour, weekly, rows, notes }: QuotaRemainingCardProps) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  return (
    <section
      aria-label={title}
      data-testid="quota-remaining-card"
      className="@container/remaining flex min-w-0 flex-col gap-3.5 rounded-xl border bg-card px-[18px] py-4 @min-[44rem]/quota:col-span-2 @min-[74rem]/quota:col-span-1"
    >
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
      </div>
      <div className="grid items-center gap-x-6 gap-y-4 @min-[32rem]/remaining:grid-cols-[auto_minmax(0,1fr)]">
        <div className="flex justify-center gap-3.5">
          <RingFigure label={t("dashboard.remaining.fiveHours")} pool={fiveHour} format={format} rowCount={rows.length} testId="quota-ring-5h" />
          <RingFigure label={t("dashboard.remaining.weekly")} pool={weekly} format={format} rowCount={rows.length} testId="quota-ring-weekly" />
        </div>
        {rows.length > 0 ? (
          <table className="w-full border-collapse text-[12.5px] [&_td]:border-b [&_tbody_tr:last-child_td]:border-b-0">
            <thead>
              <tr className="text-[11.5px] text-muted-foreground">
                <th className="border-b pb-1.5 text-left font-medium">{t("dashboard.remaining.account")}</th>
                <th className="border-b pb-1.5 pl-4 text-right font-medium">{t("dashboard.remaining.fiveHours")}</th>
                <th className="border-b pb-1.5 pl-4 text-right font-medium">{t("dashboard.remaining.weekly")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} data-testid="quota-remaining-row">
                  <td className="max-w-0 py-1.5">
                    <span className="flex min-w-0 items-center gap-2 font-medium">
                      <ProviderLogo provider={row.provider} color={row.color} />
                      <span className={cn("truncate", row.blurName && blurred && "privacy-blur")}>{row.name}</span>
                    </span>
                  </td>
                  <Cell cell={row.fiveHour} format={format} />
                  <Cell cell={row.weekly} format={format} />
                </tr>
              ))}
            </tbody>
            {rows.length > 1 ? (
              <tfoot>
                <tr className="text-muted-foreground">
                  <td className="border-t pt-2">{t("dashboard.remaining.total")}</td>
                  {[fiveHour, weekly].map((pool, index) => (
                    <td key={index} className="border-t pt-2 pl-4 text-right whitespace-nowrap">
                      <b className="font-semibold text-foreground tabular-nums">{format(pool.remaining)}</b>
                      <span className="block text-[11px] leading-tight tabular-nums">
                        {t("dashboard.remaining.of", { total: format(pool.total) })}
                      </span>
                    </td>
                  ))}
                </tr>
              </tfoot>
            ) : null}
          </table>
        ) : (
          <p className="text-xs text-muted-foreground">{t("dashboard.remaining.empty")}</p>
        )}
      </div>
      {notes.map((note) => (
        <p key={note} className="text-[11.5px] text-muted-foreground" data-testid="quota-remaining-note">
          {note}
        </p>
      ))}
    </section>
  );
}

