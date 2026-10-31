import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { NO_ACCOUNT_COLORS } from "@/features/accounts/account-colors";
import { summarizeSources, type ProviderSources } from "@/features/accounts/provider-summary";
import { providerSources, summaryContext } from "@/features/accounts/test-utils";
import {
  DashboardAccountCards,
  DashboardAccountList,
  type DashboardAccountActions,
  type DashboardAccountsProps,
} from "@/features/dashboard/components/dashboard-accounts";

export function dashboardSummaries(sources: Partial<ProviderSources>) {
  return summarizeSources(providerSources(sources), summaryContext());
}

/** Renders the dashboard account cards or list for the given accounts in a router. */
export function renderDashboardAccounts(
  sources: Partial<ProviderSources>,
  {
    view = "cards",
    actions = {},
    ...props
  }: { view?: "cards" | "list"; actions?: Partial<DashboardAccountActions> } & Partial<Omit<DashboardAccountsProps, "summaries" | "actions">> = {},
) {
  const Component = view === "cards" ? DashboardAccountCards : DashboardAccountList;
  return render(
    <MemoryRouter>
      <Component
        summaries={dashboardSummaries(sources)}
        colors={NO_ACCOUNT_COLORS}
        activity={undefined}
        activityAvailable={false}
        actions={{ readOnly: false, onResume: () => {}, onResetCredit: () => {}, ...actions }}
        {...props}
      />
    </MemoryRouter>,
  );
}
