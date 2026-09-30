import { Link } from "react-router-dom";
import {
  AccountCardSurface,
  AccountSelectionSurface,
} from "@/components/account-surfaces";
import { StatusBadge } from "@/components/status-badge";
import { ExternalLink } from "lucide-react";
import { MiniQuotaRow, QuotaBar, QuotaRow } from "@/features/accounts/components/quota-display";
import { RoutingPolicyBadge } from "@/features/accounts/components/routing-policy";
import { useAccountQuotaDisplayStore } from "@/hooks/use-account-quota-display";
import { formatPercentNullable, formatQuotaResetLabel } from "@/utils/formatters";
import { Button } from "@/components/ui/button";
import { usePrivacyStore } from "@/hooks/use-privacy";
import type { ClaudeAccount } from "./api";
import { normalizeStatus } from "@/utils/account-status";

import { claudeStatus } from "./display-values";

export function ClaudeName({ account }: { account: ClaudeAccount }) {
  const blurred = usePrivacyStore((s) => s.blurred);
  return (
    <span className={blurred ? "privacy-blur" : undefined}>{account.name}</span>
  );
}

const labels = {
  five_hour: "5-hour",
  seven_day: "Weekly",
  seven_day_opus: "Weekly Opus",
  seven_day_sonnet: "Weekly Sonnet",
};
export function ClaudeQuota({
  account, detailed = false, variant = "list",
}: { account: ClaudeAccount; detailed?: boolean; variant?: "card" | "list" }) {
  const quotaDisplay = useAccountQuotaDisplayStore((state) => state.quotaDisplay);
  const windows = account.quota.windows.filter((window) => {
    if (detailed) return true;
    if (window.name !== "five_hour" && window.name !== "seven_day") return false;
    if (variant === "card") return true;
    return quotaDisplay === "both" ||
      (quotaDisplay === "weekly" ? window.name === "seven_day" : window.name === "five_hour");
  });
  return <div className={windows.length > 1 ? "grid grid-cols-1 gap-3 sm:grid-cols-2" : "grid grid-cols-1 gap-3"}>
    {windows.map((window) => {
      const percent = window.utilization === null ? null : Math.max(0, 100 - window.utilization);
      const label = window.name === "five_hour" ? "5h" : labels[window.name];
      return <div key={window.name} className="space-y-1">
        {detailed ? <QuotaRow label={label} percent={percent} resetAt={window.resetsAt} />
          : variant === "card" ? <QuotaBar label={label} percent={percent} resetLabel={formatQuotaResetLabel(window.resetsAt)} />
          : <MiniQuotaRow label={label} percent={percent} resetAt={window.resetsAt} />}
        {(window.freshness !== "fresh" || (window.utilization !== null && window.utilization > 100)) && (
          <p className="text-[10px] text-muted-foreground">
            {window.utilization === null ? "Unknown" : window.utilization > 100 ? `${formatPercentNullable(window.utilization, 1)} used` : null}
            {window.freshness === "stale" && " · stale"}
          </p>
        )}
      </div>;
    })}
  </div>;
}

function Heading({ account, card = false }: { account: ClaudeAccount; card?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className={card ? "truncate text-sm font-semibold leading-tight" : "truncate text-sm font-medium"}>
          <ClaudeName account={account} />
        </p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          Claude | {account.state.all_models ? "All models" : `${account.state.selections.length} ${account.state.selections.length === 1 ? "model" : "models"} selected`}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {/* Like Codex accounts: routing policy shows in the Accounts list, not on dashboard cards. */}
        {card ? null : <RoutingPolicyBadge policy={account.routingPolicy} />}
        <StatusBadge status={normalizeStatus(claudeStatus(account))} />
      </div>
    </div>
  );
}

export function ClaudeListItem({
  account,
  selected,
  onSelect,
}: {
  account: ClaudeAccount;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <AccountSelectionSurface
      selected={selected}
      onClick={() => onSelect(account.id)}
    >
      <Heading account={account} />
      <div className="mt-2">
        <ClaudeQuota account={account} />
      </div>
    </AccountSelectionSurface>
  );
}

export function ClaudeAccountCard({ account }: { account: ClaudeAccount }) {
  return (
    <AccountCardSurface data-testid="claude-account-card">
      <Heading account={account} card />
      <div className="mt-3.5">
        <ClaudeQuota account={account} variant="card" />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t pt-3">
        <Button asChild variant="ghost" size="sm" className="h-7 gap-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground">
          <Link to={`/accounts?selected=${encodeURIComponent(account.id)}`}>
            <ExternalLink className="h-3 w-3" />
            Details
          </Link>
        </Button>
      </div>
    </AccountCardSurface>
  );
}
