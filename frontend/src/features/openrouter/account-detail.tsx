import { Image, KeyRound, Layers, RefreshCw, Trash2 } from "lucide-react";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import { AccountInfoPanel } from "@/features/accounts/components/account-info-panel";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { Button } from "@/components/ui/button";
import { AccountPauseButton } from "@/components/account-pause-button";
import { useTranslation } from "react-i18next";
import { AlertMessage } from "@/components/alert-message";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { formatDateTimeInline } from "@/utils/formatters";
import type { OpenRouterAccount } from "./api";
import { OpenRouterName, OpenRouterTier, OpenRouterMetrics } from "./account-display";
import { modelSelectionKind } from "./model-selection";
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import type { AccountRoutingPolicy } from "@/features/accounts/schemas";

export function OpenRouterAccountDetail({
  account,
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
  const { state } = account;
  const catalog = new Map(state.catalog.map((model) => [model.id, model]));
  const imageCount = state.selections.filter(
    (selection) => modelSelectionKind(catalog.get(selection.model)) === "images",
  ).length;
  const monitoringErrors = [...new Set([state.catalog_error, state.key_error, state.credits_error].filter(Boolean))];
  const updated = (value: string | null) => (value ? formatDateTimeInline(value, dateFormat) : "Never");
  return (
    <section
      className="animate-fade-in-up min-w-0 space-y-4 rounded-xl border bg-card p-4 sm:p-5"
      data-testid="openrouter-account-detail"
    >
      <div>
        <AccountNameEditor
          key={account.id}
          value={account.name}
          labels={{ edit: "Rename account", input: "Account name", save: "Save name", cancel: t("common.cancel") }}
          disabled={readOnly || busy}
          accessory={<AccountColorPicker target={{ modelSourceId: account.id }} disabled={readOnly || busy} />}
          onSave={(name) => onRename(name ?? account.name)}
        >
          <OpenRouterName account={account} />
        </AccountNameEditor>
        <p className="mt-0.5 text-xs text-muted-foreground">
          OpenRouter | <OpenRouterTier account={account} /> | {state.all_models ? "All conversation models" : `${state.selections.length} ${state.selections.length === 1 ? "model" : "models"} selected`}
        </p>
      </div>
      {error && <AlertMessage variant="error">{error}</AlertMessage>}
      {monitoringErrors.map((message) => (
        <p key={message} role="alert" className="break-words text-sm text-destructive">
          {message}
        </p>
      ))}
      <section
        className="min-w-0 space-y-4 rounded-lg border bg-muted/30 p-4"
        aria-label="OpenRouter usage"
      >
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Usage</h3>
        <OpenRouterMetrics account={account} detailed />
        {!account.hasManagementKey && (
          <p className="text-xs text-muted-foreground">
            Add a management key to display account credits. Key allowance is separate from balance.
          </p>
        )}
        <ProviderAccountTrends provider="openrouter" accountId={account.id} embedded />
      </section>
      <AccountInfoPanel title="Monitoring" rows={[
        { label: "Management key", value: account.hasManagementKey ? "Configured" : "Not configured" },
        { label: "Usage updated", value: updated(state.key_updated_at) },
        { label: "Credits updated", value: updated(state.credits_updated_at) },
        { label: "Catalog updated", value: updated(state.catalog_updated_at) },
      ]} />
      {/* Actions last, matching the Codex account detail. */}
      <div className="space-y-3 border-t pt-4">
        <AccountRoutingPolicyControl policy={account.routingPolicy} disabled={readOnly || busy} onChange={onRoutingPolicy} />
        <div className="flex flex-wrap gap-2">
        <AccountPauseButton
          paused={!account.isEnabled}
          disabled={readOnly || busy}
          onClick={() => onToggle(!account.isEnabled)}
        />
        <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={readOnly || busy} onClick={onModels}>
          <Layers className="h-3.5 w-3.5" />
          Models ({state.all_models ? "All" : state.selections.length - imageCount})
        </Button>
        <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={readOnly || busy} onClick={onImageModels}>
          <Image className="h-3.5 w-3.5" />
          Image models ({imageCount})
        </Button>
        <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={readOnly || busy} onClick={onRefresh}>
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
        <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={readOnly || busy} onClick={onEdit}>
          <KeyRound className="h-3.5 w-3.5" />
          API keys
        </Button>
        <Button size="sm" variant="destructive" className="h-8 gap-1.5 text-xs" disabled={readOnly || busy} onClick={onDelete}>
          <Trash2 className="h-3.5 w-3.5" />
          {t("common.actions.delete")}
        </Button>
        </div>
      </div>
    </section>
  );
}
