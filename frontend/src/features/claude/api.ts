import { z } from "zod";
import { del, get, patch, post } from "@/lib/api-client";

export const SelectionSchema = z.object({
  model: z.string(),
});
export type ClaudeSelection = z.infer<typeof SelectionSchema>;
export const ClaudeAccountSchema = z.object({
  planType: z.enum(["free", "pro", "max", "max_5x", "max_20x", "team", "enterprise", "unknown"]),
  routingPolicy: z.enum(["normal", "burn_first", "preserve"]),
  maxConcurrency: z.number().int().positive().nullable(),
  id: z.string(),
  name: z.string(),
  isEnabled: z.boolean(),
  credentialStatus: z.string(),
  expiresAt: z.string(),
  state: z.object({
    subscription: z.object({
      subscription_type: z.string().nullable(),
      rate_limit_tier: z.string().nullable(),
      source: z.enum(["credential_file", "bootstrap"]),
      observed_at: z.string(),
    }).nullable(),
    subscription_updated_at: z.string().nullable(),
    subscription_error: z.string().nullable(),
    all_models: z.boolean(),
    reasoning_restrictions: z.record(z.string(), z.array(z.string()).min(1)),
    selections: z.array(SelectionSchema),
    catalog: z.array(
      z.object({
        id: z.string(),
        display_name: z.string(),
        max_input_tokens: z.number().int().positive().nullable(),
        max_tokens: z.number().int().positive().nullable(),
        reasoning_levels: z.array(z.string()),
        default_reasoning_level: z.string().nullable(),
      }),
    ),
    catalog_updated_at: z.string().nullable(),
    catalog_error: z.string().nullable(),
    usage_updated_at: z.string().nullable(),
    usage_error: z.string().nullable(),
  }),
  quota: z.object({
    observedAt: z.string().nullable(),
    windows: z.array(
      z.object({
        name: z.enum([
          "five_hour",
          "seven_day",
          "seven_day_opus",
          "seven_day_sonnet",
        ]),
        utilization: z.number().nullable(),
        resetsAt: z.string().nullable(),
        freshness: z.enum(["fresh", "stale", "unknown"]),
        exhausted: z.boolean(),
      }),
    ),
    models: z.array(
      z.object({
        model: z.string(),
        blocked: z.boolean(),
        retryAt: z.string().nullable(),
      }),
    ),
  }),
});
export type ClaudeAccount = z.infer<typeof ClaudeAccountSchema>;
export type ClaudeUpdate = {
  allModels?: boolean;
  reasoningRestrictions?: Record<string, string[]>;
  routingPolicy?: "normal" | "burn_first" | "preserve";
  maxConcurrency?: number | null;
  name?: string;
  isEnabled?: boolean;
  selections?: ClaudeSelection[];
};
const path = "/api/claude-accounts";
const OAuthStartedSchema = z.object({
  state: z.string(),
  authorizationUrl: z.string(),
  expiresAt: z.string(),
});
export type OAuthStarted = z.infer<typeof OAuthStartedSchema>;
export const listAccounts = () =>
  get(path, z.object({ accounts: z.array(ClaudeAccountSchema) }));
export const importAccount = (body: {
  name: string;
  credentials: unknown;
  acknowledgeExclusiveRefresh: true;
}) => post(`${path}/import`, ClaudeAccountSchema, { body });
export const startOAuth = (body: {
  name: string;
  acknowledgeExclusiveRefresh: true;
  sourceId?: string;
}) => post(`${path}/oauth/start`, OAuthStartedSchema, { body });
export const completeOAuth = (body: { state: string; code: string }) =>
  post(`${path}/oauth/complete`, ClaudeAccountSchema, { body });
export const updateAccount = (id: string, body: ClaudeUpdate) =>
  patch(`${path}/${encodeURIComponent(id)}`, ClaudeAccountSchema, { body });
export const refreshAccount = (id: string) =>
  post(`${path}/${encodeURIComponent(id)}/refresh`, ClaudeAccountSchema);
export const deleteAccount = (id: string) =>
  del(`${path}/${encodeURIComponent(id)}`);
export const reconnectAccount = (
  id: string,
  body: { credentials: unknown; acknowledgeExclusiveRefresh: true },
) =>
  post(`${path}/${encodeURIComponent(id)}/reconnect`, ClaudeAccountSchema, {
    body,
  });
