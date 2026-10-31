import { useTranslation } from "react-i18next";

import { useAccountSubscriptionEnds } from "@/features/accounts/account-subscriptions";
import type { SummaryContext } from "@/features/accounts/provider-summary";
import { useAccountQuotaDisplayStore } from "@/hooks/use-account-quota-display";

/** Inputs every provider summary depends on besides the account itself. */
export function useSummaryContext(): SummaryContext {
  const { t } = useTranslation();
  const quotaDisplay = useAccountQuotaDisplayStore((s) => s.quotaDisplay);
  const { data: subscriptionEnds } = useAccountSubscriptionEnds();
  return { t, quotaDisplay, subscriptionEnds };
}

