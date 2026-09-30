import { describe, expect, it } from "vitest";

import {
  formatCostCoverageNote,
  formatCoveredCost,
  formatCoveredCostShort,
  isCostCoverageComplete,
} from "./cost-coverage";

describe("cost coverage formatting", () => {
  it("distinguishes no usage, explicit free pricing, and entirely unknown cost", () => {
    expect(formatCoveredCost(0, { pricedRequests: 0 })).toBe("No usage");
    expect(formatCoveredCost(0, { pricedRequests: 1 })).toBe("$0.00");
    expect(formatCoveredCost(0, { unpricedRequests: 1 })).toBe("Unknown");
    expect(formatCoveredCost(0, { unmeteredRequests: 1 })).toBe("Unknown");
    expect(formatCoveredCost(0, { coverageUnknown: true })).toBe("Unknown");
  });

  it("has a compact form and a short note for tight spaces", () => {
    const coverage = { pricedRequests: 442, unmeteredRequests: 23, coverageUnknown: true };
    expect(formatCoveredCostShort(5095.99, coverage)).toBe("$5,095.99");
    expect(formatCostCoverageNote(coverage)).toBe("Known cost only · 23 unmetered · older totals unverified");
    expect(formatCoveredCostShort(12, { pricedRequests: 3 })).toBe("$12.00");
    expect(formatCostCoverageNote({ pricedRequests: 3 })).toBeNull();
    expect(formatCoveredCostShort(0, { unmeteredRequests: 1 })).toBe("Unknown");
  });

  it("keeps a known historical subtotal visible when its coverage is unavailable", () => {
    expect(formatCoveredCost(3.5, { coverageUnknown: true })).toBe("$3.50 known · coverage unavailable");
    expect(formatCoveredCost(3.5, { unpricedRequests: 2, coverageUnknown: true })).toBe(
      "$3.50 known · incomplete (2 unpriced, historical coverage unknown)",
    );
  });

  it("labels a known subtotal and its missing request coverage", () => {
    const coverage = {
      pricedRequests: 2,
      unpricedRequests: 1,
      unmeteredRequests: 1,
      coverageUnknown: true,
    };
    expect(isCostCoverageComplete(coverage)).toBe(false);
    expect(formatCoveredCost(1.25, coverage)).toBe(
      "$1.25 known · incomplete (2 priced, 1 unpriced, 1 unmetered, historical coverage unknown)",
    );
  });
});
