import { z } from "zod";
import { del, get, patch, post } from "@/lib/api-client";

const SelectionSchema = z.object({
  model: z.string(),
  contextWindow: z.number().int().positive(),
  maxOutputTokens: z.number().nullable(),
  displayName: z.string().nullable(),
});
export type Selection = z.infer<typeof SelectionSchema>;
const CatalogSchema = z.object({
  id: z.string(),
  name: z.string(),
  context_length: z.number().nullable(),
  image: z
    .object({
      supports_streaming: z.boolean(),
      endpoint_details: z.array(
        z.object({
          provider_name: z.string(),
          pricing: z.array(
            z.object({
              billable: z.string(),
              unit: z.string(),
              cost_usd: z.number(),
              variant: z.string().nullable(),
            }),
          ),
        }),
      ),
    })
    .nullable(),
  pricing: z.object({
    prompt: z.number().nullable(),
    completion: z.number().nullable(),
    input_cache_read: z.number().nullable(),
  }),
  supported_parameters: z.array(z.string()),
  architecture: z.object({
    input_modalities: z.array(z.string()),
    output_modalities: z.array(z.string()),
  }),
  top_provider: z.object({
    context_length: z.number().nullable(),
    max_completion_tokens: z.number().nullable(),
  }),
  reasoning: z
    .object({
      mandatory: z.boolean(),
      supported_efforts: z.array(z.string()).nullable(),
      default_effort: z.string().nullable(),
    })
    .nullable(),
});
const AccountSchema = z.object({
  id: z.string(),
  name: z.string(),
  isEnabled: z.boolean(),
  hasManagementKey: z.boolean(),
  state: z.object({
    selections: z.array(SelectionSchema),
    catalog: z.array(CatalogSchema),
    catalog_updated_at: z.string().nullable(),
    catalog_error: z.string().nullable(),
    key_updated_at: z.string().nullable(),
    key_error: z.string().nullable(),
    credits_updated_at: z.string().nullable(),
    credits_error: z.string().nullable(),
    credits: z
      .object({ total_credits: z.number(), total_usage: z.number() })
      .nullable(),
    key: z
      .object({
        limit: z.number().nullable(),
        limit_remaining: z.number().nullable(),
        limit_reset: z.string().nullable(),
        usage: z.number(),
        usage_daily: z.number(),
        usage_weekly: z.number(),
        usage_monthly: z.number(),
        free_model_daily_requests: z
          .object({
            used: z.number(),
            limit: z.number(),
            remaining: z.number(),
          })
          .nullable(),
      })
      .nullable(),
  }),
});
export type OpenRouterAccount = z.infer<typeof AccountSchema>;
export type AccountUpdate = {
  name?: string;
  isEnabled?: boolean;
  apiKey?: string;
  managementKey?: string | null;
  selections?: Selection[];
};
const path = "/api/openrouter-accounts";
export const listAccounts = () =>
  get(path, z.object({ accounts: z.array(AccountSchema) }));
export const createAccount = (body: {
  name: string;
  apiKey: string;
  managementKey?: string;
}) => post(path, AccountSchema, { body });
export const updateAccount = (id: string, body: AccountUpdate) =>
  patch(`${path}/${encodeURIComponent(id)}`, AccountSchema, { body });
export const refreshAccount = (id: string) =>
  post(`${path}/${encodeURIComponent(id)}/refresh`, AccountSchema);
export const deleteAccount = (id: string) =>
  del(`${path}/${encodeURIComponent(id)}`);
