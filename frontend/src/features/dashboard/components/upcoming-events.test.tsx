import { beforeEach, describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { summarizeEntry, type ProviderSummary } from "@/features/accounts/provider-summary";
import { summaryContext } from "@/features/accounts/test-utils";
import { useDashboardPreferencesStore } from "@/hooks/use-dashboard-preferences";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { createAccountSummary } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";

import { UpcomingEventsSection } from "./upcoming-events";

const inHours = (hours: number) => new Date(Date.now() + hours * 3_600_000).toISOString();

/** A rate-limited Codex account whose 5h window resets after the given hours. */
function limited(id: string, hours: number): ProviderSummary {
  return summarizeEntry(
    {
      kind: "codex",
      account: createAccountSummary({
        accountId: id,
        email: `${id}@example.com`,
        displayName: `${id}@example.com`,
        status: "rate_limited",
        usage: { primaryRemainingPercent: 0, secondaryRemainingPercent: 50, monthlyRemainingPercent: null },
        resetAtPrimary: inHours(hours),
        resetAtSecondary: inHours(150),
      }),
    },
    summaryContext(),
  );
}

function renderSection(summaries: ProviderSummary[]) {
  return renderWithProviders(<UpcomingEventsSection summaries={summaries} subscriptionEnds={[]} pools={[]} />);
}

describe("UpcomingEventsSection", () => {
  beforeEach(() => {
    useDashboardPreferencesStore.setState({ upcomingHorizon: "24h" });
    usePrivacyStore.setState({ blurred: false });
  });

  it("says when nothing is scheduled", () => {
    renderSection([]);

    expect(screen.getByText("Nothing scheduled in the next 24 hours.")).toBeInTheDocument();
  });

  it("links the account coming back and blurs its name in privacy mode", () => {
    usePrivacyStore.setState({ blurred: true });
    renderSection([limited("plus-2", 2)]);

    const row = screen.getByTestId("upcoming-event");
    expect(row).toHaveTextContent("back · 5h resets");
    const link = within(row).getByRole("link", { name: "plus-2@example.com" });
    expect(link).toHaveAttribute("href", "/providers/plus-2");
    expect(link).toHaveClass("privacy-blur");
  });

  it("looks a week ahead under day headings and remembers the choice", async () => {
    const user = userEvent.setup();
    renderSection([limited("soon", 2), limited("later", 72)]);

    expect(screen.getAllByTestId("upcoming-event")).toHaveLength(1);
    expect(screen.queryByRole("heading", { level: 3 })).not.toBeInTheDocument();

    await user.click(within(screen.getByRole("group", { name: "Coming up horizon" })).getByRole("button", { name: "7d" }));

    expect(screen.getAllByTestId("upcoming-event")).toHaveLength(2);
    expect(screen.getAllByRole("heading", { level: 3 }).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("2 in the next 7 days")).toBeInTheDocument();
    expect(window.localStorage.getItem("codex-lb-dashboard-upcoming-horizon")).toBe("7d");
  });

  it("shows eight rows until asked for all", async () => {
    const user = userEvent.setup();
    renderSection(Array.from({ length: 10 }, (_, index) => limited(`acc-${index}`, 1 + index)));

    expect(screen.getAllByTestId("upcoming-event")).toHaveLength(8);
    await user.click(screen.getByRole("button", { name: "Show all (10)" }));

    expect(screen.getAllByTestId("upcoming-event")).toHaveLength(10);
  });
});
