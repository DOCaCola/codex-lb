import { MoreHorizontal } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { PlanBadge } from "@/components/plan-badge";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ProviderKind } from "@/features/accounts/provider-summary";
import { cn } from "@/lib/utils";
import type { DashboardAccountStatus } from "@/utils/account-status";

export type DetailMenuItem = {
  key: string;
  label: string;
  icon?: ReactNode;
  onSelect: () => void;
  disabled?: boolean;
  destructive?: boolean;
};

/** The ⋯ menu of an account page; destructive items follow a separator. */
export function DetailMenu({ items, label }: { items: DetailMenuItem[]; label: string }) {
  const regular = items.filter((item) => !item.destructive);
  const destructive = items.filter((item) => item.destructive);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" size="icon-sm" variant="outline" aria-label={label} title={label}>
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-52">
        {regular.map((item) => (
          <DropdownMenuItem key={item.key} disabled={item.disabled} onSelect={item.onSelect}>
            {item.icon}
            {item.label}
          </DropdownMenuItem>
        ))}
        {destructive.length > 0 && regular.length > 0 ? <DropdownMenuSeparator /> : null}
        {destructive.map((item) => (
          <DropdownMenuItem key={item.key} variant="destructive" disabled={item.disabled} onSelect={item.onSelect}>
            {item.icon}
            {item.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** A card of an account page: a titled section with optional hint and header action. */
export function DetailCard({
  title,
  hint,
  action,
  children,
  className,
  "data-testid": testId,
}: {
  title: string;
  hint?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <section aria-label={title} data-testid={testId} className={cn("min-w-0 rounded-xl border bg-card shadow-xs", className)}>
      <header className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1 px-4 pt-3.5">
        <h2 className="text-sm font-semibold">{title}</h2>
        {hint ? <span className="min-w-0 text-xs text-muted-foreground">{hint}</span> : null}
        {action ? <div className="ml-auto flex items-center gap-1.5">{action}</div> : null}
      </header>
      <div className="min-w-0 px-4 pt-3 pb-4">{children}</div>
    </section>
  );
}

/** Stacked parts of a card body, separated by rules. */
export function DetailParts({ children }: { children: ReactNode }) {
  return <div className="flex min-w-0 flex-col divide-y [&>*]:py-3 [&>*:first-child]:pt-0 [&>*:last-child]:pb-0">{children}</div>;
}

export type DetailRow = { label: string; value: ReactNode; help?: ReactNode };

/** Label–value rows of a card. */
export function DetailRows({ rows }: { rows: DetailRow[] }) {
  return (
    <dl className="flex min-w-0 flex-col divide-y text-[13px]">
      {rows.map((row) => (
        <div key={row.label} className="flex min-w-0 flex-col gap-0.5 py-2 first:pt-0 last:pb-0">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <dt className="shrink-0 text-muted-foreground">{row.label}</dt>
            <dd className="min-w-0 break-words text-right font-medium">{row.value}</dd>
          </div>
          {row.help ? <p className="text-[11px] text-muted-foreground">{row.help}</p> : null}
        </div>
      ))}
    </dl>
  );
}

/** A setting row: label and optional description on the left, the control on the right. */
export function SettingRow({
  label,
  description,
  htmlFor,
  icon,
  control,
  children,
}: {
  label: string;
  description?: ReactNode;
  htmlFor?: string;
  icon?: ReactNode;
  control?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="min-w-0 space-y-2">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0">
          <label htmlFor={htmlFor} className="flex min-w-0 items-center gap-2 text-[13px] font-medium">
            {icon}
            <span className="min-w-0">{label}</span>
          </label>
          {description ? <div className="mt-0.5 text-[11px] text-muted-foreground">{description}</div> : null}
        </div>
        {control ? <div className="flex shrink-0 items-center gap-2">{control}</div> : null}
      </div>
      {children}
    </div>
  );
}

export type ProviderDetailProps = {
  provider: ProviderKind;
  color?: string;
  /** Name heading with rename and colour controls. */
  name: ReactNode;
  plan?: ReactNode;
  planKey?: string;
  status: DashboardAccountStatus;
  statusTitle?: string;
  /** Badges after the status, for example extra usage. */
  badges?: ReactNode;
  subline?: ReactNode[];
  actions?: ReactNode;
  menu: DetailMenuItem[];
  /** Banner of a limit hit, a pause or a hold. */
  banner?: ReactNode;
  /** Errors of the last action and of provider monitoring. */
  alerts?: ReactNode;
  main: ReactNode;
  side: ReactNode;
  "data-testid"?: string;
};

/** Account page shared by every provider: header with actions, then usage on the left and settings on the right. */
export function ProviderDetail({
  provider,
  color,
  name,
  plan,
  planKey = "unknown",
  status,
  statusTitle,
  badges,
  subline = [],
  actions,
  menu,
  banner,
  alerts,
  main,
  side,
  "data-testid": testId,
}: ProviderDetailProps) {
  const { t } = useTranslation();
  const parts = subline.filter((part) => part !== null && part !== undefined && part !== false && part !== "");
  return (
    <div data-testid={testId} className="animate-fade-in-up flex min-w-0 flex-col gap-4">
      <div className="flex min-w-0 flex-wrap items-start gap-x-3 gap-y-2">
        <span className="mt-0.5 flex">
          <ProviderLogo provider={provider} color={color} size="lg" />
        </span>
        {/* The 16rem basis wraps the actions below the title on narrow screens instead of squeezing the name. */}
        <div className="min-w-0 flex-[1_1_16rem]">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <div className="min-w-0 max-w-full">{name}</div>
            {plan ? <PlanBadge plan={planKey}>{plan}</PlanBadge> : null}
            <StatusBadge status={status} title={statusTitle} />
            {badges}
          </div>
          {parts.length > 0 ? (
            <p className="mt-1 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-muted-foreground">
              {parts.map((part, index) => (
                <Fragment key={index}>
                  {index > 0 ? <span aria-hidden="true">·</span> : null}
                  <span className="min-w-0 break-all">{part}</span>
                </Fragment>
              ))}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {actions}
          <DetailMenu items={menu} label={t("providers.detail.moreActions")} />
        </div>
      </div>
      {banner}
      {alerts}
      <div className="grid min-w-0 grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(19rem,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">{main}</div>
        <div className="flex min-w-0 flex-col gap-4">{side}</div>
      </div>
    </div>
  );
}

/** Banner of an account that routing currently skips. */
export function DetailBanner({
  tone,
  icon,
  children,
  action,
}: {
  tone: "warn" | "bad" | "off";
  icon: ReactNode;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div
      role="status"
      className={cn(
        "flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border px-3.5 py-2.5 text-[13px]",
        tone === "warn" && "border-amber-500/30 bg-amber-500/10",
        tone === "bad" && "border-destructive/30 bg-destructive/5",
        tone === "off" && "bg-muted",
      )}
    >
      <span className="shrink-0 text-muted-foreground [&_svg]:size-4">{icon}</span>
      <div className="min-w-0 flex-1">{children}</div>
      {action}
    </div>
  );
}

