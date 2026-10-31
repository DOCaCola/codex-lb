import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ProviderAccountName } from "@/components/brand/provider-account-name";
import { AccountCardAction, AccountCardSurface } from "@/components/account-surfaces";
import { StatusBadge } from "@/components/status-badge";
import { CardQuotaGrid, QuotaBar, QuotaRow } from "@/features/accounts/components/quota-display";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { normalizeStatus } from "@/utils/account-status";
import { formatQuotaResetLabel } from "@/utils/formatters";
import type { AntigravityAccount, AntigravityWindow } from "./api";
import {
  FAMILY_LABELS,
  WINDOW_LABELS,
  antigravityStatus,
  bindingWindow,
  quotaFamilies,
} from "./display-values";

export function AntigravityName({ account, color }: { account: AntigravityAccount; color?: string }) {
  const blurred = usePrivacyStore((s) => s.blurred);
  return (
    <ProviderAccountName provider="antigravity" color={color}>
      <span className={blurred ? "privacy-blur" : undefined}>{account.name}</span>
    </ProviderAccountName>
  );
}

export function AntigravityPlan({ account }: { account: AntigravityAccount }) {
  const { t } = useTranslation();
  return <span>{t("antigravity.plan." + account.planType)}</span>;
}

const remaining = (window: AntigravityWindow) => Math.max(0, 100 - window.usedPercent);

/**
 * Quota per family. Detailed views list every window; compact views show each family's
 * binding window, the one that decides whether the family can serve.
 */
export function AntigravityQuota({
  account,
  detailed = false,
}: {
  account: AntigravityAccount;
  detailed?: boolean;
}) {
  const families = quotaFamilies(account);
  if (families.length === 0)
    return <p className="text-xs text-muted-foreground">No quota reported yet</p>;
  if (detailed)
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {families.flatMap((family) =>
          account.windows
            .filter((window) => window.family === family)
            .map((window) => (
              <QuotaRow
                key={family + window.window}
                label={FAMILY_LABELS[family] + " " + WINDOW_LABELS[window.window]}
                percent={remaining(window)}
                resetAt={window.resetsAt}
              />
            )),
        )}
      </div>
    );
  const rows = families.flatMap((family) => {
    const window = bindingWindow(account, family);
    return window ? [{ family, window }] : [];
  });
  return (
    <CardQuotaGrid columns={rows.length > 1 ? 2 : 1}>
      {rows.map(({ family, window }) => (
        <QuotaBar
          key={family}
          label={FAMILY_LABELS[family] + " · " + WINDOW_LABELS[window.window]}
          percent={remaining(window)}
          resetLabel={formatQuotaResetLabel(window.resetsAt)}
        />
      ))}
    </CardQuotaGrid>
  );
}

export function AntigravityAccountCard({ account, color }: { account: AntigravityAccount; color?: string }) {
  const { t } = useTranslation();
  return (
    <AccountCardSurface
      data-testid="antigravity-account-card"
      title={<AntigravityName account={account} color={color} />}
      subtitle={<>Antigravity · <AntigravityPlan account={account} /></>}
      status={<StatusBadge status={normalizeStatus(antigravityStatus(account))} />}
      actions={
        <AccountCardAction asChild>
          <Link to={"/providers/" + encodeURIComponent(account.id)}>
            <ExternalLink className="h-3 w-3" />
            {t("common.actions.details")}
          </Link>
        </AccountCardAction>
      }
    >
      <AntigravityQuota account={account} />
    </AccountCardSurface>
  );
}
