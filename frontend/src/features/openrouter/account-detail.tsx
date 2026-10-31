import { Image, KeyRound, Layers, PauseCircle, RefreshCw, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { AccountPauseButton } from "@/components/account-pause-button";
import { Button } from "@/components/ui/button";
import { AccountActivityCard } from "@/features/accounts/components/account-activity-card";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { AccountNotePanel } from "@/features/accounts/components/account-note-panel";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import {
  DetailBanner,
  DetailCard,
  DetailParts,
  DetailRows,
  ProviderDetail,
  SettingRow,
} from "@/features/accounts/components/provider-detail";
import { useCommonMenuItems } from "@/features/accounts/hooks/use-common-menu-items";
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import { useSummaryContext } from "@/features/accounts/hooks/use-summary-context";
import { summarizeEntry } from "@/features/accounts/provider-summary";
import type { AccountRoutingPolicy } from "@/features/accounts/schemas";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatDateTimeInline } from "@/utils/formatters";
import type { OpenRouterAccount } from "./api";
import { OpenRouterMetrics, OpenRouterTier } from "./account-display";
import { modelSelectionKind } from "./model-selection";

/** Account page of an OpenRouter account. */
export function OpenRouterAccountDetail({
  account,
  color,
  readOnly,
  busy,
  error,
  onEdit,
  onRename,
  onModels,
  onImageModels,
  onRefresh,
  onToggle,
  onDelete,
  onRoutingPolicy,
}: {
  account: OpenRouterAccount;
  /** The account's chart colour, used for its logo. */
  color?: string;
  readOnly: boolean;
  busy: boolean;
  error?: string;
  onEdit: () => void;
  onRename: (name: string) => Promise<unknown>;
  onModels: () => void;
  onImageModels: () => void;
  onRefresh: () => void;
  onToggle: (enabled: boolean) => void;
  onDelete: () => void;
  onRoutingPolicy: (value: AccountRoutingPolicy) => void;
}) {
  const { t } = useTranslation();
  const dateFormat = useDateDisplayFormatStore((s) => s.dateDisplayFormat);
  const blurred = usePrivacyStore((s) => s.blurred);
  const summary = summarizeEntry({ kind: "openrouter", account }, useSummaryContext());
  const commonMenu = useCommonMenuItems(account.id, summary.logsAccountId);
  const disabled = readOnly || busy;
  const { state } = account;
  const catalog = new Map(state.catalog.map((model) => [model.id, model]));
  const imageCount = state.selections.filter(
    (selection) => modelSelectionKind(catalog.get(selection.model)) === "images",
  ).length;
  const monitoringErrors = [...new Set([state.catalog_error, state.key_error, state.credits_error].filter(Boolean))];
  const updated = (value: string | null) => (value ? formatDateTimeInline(value, dateFormat) : "Never");
  const apiKeysButton = (
    <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onEdit}>
      <KeyRound className="h-3.5 w-3.5" />
      API keys
    </Button>
  );
  return (
    <ProviderDetail
      key={account.id}
      accountId={account.id}
      data-testid="openrouter-account-detail"
      provider="openrouter"
      color={color}
      name={
        <AccountNameEditor
          key={account.id}
          value={account.name}
          labels={{ edit: "Rename account", input: "Account name", save: "Save name", cancel: t("common.cancel") }}
          disabled={disabled}
          accessory={<AccountColorPicker target={{ modelSourceId: account.id }} disabled={disabled} />}
          onSave={(name) => onRename(name ?? account.name)}
        >
          <span className={cn(blurred && "privacy-blur")}>{account.name}</span>
        </AccountNameEditor>
      }
      plan={<OpenRouterTier account={account} />}
      planKey={summary.planKey}
      status={summary.status}
      subline={[summary.subtitle]}
      actions={
        <>
          <AccountPauseButton paused={!account.isEnabled} disabled={disabled} onClick={() => onToggle(!account.isEnabled)} />
          <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onRefresh}>
            <RefreshCw className="h-3.5 w-3.5" />
            {t("providers.detail.refreshBalance")}
          </Button>
        </>
      }
      menu={[
        ...commonMenu,
        {
          key: "delete",
          label: t("providers.detail.deleteAccount"),
          icon: <Trash2 />,
          destructive: true,
          disabled,
          onSelect: onDelete,
        },
      ]}
      banner={
        summary.status === "paused" ? (
          <DetailBanner tone="off" icon={<PauseCircle />}>
            {t("providers.banner.paused")}
          </DetailBanner>
        ) : null
      }
      alerts={
        <>
          {error && <AlertMessage variant="error">{error}</AlertMessage>}
          {monitoringErrors.map((message) => (
            <p key={message} role="alert" className="break-words text-sm text-destructive">
              {message}
            </p>
          ))}
        </>
      }
      main={
        <>
          <DetailCard title={t("accounts.usage.title")} data-testid="account-usage">
            <div className="min-w-0 space-y-4" aria-label="OpenRouter usage">
              <OpenRouterMetrics account={account} />
              {!account.hasManagementKey && (
                <p className="text-xs text-muted-foreground">
                  Add a management key to display account credits. Key allowance is separate from balance.
                </p>
              )}
              <ProviderAccountTrends provider="openrouter" accountId={account.id} embedded />
            </div>
          </DetailCard>
          <AccountActivityCard activityKey={summary.activityKey} logsAccountId={summary.logsAccountId} color={color} />
        </>
      }
      side={
        <>
          <DetailCard title={t("providers.detail.apiKeys")} action={apiKeysButton}>
            <DetailRows
              rows={[
                { label: "Management key", value: account.hasManagementKey ? "Configured" : "Not configured" },
                { label: "Usage updated", value: updated(state.key_updated_at) },
                { label: "Credits updated", value: updated(state.credits_updated_at) },
                { label: "Catalog updated", value: updated(state.catalog_updated_at) },
              ]}
            />
          </DetailCard>
          <DetailCard title={t("providers.detail.details")}>
            <AccountNotePanel target={{ modelSourceId: account.id }} readOnly={readOnly} />
          </DetailCard>
        </>
      }
      settings={
        <>
          <DetailCard title={t("providers.detail.routing")}>
            <DetailParts>
              <AccountRoutingPolicyControl policy={account.routingPolicy} disabled={disabled} onChange={onRoutingPolicy} />
              <SettingRow
                label={t("providers.detail.models")}
                control={
                  <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onModels}>
                    <Layers className="h-3.5 w-3.5" />
                    Models ({state.all_models ? "All" : state.selections.length - imageCount})
                  </Button>
                }
              />
              <SettingRow
                label={t("providers.detail.imageModels")}
                control={
                  <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onImageModels}>
                    <Image className="h-3.5 w-3.5" />
                    Image models ({imageCount})
                  </Button>
                }
              />
            </DetailParts>
          </DetailCard>
        </>
      }
    />
  );
}
