import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import {
  AccountCardAction,
  AccountCardNotice,
  AccountCardSurface,
  AccountSelectionSurface,
} from "@/components/account-surfaces";
import { StatusBadge } from "@/components/status-badge";
import { MiniQuotaBar } from "@/components/mini-quota-bar";
import { RoutingPolicyBadge } from "@/features/accounts/components/routing-policy";
import { useTranslation } from "react-i18next";
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

export function OpenRouterTier({ account }: { account: OpenRouterAccount }) {
  const { key, key_error } = account.state;
  return (
    <span title="API key tier reported by OpenRouter; Paid does not identify a commercial subscription plan.">
      {key === null ? "Unknown" : key.is_free_tier ? "Free" : "Paid"}
      {key !== null && key_error && (
        <span className="ml-1 text-amber-600 dark:text-amber-400">· stale</span>
      )}
    </span>
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

function keyAllowancePercent(account: OpenRouterAccount): number | null {
  const { key } = account.state;
  return key && key.limit !== null && key.limit > 0 && key.limit_remaining !== null
    ? (key.limit_remaining / key.limit) * 100
    : null;
}

export function OpenRouterMetrics({
  account,
  detailed = false,
}: {
  account: OpenRouterAccount;
  detailed?: boolean;
}) {
  const { key, credits, key_error, credits_error } = account.state;
  const percent = keyAllowancePercent(account);
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
  // Same row anatomy as the Codex list item: title/subtitle and status, a
  // compact meter, then a one-line muted footer.
  const { key, key_error, credits, credits_error } = account.state;
  const percent = keyAllowancePercent(account);
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
          <p className="truncate text-xs text-muted-foreground">
            OpenRouter | <OpenRouterTier account={account} /> | {account.state.all_models ? "All models" : `${account.state.selections.length} ${account.state.selections.length === 1 ? "model" : "models"}`}
          </p>
        </div>
        <RoutingPolicyBadge policy={account.routingPolicy} />
        <StatusBadge status={openRouterStatus(account)} />
      </div>
      <div className="mt-2 space-y-1">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground">Key allowance</span>
          <span className="tabular-nums font-medium">
            {keyAllowance(account)}
            {key && key_error ? <span className="ml-1 text-amber-600 dark:text-amber-400">· stale</span> : null}
          </span>
        </div>
        {percent !== null && (
          <MiniQuotaBar aria-label="Key allowance remaining" percent={percent} testId="openrouter-list-key-allowance" />
        )}
      </div>
      <div className="mt-2 flex min-w-0 items-center justify-between gap-2 text-[10px] text-muted-foreground">
        <span className="shrink-0 tabular-nums">
          Balance {money(openRouterBalance(account))}
          {credits && credits_error ? " · stale" : ""}
        </span>
        <span className="min-w-0 truncate tabular-nums">Used today {money(key?.usage_daily)}</span>
      </div>
    </AccountSelectionSurface>
  );
}

export function OpenRouterAccountCard({
  account,
}: {
  account: OpenRouterAccount;
}) {
  const { t } = useTranslation();
  const stale = !!(
    account.state.key_error ||
    account.state.credits_error ||
    account.state.catalog_error
  );
  return (
    <AccountCardSurface
      data-testid="openrouter-account-card"
      title={<OpenRouterName account={account} />}
      subtitle={
        <>
          OpenRouter · <OpenRouterTier account={account} /> ·{" "}
          {account.state.all_models
            ? "All models"
            : `${account.state.selections.length} ${account.state.selections.length === 1 ? "model" : "models"} selected`}
        </>
      }
      status={<StatusBadge status={openRouterStatus(account)} />}
      actions={
        <AccountCardAction asChild>
          <Link to={`/accounts?selected=${encodeURIComponent(account.id)}`}>
            <ExternalLink className="h-3 w-3" />
            {t("common.actions.details")}
          </Link>
        </AccountCardAction>
      }
    >
      <OpenRouterMetrics account={account} />
      <AccountCardNotice className="text-muted-foreground">
        <p>
          Used today{" "}
          <span className="font-medium tabular-nums text-foreground">
            {money(account.state.key?.usage_daily)}
          </span>
        </p>
        {stale && (
          <span className="text-amber-600 dark:text-amber-400">
            Monitoring needs attention
          </span>
        )}
      </AccountCardNotice>
    </AccountCardSurface>
  );
}
