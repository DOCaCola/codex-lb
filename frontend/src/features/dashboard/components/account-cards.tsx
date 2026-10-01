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

  const cards = [
    ...accounts.map((account) => (
      <AccountCard
        key={`codex:${account.accountId}`}
        account={account}
        showAccountId={account.isEmailDuplicate === true}
        readOnly={readOnly}
        onAction={onAction}
      />
    )),
    ...claudeAccounts.map((account) => (
      <ClaudeAccountCard key={`claude:${account.id}`} account={account} />
    )),
    ...openRouterAccounts.map((account) => (
      <OpenRouterAccountCard
        key={`openrouter:${account.id}`}
        account={account}
      />
    )),
  ];

  return (
    // Intrinsic equal-height rows on multi-column screens; no cap or inner scroll.
    <div
      data-testid="dashboard-account-cards"
      className="grid gap-4 sm:auto-rows-fr sm:grid-cols-2 lg:grid-cols-3"
    >
      {cards.map((card, index) => (
        <div
          key={card.key}
          className="animate-fade-in-up flex min-w-0"
          style={{ animationDelay: `${index * 75}ms` }}
        >
          {card}
        </div>
      ))}
    </div>
  );
}
