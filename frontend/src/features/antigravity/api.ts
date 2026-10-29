import { z } from "zod";
import { del, get, patch, post } from "@/lib/api-client";

export const QUOTA_FAMILIES = ["gemini", "argon", "claude"] as const;
export type QuotaFamily = (typeof QUOTA_FAMILIES)[number];

const MetadataStateSchema = z.object({
  updated_at: z.string().nullable(),
  error: z.string().nullable(),
  retry_at: z.string().nullable(),
});

const CatalogFamilySchema = z.object({
  id: z.string(),
  display_name: z.string(),
  /** Effort tier to wire model; empty for a standalone model. */
  tiers: z.record(z.string(), z.string()),
  quota_family: z.enum(QUOTA_FAMILIES),
  context_window: z.number().int().positive().nullable(),
  max_output_tokens: z.number().int().positive().nullable(),
  supports_images: z.boolean(),
  supports_thinking: z.boolean(),
});
export type AntigravityCatalogFamily = z.infer<typeof CatalogFamilySchema>;

export const AntigravityAccountSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string(),
  projectId: z.string().nullable(),
  isEnabled: z.boolean(),
  routingPolicy: z.enum(["normal", "burn_first", "preserve"]),
  maxConcurrency: z.number().int().positive().nullable(),
  credentialStatus: z.string(),
  hold: z.enum(["banned", "misconfigured", "location_unsupported"]).nullable(),
  holdReason: z.string().nullable(),
  holdAt: z.string().nullable(),
  expiresAt: z.string(),
  planType: z.enum(["free", "pro", "ultra_5x", "ultra_20x", "unknown"]),
  /** Pro-unit weight for pooled quota display; null when the plan has no known multiplier. */
  quotaWeight: z.number().int().positive().nullable(),
  state: z.object({
    subscription: z
      .object({
        current_tier: z.object({ id: z.string(), name: z.string().nullable() }).nullable(),
        paid_tier: z.object({ id: z.string(), name: z.string().nullable() }).nullable(),
        observed_at: z.string(),
      })
      .nullable(),
    catalog: z.array(CatalogFamilySchema),
    default_model: z.string().nullable(),
    all_models: z.boolean(),
    selections: z.array(z.string()),
    metadata: z.object({
      account: MetadataStateSchema.optional(),
      catalog: MetadataStateSchema.optional(),
      quota: MetadataStateSchema.optional(),
    }),
    verification: z.object({ url: z.string().nullable(), observed_at: z.string() }).nullable(),
  }),
  windows: z.array(
    z.object({
      family: z.enum(QUOTA_FAMILIES),
      window: z.enum(["five_hour", "weekly"]),
      usedPercent: z.number(),
      resetsAt: z.string().nullable(),
      exhausted: z.boolean(),
    }),
  ),
  cooldowns: z.array(z.object({ scope: z.string(), until: z.string(), reason: z.string() })),
});
export type AntigravityAccount = z.infer<typeof AntigravityAccountSchema>;
export type AntigravityWindow = AntigravityAccount["windows"][number];

export type AntigravityUpdate = {
  name?: string;
  isEnabled?: boolean;
  routingPolicy?: "normal" | "burn_first" | "preserve";
  maxConcurrency?: number | null;
  allModels?: boolean;
  selections?: string[];
  clearHold?: boolean;
};

const OAuthStartedSchema = z.object({
  state: z.string(),
  authorizationUrl: z.string(),
  expiresAt: z.string(),
});
export type OAuthStarted = z.infer<typeof OAuthStartedSchema>;

const BuildSchema = z.object({
  sha512: z.string(),
  version: z.string(),
  changelist: z.string(),
  buildId: z.string().nullable(),
  verifiedAt: z.string(),
});
export const VersionStatusSchema = z.object({
  platform: z.string(),
  platforms: z.array(z.string()),
  effective: BuildSchema.nullable(),
  pinnedSha512: z.string().nullable(),
  builds: z.array(BuildSchema),
  lastCheckedAt: z.string().nullable(),
  retryAt: z.string().nullable(),
  error: z.string().nullable(),
});
export type VersionStatus = z.infer<typeof VersionStatusSchema>;
export type VersionUpdate = { platform?: string; pinnedSha512?: string; clearPin?: boolean };

const path = "/api/antigravity-accounts";
const accountPath = (id: string) => path + "/" + encodeURIComponent(id);

export const listAccounts = () => get(path, z.object({ accounts: z.array(AntigravityAccountSchema) }));
export const importAccount = (body: { name: string; credentials: unknown }) =>
  post(path + "/import", AntigravityAccountSchema, { body });
export const startOAuth = (body: { name: string; sourceId?: string }) =>
  post(path + "/oauth/start", OAuthStartedSchema, { body });
export const completeOAuth = (body: { state: string; code: string }) =>
  post(path + "/oauth/complete", AntigravityAccountSchema, { body });
export const updateAccount = (id: string, body: AntigravityUpdate) =>
  patch(accountPath(id), AntigravityAccountSchema, { body });
export const refreshAccount = (id: string) => post(accountPath(id) + "/refresh", AntigravityAccountSchema);
export const reconnectAccount = (id: string, body: { credentials: unknown }) =>
  post(accountPath(id) + "/reconnect", AntigravityAccountSchema, { body });
export const deleteAccount = (id: string) => del(accountPath(id));
export const getVersion = () => get(path + "/version", VersionStatusSchema);
export const updateVersion = (body: VersionUpdate) => patch(path + "/version", VersionStatusSchema, { body });
