import { Users } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import {
  AccountCard,
  type AccountCardProps,
} from "@/features/dashboard/components/account-card";
import type { AccountSummary } from "@/features/dashboard/schemas";
import type { OpenRouterAccount } from "@/features/openrouter/api";
import { OpenRouterAccountCard } from "@/features/openrouter/account-display";
import type { ClaudeAccount } from "@/features/claude/api";
import { ClaudeAccountCard } from "@/features/claude/account-display";

export type AccountCardsProps = {
  accounts: AccountSummary[];
  openRouterAccounts?: OpenRouterAccount[];
  claudeAccounts?: ClaudeAccount[];
  readOnly?: boolean;
  onAction?: AccountCardProps["onAction"];
};

export function AccountCards({
  accounts,
  openRouterAccounts = [],
  claudeAccounts = [],
  readOnly = false,
  onAction,
}: AccountCardsProps) {
  const { t } = useTranslation();

  if (
    accounts.length === 0 &&
    openRouterAccounts.length === 0 &&
    claudeAccounts.length === 0
  ) {
    return (
      <EmptyState
        icon={Users}
        title={t("dashboard.accounts.emptyTitle")}
        description={t("dashboard.accounts.emptyDescription")}
        action={
          <Button asChild size="sm">
            <Link to="/accounts">{t("dashboard.accounts.emptyAction")}</Link>
          </Button>
        }
      />
    );
  }

  return (
    // Every account card is shown in full: no height cap or inner scrolling.
    <div data-testid="dashboard-account-cards" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {accounts.map((account, index) => (
        <div
          key={account.accountId}
          className="animate-fade-in-up"
          style={{ animationDelay: `${index * 75}ms` }}
        >
          <AccountCard
            account={account}
            showAccountId={account.isEmailDuplicate === true}
            readOnly={readOnly}
            onAction={onAction}
          />
        </div>
      ))}
      {openRouterAccounts.map((account) => (
        <OpenRouterAccountCard key={account.id} account={account} />
      ))}
      {claudeAccounts.map((account) => (
        <ClaudeAccountCard key={account.id} account={account} />
      ))}
    </div>
  );
}
