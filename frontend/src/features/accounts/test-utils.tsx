import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import i18n from "@/i18n";
import { NO_ACCOUNT_COLORS } from "@/features/accounts/account-colors";
import { ProvidersList, type ProvidersListProps } from "@/features/accounts/components/providers-list";
import { buildProviderGroups, type ProviderSources, type SummaryContext } from "@/features/accounts/provider-summary";

export function summaryContext(overrides: Partial<SummaryContext> = {}): SummaryContext {
  return { t: i18n.t.bind(i18n), quotaDisplay: "both", subscriptionEnds: [], ...overrides };
}

export function providerSources(sources: Partial<ProviderSources>): ProviderSources {
  return { accounts: [], claudeAccounts: [], antigravityAccounts: [], openRouterAccounts: [], modelSources: [], ...sources };
}

/** Renders the Providers table for the given accounts in a router. */
export function renderProvidersList(
  sources: Partial<ProviderSources>,
  props: Partial<Omit<ProvidersListProps, "groups">> = {},
  context: Partial<SummaryContext> = {},
) {
  const groups = buildProviderGroups(providerSources(sources), props.sortMode ?? "status_asc", summaryContext(context));
  return render(
    <MemoryRouter>
      <ProvidersList
        groups={groups}
        activity={undefined}
        activityAvailable={false}
        colors={NO_ACCOUNT_COLORS}
        sortMode="status_asc"
        onSortModeChange={() => {}}
        showResetCreditBadges
        readOnly={false}
        onAdd={() => {}}
        {...props}
      />
    </MemoryRouter>,
  );
}
