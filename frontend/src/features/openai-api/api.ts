import { z } from "zod";
import { del, get, patch, post } from "@/lib/api-client";

const SelectionSchema = z.object({
  model: z.string(),
});
export type Selection = z.infer<typeof SelectionSchema>;
const CatalogModelSchema = z.object({
  id: z.string(),
  kind: z.enum(["text", "image"]),
  created: z.number().nullable(),
});
export type CatalogModel = z.infer<typeof CatalogModelSchema>;
const CreditSchema = z.object({
  cycleStart: z.string(),
  cycleEnd: z.string(),
  spentUsd: z.number(),
  monthlyCreditUsd: z.number().nullable(),
  remainingUsd: z.number().nullable(),
  exhaustedUntil: z.string().nullable(),
});
export type CreditEstimate = z.infer<typeof CreditSchema>;
const AccountSchema = z.object({
  routingPolicy: z.enum(["normal", "burn_first", "preserve"]),
  id: z.string(),
  name: z.string(),
  isEnabled: z.boolean(),
  state: z.object({
    selections: z.array(SelectionSchema),
    catalog: z.array(CatalogModelSchema),
    catalog_updated_at: z.string().nullable(),
    catalog_error: z.string().nullable(),
    monthly_credit_usd: z.number().nullable(),
    credit_renews_on: z.number().int().nullable(),
  }),
  modelNames: z.record(z.string(), z.string()),
  credit: CreditSchema,
});
export type OpenAIApiAccount = z.infer<typeof AccountSchema>;
export type AccountUpdate = {
  routingPolicy?: "normal" | "burn_first" | "preserve";
  name?: string;
  isEnabled?: boolean;
  apiKey?: string;
  selections?: Selection[];
  /** Null clears the setting. */
  monthlyCreditUsd?: number | null;
  creditRenewsOn?: number | null;
};
const path = "/api/openai-api-accounts";
export const listAccounts = () =>
  get(path, z.object({ accounts: z.array(AccountSchema) }));
export const createAccount = (body: {
  name: string;
  apiKey: string;
  monthlyCreditUsd?: number;
  creditRenewsOn?: number;
}) => post(path, AccountSchema, { body });
export const updateAccount = (id: string, body: AccountUpdate) =>
  patch(`${path}/${encodeURIComponent(id)}`, AccountSchema, { body });
export const refreshAccount = (id: string) =>
  post(`${path}/${encodeURIComponent(id)}/refresh`, AccountSchema);
export const deleteAccount = (id: string) =>
  del(`${path}/${encodeURIComponent(id)}`);
