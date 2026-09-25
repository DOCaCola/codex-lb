import { Link } from "react-router-dom";
import {
  AccountCardSurface,
  AccountSelectionSurface,
} from "@/components/account-surfaces";
import { StatusBadge } from "@/components/status-badge";
import { MiniQuotaBar } from "@/components/mini-quota-bar";
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
  account,
  detailed = false,
}: {
  account: ClaudeAccount;
  detailed?: boolean;
}) {
  const windows = account.quota.windows.filter(
    (window) =>
      detailed || window.name === "five_hour" || window.name === "seven_day",
  );
  return (
    <dl className="grid grid-cols-2 gap-3">
      {windows.map((window) => (
        <div key={window.name} className="space-y-1">
          <dt className="text-xs text-muted-foreground">
            {labels[window.name]}
          </dt>
          <dd className="text-sm tabular-nums">
            {window.utilization === null
              ? "Unknown"
              : `${window.utilization}% used`}
            {window.freshness === "stale" && " · stale"}
          </dd>
          {window.utilization !== null && (
            <MiniQuotaBar
              testId={`claude-quota-${window.name}`}
              aria-label={`${labels[window.name]} quota remaining`}
              percent={Math.max(0, 100 - window.utilization)}
            />
          )}
          {detailed && window.resetsAt && (
            <dd className="text-xs text-muted-foreground">
              Resets {new Date(window.resetsAt).toLocaleString()}
            </dd>
          )}
        </div>
      ))}
    </dl>
  );
}

function Heading({ account }: { account: ClaudeAccount }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">
          <ClaudeName account={account} />
        </p>
        <p className="text-xs text-muted-foreground">
          Claude · {account.state.selections.length} models selected
        </p>
      </div>
      <StatusBadge status={normalizeStatus(claudeStatus(account))} />
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
      <Heading account={account} />
      <div className="mt-3.5">
        <ClaudeQuota account={account} />
      </div>
      <div className="mt-3 border-t pt-3">
        <Button asChild variant="ghost" size="sm">
          <Link to={`/accounts?selected=${encodeURIComponent(account.id)}`}>
            Details
          </Link>
        </Button>
      </div>
    </AccountCardSurface>
  );
}
