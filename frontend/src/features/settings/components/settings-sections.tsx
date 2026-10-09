import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { LoadingOverlay } from "@/components/layout/loading-overlay";
import { ApiKeysSection } from "@/features/api-keys/components/api-keys-section";
import { useAccounts } from "@/features/accounts/hooks/use-accounts";
import { useAuthStore, usePermission } from "@/features/auth/hooks/use-auth";
import { CacheIsolationProbeSection } from "@/features/cache-probe/components/cache-isolation-probe-section";
import { useClaudeAccounts } from "@/features/claude/use-claude";
import { FirewallSection } from "@/features/firewall/components/firewall-section";
import { QuotaPlannerSection } from "@/features/quota-planner/components/quota-planner-section";
import { AccessCard } from "@/features/settings/components/access/access-card";
import { AppearanceSettings } from "@/features/settings/components/appearance-settings";
import { BackgroundJobsSettings } from "@/features/settings/components/background-jobs-settings";
import { ConversationArchiveSettings } from "@/features/settings/components/conversation-archive-settings";
import { DataRetentionSettings } from "@/features/settings/components/data-retention-settings";
import { ImportSettings } from "@/features/settings/components/import-settings";
import { ModelCatalogueSettings } from "@/features/settings/components/model-catalogue-settings";
import { QuotaResetWebhookSettings } from "@/features/settings/components/quota-reset-webhook-settings";
import { ResetCreditSettings } from "@/features/settings/components/reset-credit-settings";
import { ResilienceSettings } from "@/features/settings/components/resilience-settings";
import { RoutingSettings } from "@/features/settings/components/routing-settings";
import { SessionBridgeSettings } from "@/features/settings/components/session-bridge-settings";
import { SettingsSection } from "@/features/settings/components/settings-layout";
import { useSettingsSection } from "@/features/settings/use-settings-section";
import { UpstreamProxySettings } from "@/features/settings/components/upstream-proxy-settings";
import { UpstreamTimeoutSettings } from "@/features/settings/components/upstream-timeout-settings";
import { useUpstreamProxyAdmin } from "@/features/settings/hooks/use-settings";
import { buildSettingsUpdateRequest } from "@/features/settings/payload";
import { StickySessionsSection } from "@/features/sticky-sessions/components/sticky-sessions-section";
import { getErrorMessageOrNull } from "@/utils/errors";

// C2-2 routing/overload: a layer move (dashboard <-> inherited) without a
// value change must still reset the routing form's drafts.
const ROUTING_OVERLOAD_PROVENANCE_KEYS = [
  "proxy_overload_isolation_seconds",
  "proxy_account_error_rate_weighting_enabled",
  "proxy_account_inflight_penalty_pct",
  "proxy_account_lease_token_weight",
  "proxy_account_lease_ttl_seconds",
] as const;

export function GeneralSettingsSection() {
  return (
    <SettingsSection section="general">
      <AppearanceSettings />
    </SettingsSection>
  );
}

export function AccountsSettingsSection() {
  const { settings, controlsDisabled, onSave } = useSettingsSection();
  return (
    <SettingsSection section="accounts">
      <ImportSettings settings={settings} busy={controlsDisabled} onSave={onSave} />
      <ResetCreditSettings settings={settings} busy={controlsDisabled} onSave={onSave} />
      <BackgroundJobsSettings settings={settings} busy={controlsDisabled} onSave={onSave} />
    </SettingsSection>
  );
}

export function AccessSettingsSection() {
  const { settings, saving, controlsDisabled, onSave, refetchSettings } = useSettingsSection();
  const canWrite = useAuthStore((state) => state.canWrite);
  // Security-bearing controls (API-key auth policy, firewall) need
  // `security:write`; an Operator sees them read-only instead of a 403.
  const canWriteSecurity = usePermission("security:write");
  // Any signed-in account reaches its own password/two-factor controls: a
  // reverse-proxy account has no password session and still needs to enrol a
  // second factor, which is how it confirms sensitive changes.
  const personalSignIn = useAuthStore(
    (state) => state.passwordManagementEnabled && (state.passwordSessionActive || state.user !== null),
  );

  return (
    <SettingsSection section="access">
      {/* Guest access, password, session and TOTP live inside the Access
          card. It mounts for `write` holders and for any fully signed-in
          account (its own password/TOTP); guests never see it. */}
      {canWrite || personalSignIn ? (
        <AccessCard settings={settings} busy={saving} onSave={onSave} onRefresh={refetchSettings} />
      ) : null}
      {/* API keys are a write-only read on the backend (403 for guests). */}
      {canWrite ? (
        <ApiKeysSection
          apiKeyAuthEnabled={settings.apiKeyAuthEnabled}
          hideUpstreamQuotaFromApiKeys={settings.hideUpstreamQuotaFromApiKeys}
          disabled={controlsDisabled}
          policyControlsDisabled={controlsDisabled || !canWriteSecurity}
          onApiKeyAuthEnabledChange={(enabled) =>
            void onSave(buildSettingsUpdateRequest(settings, { apiKeyAuthEnabled: enabled }))
          }
          onHideUpstreamQuotaFromApiKeysChange={(enabled) =>
            void onSave(buildSettingsUpdateRequest(settings, { hideUpstreamQuotaFromApiKeys: enabled }))
          }
        />
      ) : null}
      <FirewallSection disabled={controlsDisabled || !canWriteSecurity} />
    </SettingsSection>
  );
}

export function RoutingSettingsSection() {
  const { settings, controlsDisabled, onSave } = useSettingsSection();
  const canWrite = useAuthStore((state) => state.canWrite);
  // The probe spends account quota, so it mirrors its backend `ops:write` gate
  // rather than the coarse write alias.
  const canWriteOps = usePermission("ops:write");
  const { accountsQuery } = useAccounts();
  const claudeAccountsQuery = useClaudeAccounts();

  return (
    <SettingsSection section="routing">
      <RoutingSettings
        claudeAccounts={claudeAccountsQuery.data?.accounts}
        key={[
          settings.openaiCacheAffinityMaxAgeSeconds,
          settings.warmupModel,
          settings.limitWarmupModel,
          settings.limitWarmupPrompt,
          settings.limitWarmupExhaustedThresholdPercent,
          settings.limitWarmupIdleThresholdPercent,
          settings.limitWarmupCooldownSeconds,
          settings.limitWarmupStaggeredIdleEnabled,
          settings.proxyAccountResponseCreateLimit,
          settings.proxyAccountResponseCreateLimitOverride,
          settings.proxyAccountStreamLimit,
          settings.proxyAccountStreamLimitOverride,
          settings.proxyAccountStreamRecoveryReserve,
          settings.proxyAccountStreamRecoveryReserveOverride,
          settings.proxyApiKeyFairShareCongestionThresholdPct,
          settings.proxyApiKeyFairShareCongestionThresholdPctOverride,
          settings.proxyOverloadIsolationSeconds,
          settings.proxyAccountErrorRateWeightingEnabled,
          settings.proxyAccountInflightPenaltyPct,
          settings.proxyAccountLeaseTokenWeight,
          settings.proxyAccountLeaseTtlSeconds,
          ...ROUTING_OVERLOAD_PROVENANCE_KEYS.map((name) => settings.provenance?.[name]?.source ?? ""),
        ].join(":")}
        settings={settings}
        accounts={accountsQuery.data ?? []}
        accountsLoading={accountsQuery.isLoading}
        busy={controlsDisabled}
        onSave={onSave}
      />
      <QuotaPlannerSection disabled={controlsDisabled} />
      {/* Sticky sessions are a write-only read on the backend (403 for guests). */}
      {canWrite ? <StickySessionsSection disabled={controlsDisabled} /> : null}
      {/* Next to sticky sessions: both answer "which account served this, and what did it reuse?" */}
      {canWriteOps ? <CacheIsolationProbeSection disabled={controlsDisabled} /> : null}
    </SettingsSection>
  );
}

export function ModelsSettingsSection() {
  const { controlsDisabled } = useSettingsSection();
  return (
    <SettingsSection section="models">
      <ModelCatalogueSettings disabled={controlsDisabled} />
    </SettingsSection>
  );
}

export function UpstreamSettingsSection() {
  const { t } = useTranslation();
  const { settings, controlsDisabled, onSave } = useSettingsSection();
  const canWrite = useAuthStore((state) => state.canWrite);
  const canWriteSecurity = usePermission("security:write");
  // Upstream-proxy administration is a write-only read on the backend (403 for
  // guests). `enabled: false` only stops fetching; cached data from an earlier
  // admin session is still returned, so rendering is gated on `canWrite` too.
  const {
    upstreamProxyQuery,
    createEndpointMutation,
    createPoolMutation,
    addPoolMemberMutation,
    testEndpointMutation,
  } = useUpstreamProxyAdmin({ enabled: canWrite });
  const proxyBusy =
    createEndpointMutation.isPending ||
    createPoolMutation.isPending ||
    addPoolMemberMutation.isPending ||
    testEndpointMutation.isPending;
  const busy = controlsDisabled || proxyBusy;
  const proxyError =
    getErrorMessageOrNull(upstreamProxyQuery.error) ||
    getErrorMessageOrNull(createEndpointMutation.error) ||
    getErrorMessageOrNull(createPoolMutation.error) ||
    getErrorMessageOrNull(addPoolMemberMutation.error) ||
    getErrorMessageOrNull(testEndpointMutation.error);

  return (
    <SettingsSection section="upstream">
      {proxyError ? <AlertMessage variant="error">{proxyError}</AlertMessage> : null}
      {canWrite && upstreamProxyQuery.data ? (
        <UpstreamProxySettings
          admin={upstreamProxyQuery.data}
          busy={busy}
          canCreateEndpoint={canWriteSecurity}
          onSaveSettings={onSave}
          onCreateEndpoint={(payload) => createEndpointMutation.mutateAsync(payload)}
          onTestEndpoint={(endpointId) => testEndpointMutation.mutateAsync(endpointId)}
          onCreatePool={(payload) => createPoolMutation.mutateAsync(payload)}
          onAddPoolMember={(poolId, payload) => addPoolMemberMutation.mutateAsync({ poolId, payload })}
        />
      ) : null}
      <ResilienceSettings settings={settings} busy={busy} onSave={onSave} />
      <SessionBridgeSettings settings={settings} busy={busy} onSave={onSave} />
      <UpstreamTimeoutSettings
        key={[
          settings.version,
          settings.upstreamConnectTimeoutSeconds,
          settings.proxyRequestBudgetSeconds,
          settings.compactRequestBudgetSeconds,
          settings.transcriptionRequestBudgetSeconds,
          settings.httpResponsesStreamRequestBudgetSeconds,
          settings.httpResponsesSessionBridgeRequestBudgetSeconds,
          settings.streamIdleTimeoutSeconds,
          settings.proxyDownstreamWebsocketIdleTimeoutSeconds,
          settings.sseKeepaliveIntervalSeconds,
        ].join(":")}
        settings={settings}
        busy={busy}
        onSave={onSave}
      />
      <LoadingOverlay visible={proxyBusy} label={t("settings.page.savingLabel")} />
    </SettingsSection>
  );
}

export function DataSettingsSection() {
  const { settings, controlsDisabled, onSave } = useSettingsSection();
  return (
    <SettingsSection section="data">
      <DataRetentionSettings
        key={[
          settings.requestLogRetentionOverrideDays,
          settings.usageHistoryRetentionOverrideDays,
          settings.requestLogRetentionDays,
          settings.usageHistoryRetentionDays,
          // R2 spool retention: a saved value (or a layer move back to
          // inherited) must re-seed the card's draft.
          settings.httpResponsesSessionBridgeOperationSpoolRetentionSeconds,
          settings.provenance?.http_responses_session_bridge_operation_spool_retention_seconds?.source ?? "",
        ].join(":")}
        settings={settings}
        busy={controlsDisabled}
        onSave={onSave}
      />
      <ConversationArchiveSettings settings={settings} busy={controlsDisabled} onSave={onSave} />
    </SettingsSection>
  );
}

export function NotificationsSettingsSection() {
  const { controlsDisabled } = useSettingsSection();
  const canWriteOps = usePermission("ops:write");
  return (
    <SettingsSection section="notifications">
      <QuotaResetWebhookSettings disabled={controlsDisabled || !canWriteOps} />
    </SettingsSection>
  );
}
