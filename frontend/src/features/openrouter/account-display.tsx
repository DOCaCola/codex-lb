import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import {
  AccountCardSurface,
  AccountSelectionSurface,
} from "@/components/account-surfaces";
import { StatusBadge } from "@/components/status-badge";
import { MiniQuotaBar } from "@/components/mini-quota-bar";
import { Button } from "@/components/ui/button";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { formatDateTimeInline } from "@/utils/formatters";
import type { OpenRouterAccount } from "./api";

import {
  openRouterStatus,
  openRouterBalance,
  money,
  keyAllowance,
} from "./display-values";

export function OpenRouterName({ account }: { account: OpenRouterAccount }) {
  const blurred = usePrivacyStore((s) => s.blurred);
  return (
    <span className={blurred ? "privacy-blur" : undefined}>{account.name}</span>
  );
}

function Metric({
  label,
  value,
  stale = false,
}: {
  label: string;
  value: string | number;
  stale?: boolean;
}) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium tabular-nums">
        {value}
        {stale && (
          <span className="ml-1 text-xs text-amber-600 dark:text-amber-400">
            · stale
          </span>
        )}
      </dd>
    </div>
  );
}

export function OpenRouterMetrics({
  account,
  detailed = false,
}: {
  account: OpenRouterAccount;
  detailed?: boolean;
}) {
  const { key, credits, key_error, credits_error } = account.state;
  const percent =
    key && key.limit !== null && key.limit > 0 && key.limit_remaining !== null
      ? (key.limit_remaining / key.limit) * 100
      : null;
  return (
    <>
      <dl className="grid grid-cols-2 gap-3">
        <Metric
          label="Account balance"
          value={money(openRouterBalance(account))}
          stale={!!credits && !!credits_error}
        />
        <div>
          <Metric
            label="Key allowance left"
            value={keyAllowance(account)}
            stale={!!key && !!key_error}
          />
          {percent !== null && (
            <div className="mt-2">
              <MiniQuotaBar
                aria-label="Key allowance remaining"
                percent={percent}
                testId="openrouter-key-allowance"
              />
            </div>
          )}
        </div>
        {detailed && (
          <>
            <Metric
              label="Used today"
              value={money(key?.usage_daily)}
              stale={!!key && !!key_error}
            />
            <Metric
              label="Free requests left today"
              value={key?.free_model_daily_requests?.remaining ?? "Unknown"}
              stale={!!key && !!key_error}
            />
          </>
        )}
      </dl>
    </>
  );
}

export function OpenRouterFreshness({
  account,
}: {
  account: OpenRouterAccount;
}) {
  const format = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const { state } = account;
  return (
    <div className="space-y-2 text-xs text-muted-foreground">
      {!account.hasManagementKey && (
        <p>
          Add a management key to display account credits. Key allowance is
          separate from balance.
        </p>
      )}
      <p>
        Usage:{" "}
        {state.key_updated_at
          ? formatDateTimeInline(state.key_updated_at, format)
          : "Never"}
        <br />
        Credits:{" "}
        {state.credits_updated_at
          ? formatDateTimeInline(state.credits_updated_at, format)
          : "Never"}
        <br />
        Catalog:{" "}
        {state.catalog_updated_at
          ? formatDateTimeInline(state.catalog_updated_at, format)
          : "Never"}
      </p>
      {[
        ...new Set(
          [state.catalog_error, state.key_error, state.credits_error].filter(
            Boolean,
          ),
        ),
      ].map((message) => (
        <p key={message} role="alert" className="break-words text-destructive">
          {message}
        </p>
      ))}
    </div>
  );
}

export function OpenRouterListItem({
  account,
  selected,
  onSelect,
}: {
  account: OpenRouterAccount;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <AccountSelectionSurface
      selected={selected}
      onClick={() => onSelect(account.id)}
    >
      <div className="flex items-start gap-2.5">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">
            <OpenRouterName account={account} />
          </p>
          <p className="text-xs text-muted-foreground">
            OpenRouter · {account.state.selections.length} models selected
          </p>
        </div>
        <StatusBadge status={openRouterStatus(account)} />
      </div>
      <div className="mt-2">
        <OpenRouterMetrics account={account} />
      </div>
    </AccountSelectionSurface>
  );
}

export function OpenRouterAccountCard({
  account,
}: {
  account: OpenRouterAccount;
}) {
  const stale = !!(
    account.state.key_error ||
    account.state.credits_error ||
    account.state.catalog_error
  );
  return (
    <AccountCardSurface data-testid="openrouter-account-card">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold leading-tight">
            <OpenRouterName account={account} />
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            OpenRouter · {account.state.selections.length} models selected
          </p>
        </div>
        <StatusBadge status={openRouterStatus(account)} />
      </div>
      <div className="mt-3.5">
        <OpenRouterMetrics account={account} />
      </div>
      <div className="mt-3 rounded-lg bg-muted/40 px-2.5 py-2 text-xs text-muted-foreground">
        Used today{" "}
        <span className="font-medium tabular-nums text-foreground">
          {money(account.state.key?.usage_daily)}
        </span>
        {stale && (
          <span className="ml-2 text-amber-600 dark:text-amber-400">
            Monitoring needs attention
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t pt-3">
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="h-7 gap-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground"
        >
          <Link to={`/accounts?selected=${encodeURIComponent(account.id)}`}>
            <ExternalLink className="h-3 w-3" />
            Details
          </Link>
        </Button>
      </div>
    </AccountCardSurface>
  );
}
