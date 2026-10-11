import { get } from "@/lib/api-client";

import { API_KEYS_BASE_PATH } from "@/features/api-keys/api";
import type { ComparisonProvider } from "@/features/apis/comparison-trends";
import { ApiKeysTrendsResponseSchema, ApiKeyTrendsResponseSchema, ApiKeyUsage7DayResponseSchema } from "@/features/apis/schemas";

export function getApiKeysTrends(provider: ComparisonProvider) {
  const query = provider === "all" ? "" : `?provider=${provider}`;
  return get(`${API_KEYS_BASE_PATH}/trends${query}`, ApiKeysTrendsResponseSchema);
}

export function getApiKeyTrends(keyId: string) {
  return get(
    `${API_KEYS_BASE_PATH}/${encodeURIComponent(keyId)}/trends`,
    ApiKeyTrendsResponseSchema,
  );
}

export function getApiKeyUsage7Day(keyId: string) {
  return get(
    `${API_KEYS_BASE_PATH}/${encodeURIComponent(keyId)}/usage-7d`,
    ApiKeyUsage7DayResponseSchema,
  );
}
