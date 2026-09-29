import { z } from "zod";

const ApiKeyTrendPointSchema = z.object({
  t: z.iso.datetime({ offset: true }),
  v: z.number(),
  pricedRequests: z.number().int().nonnegative().optional().default(0),
  unpricedRequests: z.number().int().nonnegative().optional().default(0),
  unmeteredRequests: z.number().int().nonnegative().optional().default(0),
  coverageUnknown: z.boolean().optional().default(false),
});

export const ApiKeyTrendsResponseSchema = z.object({
  keyId: z.string(),
  cost: z.array(ApiKeyTrendPointSchema),
  tokens: z.array(ApiKeyTrendPointSchema),
});

const ApiKeyAccountCostSchema = z.object({
  accountId: z.string().nullable().default(null),
  email: z.string().nullable().default(null),
  costUsd: z.number().default(0),
  pricedRequests: z.number().int().nonnegative().optional().default(0),
  unpricedRequests: z.number().int().nonnegative().optional().default(0),
  unmeteredRequests: z.number().int().nonnegative().optional().default(0),
  isDeleted: z.boolean().default(false),
});

export const ApiKeyUsage7DayResponseSchema = z.object({
  keyId: z.string(),
  totalTokens: z.number().int(),
  totalCostUsd: z.number(),
  pricedRequests: z.number().int().nonnegative().optional().default(0),
  unpricedRequests: z.number().int().nonnegative().optional().default(0),
  unmeteredRequests: z.number().int().nonnegative().optional().default(0),
  totalRequests: z.number().int(),
  cachedInputTokens: z.number().int(),
  accountCosts: z.array(ApiKeyAccountCostSchema).default([]),
});

export type ApiKeyAccountCost = z.infer<typeof ApiKeyAccountCostSchema>;
export type ApiKeyTrendPoint = z.input<typeof ApiKeyTrendPointSchema>;
export type ApiKeyTrendsResponse = z.input<typeof ApiKeyTrendsResponseSchema>;
export type ApiKeyUsage7DayResponse = z.infer<typeof ApiKeyUsage7DayResponseSchema>;
export type ApiKeyUsage7DayInput = z.input<typeof ApiKeyUsage7DayResponseSchema>;
