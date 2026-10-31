import { get } from "@/lib/api-client";
import {
  ReportsResponseSchema,
  ReportsOptionsResponseSchema,
  ThreadIdentityResponseSchema,
} from "./schemas";

export type ReportsParams = {
  startDate?: string;
  endDate?: string;
  accountIds?: readonly string[];
  modelSourceIds?: readonly string[];
  apiKeyIds?: readonly string[];
  models?: readonly string[];
  useragents?: readonly string[];
  timezone?: string;
};

const REPEATED_PARAMS = [
  ["accountIds", "account_id"],
  ["modelSourceIds", "model_source_id"],
  ["apiKeyIds", "api_key_id"],
  ["models", "model"],
  ["useragents", "useragent_group"],
] as const;

function reportQuery(params: ReportsParams): string {
  const query = new URLSearchParams();
  if (params.startDate) query.set("start_date", params.startDate);
  if (params.endDate) query.set("end_date", params.endDate);
  if (params.timezone) query.set("timezone", params.timezone);
  for (const [field, name] of REPEATED_PARAMS) {
    for (const value of params[field] ?? []) {
      query.append(name, value);
    }
  }
  return query.size > 0 ? `?${query.toString()}` : "";
}

export function getReports(params: ReportsParams = {}) {
  return get(`/api/reports${reportQuery(params)}`, ReportsResponseSchema);
}

export function getReportsOptions(params: Omit<ReportsParams, "models" | "useragents"> = {}) {
  return get(`/api/reports/options${reportQuery(params)}`, ReportsOptionsResponseSchema);
}

// Thread identity is deliberately scoped by the date range alone: an account
// or model filter would change what "accounts per conversation" means.
export function getThreadIdentity(
  params: Pick<ReportsParams, "startDate" | "endDate" | "timezone"> = {},
) {
  return get(`/api/reports/thread-identity${reportQuery(params)}`, ThreadIdentityResponseSchema);
}
