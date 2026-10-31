import { hasLimitRuleChanges, normalizeLimitRules } from "@/features/api-keys/components/limit-rules-utils";
import type {
  ApiKey,
  ApiKeyUpdateRequest,
  LimitRuleCreate,
  ReasoningEffortType,
  ServiceTierType,
  TrafficClass,
  TransportPolicyOverride,
} from "@/features/api-keys/schemas";
import { parseDate } from "@/utils/formatters";

/** Editable values of a key; "none" stands for no enforced effort or tier. */
export type KeySettings = {
  name: string;
  expiresAt: Date | null;
  trafficClass: TrafficClass;
  allowedModels: string[];
  applyToCodexModel: boolean;
  enforcedModel: string;
  allowedReasoningEfforts: ReasoningEffortType[];
  enforcedReasoningEffort: string;
  enforcedServiceTier: string;
  assignedAccountIds: string[];
  clearAccountScope: boolean;
  assignedSourceIds: string[];
  clearSourceScope: boolean;
  transportPolicyOverride: TransportPolicyOverride | null;
  limits: LimitRuleCreate[];
  usageSections: string;
};

export function savedSettings(apiKey: ApiKey): KeySettings {
  return {
    name: apiKey.name,
    expiresAt: parseDate(apiKey.expiresAt),
    trafficClass: apiKey.trafficClass,
    allowedModels: apiKey.allowedModels ?? [],
    applyToCodexModel: apiKey.applyToCodexModel,
    enforcedModel: apiKey.enforcedModel ?? "",
    allowedReasoningEfforts: apiKey.allowedReasoningEfforts ?? [],
    enforcedReasoningEffort: apiKey.enforcedReasoningEffort ?? "none",
    enforcedServiceTier: apiKey.enforcedServiceTier ?? "none",
    assignedAccountIds: apiKey.assignedAccountIds,
    clearAccountScope: false,
    assignedSourceIds: apiKey.assignedSourceIds,
    clearSourceScope: false,
    transportPolicyOverride: apiKey.transportPolicyOverride,
    limits: apiKey.limits.map((limit) => ({
      limitType: limit.limitType,
      limitWindow: limit.limitWindow,
      maxValue: limit.maxValue,
      modelFilter: limit.modelFilter,
    })),
    usageSections: apiKey.usageSections,
  };
}

function sameSet(left: string[], right: string[]): boolean {
  const set = new Set(left);
  return left.length === right.length && right.every((value) => set.has(value));
}

/** The PATCH body holding only the fields that differ from the saved key. */
export function buildSettingsPayload(apiKey: ApiKey, values: KeySettings): ApiKeyUpdateRequest {
  const saved = savedSettings(apiKey);
  const payload: ApiKeyUpdateRequest = {};
  if (values.name.trim() !== saved.name) payload.name = values.name.trim();
  if ((values.expiresAt?.getTime() ?? null) !== (saved.expiresAt?.getTime() ?? null)) {
    payload.expiresAt = values.expiresAt?.toISOString() ?? null;
  }
  if (values.trafficClass !== saved.trafficClass) payload.trafficClass = values.trafficClass;
  if (!sameSet(values.allowedModels, saved.allowedModels)) {
    payload.allowedModels = values.allowedModels.length > 0 ? values.allowedModels : null;
  }
  if (values.applyToCodexModel !== saved.applyToCodexModel) payload.applyToCodexModel = values.applyToCodexModel;
  if (values.enforcedModel.trim() !== saved.enforcedModel) payload.enforcedModel = values.enforcedModel.trim() || null;
  if (!sameSet(values.allowedReasoningEfforts, saved.allowedReasoningEfforts)) {
    payload.allowedReasoningEfforts = values.allowedReasoningEfforts.length > 0 ? values.allowedReasoningEfforts : null;
  }
  if (values.enforcedReasoningEffort !== saved.enforcedReasoningEffort) {
    payload.enforcedReasoningEffort =
      values.enforcedReasoningEffort === "none" ? null : (values.enforcedReasoningEffort as ReasoningEffortType);
  }
  if (values.enforcedServiceTier !== saved.enforcedServiceTier) {
    payload.enforcedServiceTier =
      values.enforcedServiceTier === "none" ? null : (values.enforcedServiceTier as ServiceTierType);
  }
  // A scoped key whose accounts or sources were all deleted is deny-all. An
  // empty list disables scoping and would broaden the key to everything, so it
  // is only sent when the operator explicitly removes the restriction.
  if (!sameSet(values.assignedAccountIds, saved.assignedAccountIds) || values.clearAccountScope) {
    payload.assignedAccountIds = values.assignedAccountIds;
  }
  if (!sameSet(values.assignedSourceIds, saved.assignedSourceIds) || values.clearSourceScope) {
    payload.assignedSourceIds = values.assignedSourceIds;
  }
  if (values.transportPolicyOverride !== saved.transportPolicyOverride) {
    payload.transportPolicyOverride = values.transportPolicyOverride;
  }
  if (hasLimitRuleChanges(saved.limits, values.limits)) payload.limits = normalizeLimitRules(values.limits);
  if (values.usageSections !== saved.usageSections) payload.usageSections = values.usageSections;
  return payload;
}
