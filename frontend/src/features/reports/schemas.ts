import { z } from "zod";

import { ACCOUNT_PROVIDERS } from "@/components/brand/account-provider";

const CostCoverageFields = {
  pricedRequests: z.number().int().nonnegative().optional().default(0),
  unpricedRequests: z.number().int().nonnegative().optional().default(0),
  unmeteredRequests: z.number().int().nonnegative().optional().default(0),
  coverageUnknown: z.boolean().optional().default(false),
};

const DailyReportRowSchema = z.object({
  ...CostCoverageFields,
  date: z.string(),
  requests: z.number(),
  conversations: z.number(),
  inputTokens: z.number(),
  outputTokens: z.number(),
  reasoningTokens: z.number().nullable(),
  cachedInputTokens: z.number(),
  costUsd: z.number(),
  activeAccounts: z.number(),
  cancelledCount: z.number(),
  errorCount: z.number(),
  medianTtftMs: z.number().optional().default(0),
  medianTps: z.number().optional().default(0),
  medianQueueMs: z.number().optional().default(0),
});

const ModelCostEntrySchema = z.object({
  ...CostCoverageFields,
  model: z.string(),
  costUsd: z.number(),
  requests: z.number(),
});

const UseragentCostEntrySchema = z.object({
  ...CostCoverageFields,
  useragent: z.string(),
  costUsd: z.number(),
  requests: z.number(),
});

const AccountIdentityFields = {
  accountId: z.string().nullable(),
  modelSourceId: z.string().nullable(),
  provider: z.enum(ACCOUNT_PROVIDERS).nullable(),
  name: z.string().nullable(),
};

const AccountCostEntrySchema = z.object({
  ...CostCoverageFields,
  ...AccountIdentityFields,
  costUsd: z.number(),
  requests: z.number(),
});

const DailySplitMeasuresFields = {
  ...CostCoverageFields,
  date: z.string(),
  requests: z.number(),
  inputTokens: z.number(),
  cachedInputTokens: z.number(),
  outputTokens: z.number(),
  reasoningTokens: z.number().nullable(),
  costUsd: z.number(),
};

const DailyAccountSplitSchema = z.object({
  ...DailySplitMeasuresFields,
  ...AccountIdentityFields,
});

const DailyModelSplitSchema = z.object({
  ...DailySplitMeasuresFields,
  model: z.string(),
});

const ReportSummarySchema = z.object({
  ...CostCoverageFields,
  totalCostUsd: z.number(),
  totalInputTokens: z.number(),
  totalOutputTokens: z.number(),
  totalReasoningTokens: z.number(),
  reasoningUsageKnownRequests: z.number(),
  totalCachedTokens: z.number(),
  totalRequests: z.number(),
  totalCancelled: z.number(),
  totalErrors: z.number(),
  totalConversations: z.number(),
  activeAccounts: z.number(),
  avgCostPerDay: z.number(),
  avgRequestsPerDay: z.number(),
});

const ReportComparisonPreviousSchema = z.object({
  ...CostCoverageFields,
  totalCostUsd: z.number(),
  totalTokens: z.number(),
  totalRequests: z.number(),
});

const ReportComparisonSchema = z.object({
  canCompare: z.boolean(),
  previous: ReportComparisonPreviousSchema,
});

const ReportAccountOptionSchema = z.object(AccountIdentityFields);

export const ReportsOptionsResponseSchema = z.object({
  models: z.array(z.string()),
  useragents: z.array(z.string()),
  accounts: z.array(ReportAccountOptionSchema),
});

export const ReportsResponseSchema = z.object({
  generatedAt: z.string().optional(),
  speedMetricsAvailable: z.boolean().optional(),
  speedMetricsMaxDays: z.number().optional(),
  summary: ReportSummarySchema,
  comparison: ReportComparisonSchema,
  daily: z.array(DailyReportRowSchema),
  dailyByAccount: z.array(DailyAccountSplitSchema),
  dailyByModel: z.array(DailyModelSplitSchema),
  byModel: z.array(ModelCostEntrySchema),
  byUseragent: z.array(UseragentCostEntrySchema),
  byAccount: z.array(AccountCostEntrySchema),
});

const ThreadIdentityFacetSchema = z.object({
  requests: z.number(),
  requestShare: z.number(),
  unattributedRequestShare: z.number(),
  conversations: z.number(),
  meanAccountsPerConversation: z.number(),
  singleAccountConversationShare: z.number(),
  turns: z.number(),
  accountSwitchRate: z.number(),
  cacheHitRatio: z.number(),
  cacheSampleInputTokens: z.number(),
  threadGroupingApproximate: z.boolean(),
});

export const ThreadIdentityResponseSchema = z.object({
  generatedAt: z.string().optional(),
  available: z.boolean(),
  maxDays: z.number(),
  windowDays: z.number(),
  conversationMinRequests: z.number(),
  switchMaxGapSeconds: z.number(),
  cacheMinInputTokens: z.number(),
  totalRequests: z.number(),
  unkeyedRequestShare: z.number(),
  keyed: ThreadIdentityFacetSchema,
  unkeyed: ThreadIdentityFacetSchema,
});

export type DailyReportRow = z.input<typeof DailyReportRowSchema>;
export type DailyAccountSplit = z.input<typeof DailyAccountSplitSchema>;
export type DailyModelSplit = z.input<typeof DailyModelSplitSchema>;
export type ModelCostEntry = z.input<typeof ModelCostEntrySchema>;
export type UseragentCostEntry = z.input<typeof UseragentCostEntrySchema>;
export type AccountCostEntry = z.input<typeof AccountCostEntrySchema>;
export type ReportAccountOption = z.infer<typeof ReportAccountOptionSchema>;
export type ReportSummary = z.input<typeof ReportSummarySchema>;
export type ReportComparison = z.input<typeof ReportComparisonSchema>;
export type ReportsResponse = z.infer<typeof ReportsResponseSchema>;
export type ThreadIdentityFacet = z.infer<typeof ThreadIdentityFacetSchema>;
export type ThreadIdentityResponse = z.infer<typeof ThreadIdentityResponseSchema>;
