import { describe, expect, it } from "vitest";

import type { LimitRule } from "@/features/api-keys/schemas";
import { createApiKey } from "@/test/mocks/factories";

import {
  blockingLimit,
  formatLimitAmount,
  keyHref,
  keyState,
  matchesKeyFilter,
  matchesKeySearch,
  sortKeys,
  WEEK_BUCKETS,
  weeklyUsageByKey,
} from "./key-summary";

const NOW = Date.parse("2026-10-31T12:00:00Z");
const DAY = 86_400_000;

function limit(overrides: Partial<LimitRule>): LimitRule {
  return {
    id: 1,
    limitType: "total_tokens",
    limitWindow: "weekly",
    maxValue: 1000,
    currentValue: 0,
    modelFilter: null,
    resetAt: "2026-11-01T00:00:00Z",
    ...overrides,
  } as LimitRule;
}

describe("keyState", () => {
  it("ranks disabled over expired over limited over expiring", () => {
    const reached = [limit({ currentValue: 1000 })];
    const past = new Date(NOW - DAY).toISOString();
    const soon = new Date(NOW + 3 * DAY).toISOString();

    expect(keyState(createApiKey({ isActive: false, expiresAt: past }), NOW)).toBe("disabled");
    expect(keyState(createApiKey({ expiresAt: past, limits: reached }), NOW)).toBe("expired");
    expect(keyState(createApiKey({ expiresAt: soon, limits: reached }), NOW)).toBe("limited");
    expect(keyState(createApiKey({ expiresAt: soon, limits: [] }), NOW)).toBe("expiring");
  });

  it("treats expiry beyond 14 days as active", () => {
    const later = new Date(NOW + 15 * DAY).toISOString();
    expect(keyState(createApiKey({ expiresAt: later, limits: [] }), NOW)).toBe("active");
  });
});

describe("blockingLimit", () => {
  it("returns the reached rule that resets last", () => {
    const daily = limit({ id: 1, currentValue: 1000, resetAt: "2026-11-01T00:00:00Z" });
    const weekly = limit({ id: 2, currentValue: 2000, resetAt: "2026-11-05T00:00:00Z" });
    const open = limit({ id: 3, currentValue: 10, resetAt: "2026-12-01T00:00:00Z" });

    expect(blockingLimit(createApiKey({ limits: [daily, weekly, open] }))?.id).toBe(2);
    expect(blockingLimit(createApiKey({ limits: [open] }))).toBeNull();
  });
});

describe("filters and search", () => {
  it("groups states into filter segments", () => {
    expect(matchesKeyFilter("expiring", "active")).toBe(true);
    expect(matchesKeyFilter("expiring", "attention")).toBe(true);
    expect(matchesKeyFilter("limited", "active")).toBe(false);
    expect(matchesKeyFilter("expired", "inactive")).toBe(true);
  });

  it("matches name or prefix, case-insensitively", () => {
    const apiKey = createApiKey({ name: "Build bot", keyPrefix: "sk-clb-ab12" });
    expect(matchesKeySearch(apiKey, " build ")).toBe(true);
    expect(matchesKeySearch(apiKey, "AB12")).toBe(true);
    expect(matchesKeySearch(apiKey, "deploy")).toBe(false);
  });
});

describe("formatLimitAmount", () => {
  it("formats cost rules from micro-dollars", () => {
    expect(formatLimitAmount({ limitType: "cost_usd" }, 2_500_000)).toBe("$2.50");
    expect(formatLimitAmount({ limitType: "total_tokens" }, 12_000)).toBe("12K");
  });
});

describe("weeklyUsageByKey", () => {
  it("sums each key's week into six-hour cost buckets and skips deleted keys", () => {
    const weeks = weeklyUsageByKey({
      since: "2026-10-24T12:00:00Z",
      until: "2026-10-31T12:00:00Z",
      series: [
        {
          keyId: "key_1",
          name: "Default key",
          isDeleted: false,
          cost: [
            { t: "2026-10-24T13:00:00Z", v: 1, pricedRequests: 2 },
            { t: "2026-10-31T11:00:00Z", v: 0.5, unpricedRequests: 1 },
          ],
          tokens: [
            { t: "2026-10-24T13:00:00Z", v: 100 },
            { t: "2026-10-31T11:00:00Z", v: 50 },
          ],
        },
        { keyId: null, name: "Deleted", isDeleted: true, cost: [{ t: "2026-10-30T00:00:00Z", v: 9 }], tokens: [] },
      ],
    });

    const week = weeks.get("key_1");
    expect([...weeks.keys()]).toEqual(["key_1"]);
    expect(week?.costUsd).toBe(1.5);
    expect(week?.tokens).toBe(150);
    expect(week?.coverage).toMatchObject({ pricedRequests: 2, unpricedRequests: 1 });
    expect(week?.costBuckets).toHaveLength(WEEK_BUCKETS);
    expect(week?.costBuckets[0]).toBe(1);
    expect(week?.costBuckets[WEEK_BUCKETS - 1]).toBe(0.5);
  });
});

describe("sortKeys", () => {
  const alpha = createApiKey({ id: "a", name: "Alpha", expiresAt: null, lastUsedAt: "2026-10-30T00:00:00Z" });
  const beta = createApiKey({ id: "b", name: "Beta", expiresAt: "2026-11-02T00:00:00Z", lastUsedAt: null });
  const gamma = createApiKey({ id: "c", name: "Gamma", expiresAt: "2026-11-01T00:00:00Z", lastUsedAt: "2026-10-31T00:00:00Z" });

  it("sorts by last use, newest first and never-used last", () => {
    expect(sortKeys([beta, alpha, gamma], "lastUsed", new Map()).map((apiKey) => apiKey.id)).toEqual(["c", "a", "b"]);
  });

  it("sorts by expiry with non-expiring keys last", () => {
    expect(sortKeys([alpha, beta, gamma], "expiry", new Map()).map((apiKey) => apiKey.id)).toEqual(["c", "b", "a"]);
  });
});

describe("keyHref", () => {
  it("links to a key's tabs", () => {
    expect(keyHref("key 1")).toBe("/keys/key%201");
    expect(keyHref("key_1", "settings")).toBe("/keys/key_1/settings");
  });
});
