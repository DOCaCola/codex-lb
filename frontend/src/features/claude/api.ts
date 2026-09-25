import { z } from "zod";
import { del, get, patch, post } from "@/lib/api-client";

export const SelectionSchema = z.object({
  model: z.string(),
  contextWindow: z.number().int().positive(),
  maxOutputTokens: z.number().int().positive(),
});
export type ClaudeSelection = z.infer<typeof SelectionSchema>;
export const ClaudeAccountSchema = z.object({
  id: z.string(),
  name: z.string(),
  isEnabled: z.boolean(),
  credentialStatus: z.string(),
  expiresAt: z.string(),
  state: z.object({
    selections: z.array(SelectionSchema),
    catalog: z.array(z.object({ id: z.string(), display_name: z.string() })),
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
