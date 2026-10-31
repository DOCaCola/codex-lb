import type { ReportsResponse, ThreadIdentityFacet, ThreadIdentityResponse } from "./schemas";

type DailyRow = ReportsResponse["daily"][number];
type AccountEntry = ReportsResponse["byAccount"][number];

export const NO_COVERAGE_GAPS = {
  pricedRequests: 0,
  unpricedRequests: 0,
  unmeteredRequests: 0,
  coverageUnknown: false,
};

export const EMPTY_REPORT: ReportsResponse = {
  summary: {
    ...NO_COVERAGE_GAPS,
    totalCostUsd: 0,
    totalInputTokens: 0,
    totalOutputTokens: 0,
    totalReasoningTokens: 0,
    reasoningUsageKnownRequests: 0,
    totalCachedTokens: 0,
    totalRequests: 0,
    totalCancelled: 0,
    totalErrors: 0,
    totalConversations: 0,
    activeAccounts: 0,
    avgCostPerDay: 0,
    avgRequestsPerDay: 0,
  },
  comparison: {
    canCompare: false,
    previous: { ...NO_COVERAGE_GAPS, totalCostUsd: 0, totalTokens: 0, totalRequests: 0 },
  },
  daily: [],
  dailyByAccount: [],
  dailyByModel: [],
  byModel: [],
  byUseragent: [],
  byAccount: [],
};

export function dailyRow(date: string, overrides: Partial<DailyRow> = {}): DailyRow {
  return {
    ...NO_COVERAGE_GAPS,
    date,
    requests: 0,
    conversations: 0,
    inputTokens: 0,
    outputTokens: 0,
    reasoningTokens: 0,
    cachedInputTokens: 0,
    costUsd: 0,
    activeAccounts: 0,
    cancelledCount: 0,
    errorCount: 0,
    medianTtftMs: 0,
    medianTps: 0,
    medianQueueMs: 0,
    ...overrides,
  };
}

export function accountEntry(accountId: string, name: string, costUsd: number, requests: number): AccountEntry {
  return { ...NO_COVERAGE_GAPS, accountId, modelSourceId: null, provider: "codex", name, costUsd, requests, pricedRequests: requests };
}

const EMPTY_FACET: ThreadIdentityFacet = {
  requests: 0,
  requestShare: 0,
  unattributedRequestShare: 0,
  conversations: 0,
  meanAccountsPerConversation: 0,
  singleAccountConversationShare: 0,
  turns: 0,
  accountSwitchRate: 0,
  cacheHitRatio: 0,
  cacheSampleInputTokens: 0,
  threadGroupingApproximate: false,
};

export const THREAD_IDENTITY: ThreadIdentityResponse = {
  available: true,
  maxDays: 7,
  windowDays: 7,
  conversationMinRequests: 3,
  switchMaxGapSeconds: 600,
  cacheMinInputTokens: 5000,
  totalRequests: 200,
  unkeyedRequestShare: 0.1,
  keyed: {
    ...EMPTY_FACET,
    requests: 180,
    requestShare: 0.9,
    conversations: 12,
    meanAccountsPerConversation: 1.25,
    singleAccountConversationShare: 0.8,
    turns: 160,
    accountSwitchRate: 0.05,
    cacheHitRatio: 0.92,
    cacheSampleInputTokens: 1_200_000,
  },
  unkeyed: { ...EMPTY_FACET, requests: 20, threadGroupingApproximate: true },
};
