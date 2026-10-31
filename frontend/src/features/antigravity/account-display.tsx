import { useTranslation } from "react-i18next";
import { QuotaRow } from "@/features/accounts/components/quota-display";
import type { AntigravityAccount, AntigravityWindow } from "./api";
import { FAMILY_LABELS, WINDOW_LABELS, quotaFamilies } from "./display-values";

export function AntigravityPlan({ account }: { account: AntigravityAccount }) {
  const { t } = useTranslation();
  return <span>{t("antigravity.plan." + account.planType)}</span>;
}

const remaining = (window: AntigravityWindow) => Math.max(0, 100 - window.usedPercent);

/** Every quota window of every model family. */
export function AntigravityQuota({ account }: { account: AntigravityAccount }) {
  const families = quotaFamilies(account);
  if (families.length === 0)
    return <p className="text-xs text-muted-foreground">No quota reported yet</p>;
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
}
