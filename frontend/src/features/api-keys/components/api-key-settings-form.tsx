import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ChartToggle } from "@/components/chart-toggle";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { DetailCard, DetailParts, SettingRow } from "@/features/accounts/components/provider-detail";
import { AccountMultiSelect } from "@/features/api-keys/components/account-multi-select";
import { ExpiryPicker } from "@/features/api-keys/components/expiry-picker";
import { LimitRulesEditor } from "@/features/api-keys/components/limit-rules-editor";
import { ModelMultiSelect } from "@/features/api-keys/components/model-multi-select";
import { ReasoningEffortsMultiSelect } from "@/features/api-keys/components/reasoning-efforts-multi-select";
import { UsageSectionsMultiSelect } from "@/features/api-keys/components/usage-sections-multi-select";
import { buildSettingsPayload, savedSettings, type KeySettings } from "@/features/api-keys/key-settings";
import type { ApiKey, ApiKeyUpdateRequest, TrafficClass, TransportPolicyOverride } from "@/features/api-keys/schemas";
import { LimitTrack } from "@/features/apis/components/key-parts";
import { formatLimitAmount, limitPercent } from "@/features/apis/key-summary";
import { ModelSourceMultiSelect } from "@/features/model-sources/components/model-source-multi-select";
import { formatQuotaResetLabel } from "@/utils/formatters";

const TRANSPORT_POLICY_FOLLOW_GLOBAL = "follow_global";
const TRANSPORT_POLICY_LABELS = {
  smart: "apiKeys.transport.smart",
  always_http: "apiKeys.transport.alwaysHttp",
  always_websocket: "apiKeys.transport.alwaysWebsocket",
} as const;
const ENFORCED_EFFORTS = ["minimal", "low", "medium", "high", "xhigh", "max", "ultra"] as const;
const SERVICE_TIERS = ["auto", "default", "priority", "flex", "ultrafast"] as const;

export type ApiKeySettingsFormProps = {
  apiKey: ApiKey;
  busy: boolean;
  onSave: (payload: ApiKeyUpdateRequest) => Promise<unknown>;
  onResetUsage: () => Promise<unknown>;
  onRegenerate: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
};

/** Settings tab of an API key: every key option, saved together from one save bar. */
export function ApiKeySettingsForm({
  apiKey,
  busy,
  onSave,
  onResetUsage,
  onRegenerate,
  onToggleActive,
  onDelete,
}: ApiKeySettingsFormProps) {
  const { t } = useTranslation();
  const [edits, setEdits] = useState<Partial<KeySettings>>({});
  // Discard remounts the editors that keep their own row state.
  const [revision, setRevision] = useState(0);
  const [resetOpen, setResetOpen] = useState(false);
  const values: KeySettings = { ...savedSettings(apiKey), ...edits };
  const update = (patch: Partial<KeySettings>) => setEdits((current) => ({ ...current, ...patch }));
  const payload = buildSettingsPayload(apiKey, values);
  const changes = Object.keys(payload).length;
  const nameMissing = values.name.trim() === "";
  const malformedReasoningPolicy = apiKey.allowedReasoningEfforts?.length === 0;
  const accountRestrictionMissing =
    apiKey.accountAssignmentScopeEnabled &&
    apiKey.assignedAccountIds.length === 0 &&
    values.assignedAccountIds.length === 0;
  const sourceRestrictionMissing =
    apiKey.sourceAssignmentScopeEnabled && apiKey.assignedSourceIds.length === 0 && values.assignedSourceIds.length === 0;

  const discard = () => {
    setEdits({});
    setRevision((current) => current + 1);
  };
  const save = async () => {
    try {
      await onSave(payload);
    } catch {
      return;
    }
    setEdits({});
    setRevision((current) => current + 1);
  };

  return (
    <div key={revision} className="flex min-w-0 flex-col gap-4" data-testid="api-key-settings">
      <DetailCard title={t("apiKeys.form.general")}>
        <DetailParts>
          <SettingRow label={t("apiKeys.form.name")} htmlFor="api-key-name">
            <Input
              id="api-key-name"
              value={values.name}
              maxLength={128}
              autoComplete="off"
              aria-invalid={nameMissing}
              onChange={(event) => update({ name: event.target.value })}
              className="max-w-md"
            />
            {nameMissing ? <p className="text-xs text-destructive">{t("apiKeys.validation.nameRequired")}</p> : null}
          </SettingRow>
          <SettingRow label={t("apiKeys.form.expiry")} description={t("apis.settings.expiryHelp")}>
            <ExpiryPicker value={values.expiresAt} onChange={(expiresAt) => update({ expiresAt })} />
          </SettingRow>
          <SettingRow
            label={t("apiKeys.form.trafficClass")}
            description={t("apis.settings.trafficClassHelp")}
            control={
              <ChartToggle<TrafficClass>
                label={t("apiKeys.form.trafficClass")}
                value={values.trafficClass}
                options={[
                  { value: "foreground", label: t("common.traffic.foreground") },
                  { value: "opportunistic", label: t("common.traffic.opportunistic") },
                ]}
                onChange={(trafficClass) => update({ trafficClass })}
              />
            }
          />
        </DetailParts>
      </DetailCard>

      <DetailCard title={t("apis.settings.modelsTitle")}>
        <DetailParts>
          <SettingRow label={t("apiKeys.form.allowedModels")} description={t("apis.settings.allowedModelsHelp")}>
            <ModelMultiSelect value={values.allowedModels} onChange={(allowedModels) => update({ allowedModels })} />
          </SettingRow>
          <SettingRow
            label={t("apiKeys.form.applyToCodexModel")}
            description={t("apis.settings.applyToCodexModelHelp")}
            htmlFor="api-key-apply-to-codex-model"
            control={
              <Switch
                id="api-key-apply-to-codex-model"
                checked={values.applyToCodexModel}
                onCheckedChange={(applyToCodexModel) => update({ applyToCodexModel })}
              />
            }
          />
          <SettingRow
            label={t("apiKeys.form.enforcedModel")}
            description={t("apis.settings.enforcedModelHelp")}
            htmlFor="api-key-enforced-model"
          >
            <Input
              id="api-key-enforced-model"
              value={values.enforcedModel}
              onChange={(event) => update({ enforcedModel: event.target.value })}
              placeholder="e.g. gpt-5.3-codex"
              autoComplete="off"
              className="max-w-md"
            />
          </SettingRow>
          <SettingRow label={t("apiKeys.form.allowedReasoningEfforts")} description={t("apis.settings.effortsHelp")}>
            <ReasoningEffortsMultiSelect
              value={values.allowedReasoningEfforts}
              disabled={values.enforcedReasoningEffort !== "none"}
              onChange={(allowedReasoningEfforts) =>
                update({
                  allowedReasoningEfforts,
                  enforcedReasoningEffort: allowedReasoningEfforts.length > 0 ? "none" : values.enforcedReasoningEffort,
                })
              }
            />
          </SettingRow>
          <SettingRow
            label={t("apiKeys.form.enforcedReasoning")}
            htmlFor="api-key-enforced-effort"
            control={
              <Select
                value={values.enforcedReasoningEffort}
                disabled={values.allowedReasoningEfforts.length > 0 || malformedReasoningPolicy}
                onValueChange={(enforcedReasoningEffort) => update({ enforcedReasoningEffort, allowedReasoningEfforts: [] })}
              >
                <SelectTrigger id="api-key-enforced-effort" size="sm" className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t("common.options.none")}</SelectItem>
                  {ENFORCED_EFFORTS.map((effort) => (
                    <SelectItem key={effort} value={effort}>
                      {t("common.reasoning." + effort)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
          />
          <SettingRow
            label={t("apiKeys.form.enforcedServiceTier")}
            htmlFor="api-key-enforced-service-tier"
            control={
              <Select value={values.enforcedServiceTier} onValueChange={(enforcedServiceTier) => update({ enforcedServiceTier })}>
                <SelectTrigger id="api-key-enforced-service-tier" size="sm" className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t("common.options.none")}</SelectItem>
                  {SERVICE_TIERS.map((tier) => (
                    <SelectItem key={tier} value={tier}>
                      {t("common.serviceTier." + tier)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
          />
        </DetailParts>
      </DetailCard>

      <DetailCard title={t("apis.settings.routingTitle")}>
        <DetailParts>
          <SettingRow label={t("apiKeys.form.assignedAccounts")} description={t("apis.settings.accountsHelp")}>
            <AccountMultiSelect
              value={values.assignedAccountIds}
              onChange={(assignedAccountIds) => update({ assignedAccountIds, clearAccountScope: false })}
            />
            {accountRestrictionMissing ? (
              <MissingRestriction
                id="api-key-clear-account-scope"
                message={t("apiKeys.form.missingAccountRestriction")}
                label={t("apiKeys.form.removeAccountRestriction")}
                checked={values.clearAccountScope}
                onCheckedChange={(clearAccountScope) => update({ clearAccountScope })}
              />
            ) : null}
          </SettingRow>
          <SettingRow label={t("apiKeys.form.assignedModelSources")} description={t("apis.settings.sourcesHelp")}>
            <ModelSourceMultiSelect
              value={values.assignedSourceIds}
              onChange={(assignedSourceIds) => update({ assignedSourceIds, clearSourceScope: false })}
            />
            {sourceRestrictionMissing ? (
              <MissingRestriction
                id="api-key-clear-source-scope"
                message={t("apiKeys.form.missingSourceRestriction")}
                label={t("apiKeys.form.removeSourceRestriction")}
                checked={values.clearSourceScope}
                onCheckedChange={(clearSourceScope) => update({ clearSourceScope })}
              />
            ) : null}
          </SettingRow>
          <SettingRow
            label={t("apiKeys.form.httpClientRouting")}
            description={t("apis.settings.transportHelp")}
            htmlFor="api-key-transport-policy"
            control={
              <Select
                value={values.transportPolicyOverride ?? TRANSPORT_POLICY_FOLLOW_GLOBAL}
                onValueChange={(value) =>
                  update({
                    transportPolicyOverride:
                      value === TRANSPORT_POLICY_FOLLOW_GLOBAL ? null : (value as TransportPolicyOverride),
                  })
                }
              >
                <SelectTrigger id="api-key-transport-policy" size="sm" className="w-56">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TRANSPORT_POLICY_FOLLOW_GLOBAL}>{t("apiKeys.transport.followGlobal")}</SelectItem>
                  {Object.entries(TRANSPORT_POLICY_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {t(label)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
          />
        </DetailParts>
      </DetailCard>

      <DetailCard
        title={t("apiKeys.form.limits")}
        hint={t("apiKeys.limitRules.andHint")}
        action={
          apiKey.limits.length > 0 ? (
            <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => setResetOpen(true)}>
              {t("apis.settings.resetUsage")}
            </Button>
          ) : null
        }
      >
        <div className="space-y-4">
          <LimitRulesEditor rules={values.limits} onChange={(limits) => update({ limits })} />
          {apiKey.limits.length > 0 ? (
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">{t("apiKeys.form.currentUsage")}</div>
              {apiKey.limits.map((limit) => {
                const percent = limitPercent(limit);
                return (
                  <div key={limit.id} className="space-y-1" data-testid="api-key-limit-usage">
                    <div className="flex items-baseline justify-between gap-3 text-xs">
                      <span className="text-muted-foreground">
                        {t("apiKeys.limitTypes." + limit.limitType)} · {t("apiKeys.limitWindows." + limit.limitWindow)}
                        {limit.modelFilter ? " · " + limit.modelFilter : ""}
                      </span>
                      <span className="tabular-nums">
                        {t("apis.limits.ofMax", {
                          current: formatLimitAmount(limit, limit.currentValue),
                          max: formatLimitAmount(limit, limit.maxValue),
                        })}
                        {" · "}
                        {t("apis.limits.resets", { time: formatQuotaResetLabel(limit.resetAt) })}
                      </span>
                    </div>
                    <LimitTrack percent={percent} />
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      </DetailCard>

      <DetailCard title={t("apis.settings.clientUsageTitle")}>
        <SettingRow label={t("apiKeys.form.usageSections")} description={t("apis.settings.usageSectionsHelp")}>
          <UsageSectionsMultiSelect value={values.usageSections} onChange={(usageSections) => update({ usageSections })} />
        </SettingRow>
      </DetailCard>

      <DetailCard title={t("apis.settings.keyTitle")} className="border-destructive/30">
        <DetailParts>
          <SettingRow
            label={t("apis.settings.regenerate")}
            description={t("apis.settings.regenerateHelp")}
            control={
              <Button type="button" size="sm" variant="outline" disabled={busy} onClick={onRegenerate}>
                {t("common.actions.regenerate")}
              </Button>
            }
          />
          <SettingRow
            label={t(apiKey.isActive ? "apis.settings.disable" : "apis.settings.enable")}
            description={t("apis.settings.disableHelp")}
            control={
              <Button type="button" size="sm" variant="outline" disabled={busy} onClick={onToggleActive}>
                {t(apiKey.isActive ? "common.actions.disable" : "common.actions.enable")}
              </Button>
            }
          />
          <SettingRow
            label={t("apis.settings.delete")}
            description={t("apis.settings.deleteHelp")}
            control={
              <Button type="button" size="sm" variant="destructive" disabled={busy} onClick={onDelete}>
                {t("common.actions.delete")}
              </Button>
            }
          />
        </DetailParts>
      </DetailCard>

      {changes > 0 ? (
        <div
          role="region"
          aria-label={t("apis.settings.saveBar")}
          className="sticky bottom-[calc(var(--status-bar-height)+0.75rem)] z-10 flex flex-wrap items-center gap-2 rounded-xl border bg-card px-4 py-2.5 shadow-md"
        >
          <span className="text-sm text-muted-foreground">{t("apis.settings.unsaved", { count: changes })}</span>
          <div className="ml-auto flex gap-2">
            <Button type="button" size="sm" variant="outline" disabled={busy} onClick={discard}>
              {t("apis.settings.discard")}
            </Button>
            <Button type="button" size="sm" disabled={busy || nameMissing} onClick={() => void save()}>
              {t("apis.settings.save")}
            </Button>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={resetOpen}
        title={t("apis.settings.resetUsageTitle")}
        description={t("apis.settings.resetUsageDescription")}
        confirmLabel={t("apis.settings.resetUsage")}
        onOpenChange={setResetOpen}
        onConfirm={() => {
          void onResetUsage()
            .catch(() => null)
            .finally(() => setResetOpen(false));
        }}
      />
    </div>
  );
}

/** Warning that a scoped key lost every assignment, with the opt-in to remove the restriction. */
function MissingRestriction({
  id,
  message,
  label,
  checked,
  onCheckedChange,
}: {
  id: string;
  message: string;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="space-y-1 rounded-md border border-destructive/50 p-2 text-xs">
      <p className="text-muted-foreground">{message}</p>
      <div className="flex items-center gap-2">
        <Checkbox id={id} checked={checked} onCheckedChange={(value) => onCheckedChange(value === true)} />
        <label htmlFor={id} className="cursor-pointer">
          {label}
        </label>
      </div>
    </div>
  );
}
