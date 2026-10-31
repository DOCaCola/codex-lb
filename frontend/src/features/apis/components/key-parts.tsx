import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import type { LimitRule } from "@/features/api-keys/schemas";
import {
  KEY_TONE,
  formatLimitAmount,
  limitPercent,
  limitName,
  type KeyState,
  type KeyTone,
} from "@/features/apis/key-summary";
import { cn } from "@/lib/utils";

const BADGE: Record<KeyTone, string> = {
  ok: "bg-emerald-500/15 text-emerald-700 border-emerald-500/20 dark:text-emerald-400",
  warn: "bg-amber-500/15 text-amber-700 border-amber-500/20 dark:text-amber-400",
  bad: "bg-red-500/15 text-red-700 border-red-500/20 dark:text-red-400",
  off: "bg-zinc-500/15 text-zinc-600 border-zinc-500/20 dark:text-zinc-400",
};

export function KeyStateBadge({ state }: { state: KeyState }) {
  const { t } = useTranslation();
  return (
    <Badge variant="outline" className={cn("gap-1.5", BADGE[KEY_TONE[state]])}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {t("apis.state." + state)}
    </Badge>
  );
}

/** Fill bar of an API-key limit rule. */
export function LimitTrack({ percent, color, className }: { percent: number; color?: string; className?: string }) {
  const state = percent >= 100 ? "bg-destructive" : percent >= 80 ? "bg-amber-500" : color ? undefined : "bg-primary";
  return (
    <div className={cn("h-[5px] overflow-hidden rounded-full bg-muted", className)}>
      <div
        className={cn("h-full rounded-full", state)}
        style={{ width: percent + "%", backgroundColor: state ? undefined : color }}
      />
    </div>
  );
}

/** One limit rule: name, current of maximum, and its fill. */
export function KeyLimitMeter({ limit, color }: { limit: LimitRule; color: string | undefined }) {
  const { t } = useTranslation();
  const percent = limitPercent(limit);
  return (
    <div className="min-w-0" data-testid="api-key-limit-meter">
      <div className="mb-1 flex min-w-0 items-baseline justify-between gap-2 text-xs">
        <span className="min-w-0 truncate text-muted-foreground">{limitName(limit, t)}</span>
        <b className={cn("shrink-0 font-semibold tabular-nums", percent >= 100 && "text-destructive")}>
          {formatLimitAmount(limit, limit.currentValue)}
          <span className="font-normal text-muted-foreground"> / {formatLimitAmount(limit, limit.maxValue)}</span>
        </b>
      </div>
      <LimitTrack percent={percent} color={color} />
    </div>
  );
}

/** Cost of a key over equal time buckets, oldest first; a flat line when the key was idle. */
export function KeySparkline({ buckets, color, width = 72, height = 24 }: {
  buckets: number[] | undefined;
  color: string | undefined;
  width?: number;
  height?: number;
}) {
  const max = Math.max(0, ...(buckets ?? []));
  if (!buckets || max === 0) {
    return (
      <svg aria-hidden="true" width={width} height={height} className="shrink-0">
        <line x1="0" x2={width} y1={height - 1} y2={height - 1} stroke="var(--border)" />
      </svg>
    );
  }
  const points = buckets.map((value, index) => [
    (index / (buckets.length - 1)) * width,
    height - 2 - (value / max) * (height - 4),
  ]);
  const line = "M" + points.map((point) => point.join(",")).join("L");
  return (
    <svg aria-hidden="true" width={width} height={height} className="shrink-0">
      <path d={line + "L" + width + "," + height + "L0," + height + "Z"} fill={color} opacity={0.15} />
      <path d={line} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}
