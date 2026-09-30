import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createApiKey } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";

import { ApiKeysOverview } from "./api-keys-overview";

describe("ApiKeysOverview", () => {
  it("keeps large partial lifetime cost labels compact and restores their recorded-cost bar", () => {
    renderWithProviders(
      <ApiKeysOverview
        apiKeys={[
          createApiKey({
            name: "Primary key",
            usageSummary: {
              requestCount: 426_943,
              totalTokens: 80_000,
              cachedInputTokens: 12_000,
              totalCostUsd: 44_248.05,
              pricedRequests: 422_859,
              unpricedRequests: 99,
              unmeteredRequests: 3_985,
              coverageUnknown: false,
            },
          }),
        ]}
      />,
    );

    const costPanel = screen.getByTestId("api-keys-overview-cost-panel");
    expect(within(costPanel).getByText("$44,248.05 · 100%")).toBeInTheDocument();
    expect(within(costPanel).getByText("Share of recorded estimated cost")).toBeInTheDocument();
    expect(within(costPanel).getByRole("meter", { name: "Primary key" })).toHaveAttribute("aria-valuenow", "100");
    expect(within(costPanel).getByRole("meter", { name: "Primary key" }).firstElementChild).toHaveStyle({ width: "100%" });
    expect(costPanel).not.toHaveTextContent(/known|incomplete|priced|unmetered/);
    expect(screen.getByTestId("api-keys-overview-stat-lifetime-cost")).toHaveTextContent("$44,248.05");
  });

  it.each([
    { unpricedRequests: 1 },
    { unmeteredRequests: 1 },
    { coverageUnknown: true },
  ])("shows recorded-cost shares across multiple keys with partial coverage (%j)", (coverage) => {
    const usage = {
      requestCount: 10, totalTokens: 1000, cachedInputTokens: 0,
      pricedRequests: 9, unpricedRequests: 0, unmeteredRequests: 0,
      coverageUnknown: false,
    };
    renderWithProviders(
      <ApiKeysOverview apiKeys={[
        createApiKey({ id: "first", name: "First key", usageSummary: { ...usage, totalCostUsd: 30, ...coverage } }),
        createApiKey({ id: "second", name: "Second key", usageSummary: { ...usage, totalCostUsd: 10 } }),
        createApiKey({ id: "unknown", name: "Unknown key", usageSummary: {
          ...usage, totalCostUsd: 0, pricedRequests: 0, unpricedRequests: 10,
        } }),
      ]} />,
    );

    const costPanel = screen.getByTestId("api-keys-overview-cost-panel");
    expect(within(costPanel).getByText("$30.00 · 75%")).toBeInTheDocument();
    expect(within(costPanel).getByText("$10.00 · 25%")).toBeInTheDocument();
    expect(within(costPanel).getByRole("meter", { name: "First key" }).firstElementChild).toHaveStyle({ width: "75%" });
    expect(within(costPanel).getByRole("meter", { name: "Second key" }).firstElementChild).toHaveStyle({ width: "25%" });
    expect(within(costPanel).queryByText("Unknown key")).not.toBeInTheDocument();
    expect(within(costPanel).queryByText(/\$0\.00/)).not.toBeInTheDocument();
  });

  it("does not invent dollar values when all recorded costs are unknown", () => {
    renderWithProviders(
      <ApiKeysOverview apiKeys={[createApiKey({ usageSummary: {
        requestCount: 1, totalTokens: 1000, cachedInputTokens: 0,
        totalCostUsd: 0, pricedRequests: 0, unpricedRequests: 1,
        unmeteredRequests: 0, coverageUnknown: false,
      } })]} />,
    );

    expect(screen.getByTestId("api-keys-overview-stat-lifetime-cost")).toHaveTextContent("Unknown");
    const costPanel = screen.getByTestId("api-keys-overview-cost-panel");
    expect(within(costPanel).queryByRole("meter")).not.toBeInTheDocument();
    expect(costPanel).not.toHaveTextContent(/\$0\.00|100%/);
  });

  it("summarizes the full key set and breaks usage down by metric", () => {
    renderWithProviders(
      <ApiKeysOverview
        apiKeys={[
          createApiKey({
            id: "key_1",
            name: "Primary key",
            keyPrefix: "sk-primary",
            usageSummary: {
              requestCount: 300,
              totalTokens: 80_000,
              cachedInputTokens: 12_000,
              totalCostUsd: 2.5,
              pricedRequests: 300,
              unpricedRequests: 0,
              unmeteredRequests: 0,
              coverageUnknown: false,
            },
          }),
          createApiKey({
            id: "key_2",
            name: "Secondary key",
            keyPrefix: "sk-secondary",
            isActive: false,
            usageSummary: {
              requestCount: 120,
              totalTokens: 20_000,
              cachedInputTokens: 2_000,
              totalCostUsd: 1.0,
              pricedRequests: 120,
              unpricedRequests: 0,
              unmeteredRequests: 0,
              coverageUnknown: false,
            },
          }),
        ]}
      />,
    );

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByTestId("api-keys-overview-stat-api-keys")).toHaveTextContent("2");
    expect(screen.getByTestId("api-keys-overview-stat-active-keys")).toHaveTextContent("1");
    expect(screen.getByTestId("api-keys-overview-stat-used-keys")).toHaveTextContent("2");
    expect(screen.getByTestId("api-keys-overview-stat-lifetime-requests")).toHaveTextContent("420");
    expect(screen.getByTestId("api-keys-overview-stat-lifetime-cost")).toHaveTextContent("$3.50");

    expect(screen.getByText("Lifetime Cost by API Key")).toBeInTheDocument();
    expect(screen.getByText("Lifetime Tokens by API Key")).toBeInTheDocument();

    const costPanel = screen.getByTestId("api-keys-overview-cost-panel");
    expect(within(costPanel).getByText("Primary key")).toBeInTheDocument();
    expect(within(costPanel).getByText("Secondary key")).toBeInTheDocument();
  });
});
