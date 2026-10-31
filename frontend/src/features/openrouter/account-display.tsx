import { MiniQuotaBar } from "@/components/mini-quota-bar";
import type { OpenRouterAccount } from "./api";

import { openRouterBalance, money, keyAllowance } from "./display-values";

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

export function OpenRouterMetrics({ account }: { account: OpenRouterAccount }) {
  const { key, credits, key_error, credits_error } = account.state;
  const percent = keyAllowancePercent(account);
  return (
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
    </dl>
  );
}
