import { PauseCircle, Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AccountPauseButton } from "@/components/account-pause-button";
import { AlertMessage } from "@/components/alert-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AccountActivityCard } from "@/features/accounts/components/account-activity-card";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { AccountNotePanel } from "@/features/accounts/components/account-note-panel";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import {
  DetailBanner,
  DetailCard,
  DetailRows,
  ProviderDetail,
} from "@/features/accounts/components/provider-detail";
import { useCommonMenuItems } from "@/features/accounts/hooks/use-common-menu-items";
import { useSummaryContext } from "@/features/accounts/hooks/use-summary-context";
import { summarizeEntry } from "@/features/accounts/provider-summary";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { sourceProtocols } from "./display-values";
import type { ModelSource, ModelSourceModel } from "./schemas";

const price = (value: number | null) => (value === null ? "—" : "$" + value);

function ModelRow({ model }: { model: ModelSourceModel }) {
  const { t } = useTranslation();
  return (
    <li className="space-y-1 py-2 text-xs first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className="break-all text-[13px] font-medium">{model.displayName || model.model}</span>
        {!model.isEnabled ? <Badge variant="secondary">{t("common.states.disabled")}</Badge> : null}
      </div>
      {model.displayName && model.displayName !== model.model ? (
        <div className="break-all text-muted-foreground">{model.model}</div>
      ) : null}
      <div className="flex flex-wrap gap-x-4 gap-y-1 tabular-nums text-muted-foreground">
        <span>{t("common.units.input")}: {price(model.inputPer1M)}</span>
        <span>{t("common.units.cached")}: {price(model.cachedInputPer1M)}</span>
        <span>{t("common.units.output")}: {price(model.outputPer1M)}</span>
        {model.audioPerMinute !== null ? (
          <span>{t("modelSources.fields.perMinute")}: {price(model.audioPerMinute)}</span>
        ) : null}
      </div>
    </li>
  );
}

/** Account page of an OpenAI-compatible provider. */
export function ModelSourceAccountDetail({
  source,
  color,
  readOnly,
  busy,
  error,
  onRename,
  onToggle,
  onEdit,
  onDelete,
}: {
  source: ModelSource;
  /** The source's chart colour, used for its logo. */
  color?: string;
  readOnly: boolean;
  busy: boolean;
  error?: string;
  onRename: (name: string) => Promise<unknown>;
  onToggle: (enabled: boolean) => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const summary = summarizeEntry({ kind: "openai_compatible", account: source }, useSummaryContext());
  const commonMenu = useCommonMenuItems(source.id, summary.logsAccountId);
  const disabled = readOnly || busy;
  const editButton = (
    <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onEdit}>
      <Pencil className="h-3.5 w-3.5" />
      {t("common.actions.edit")}
    </Button>
  );
  return (
    <ProviderDetail
      key={source.id}
      data-testid="model-source-account-detail"
      provider="openai_compatible"
      color={color}
      name={
        <AccountNameEditor
          key={source.id}
          value={source.name}
          labels={{ edit: "Rename provider", input: "Provider name", save: "Save name", cancel: t("common.cancel") }}
          disabled={disabled}
          accessory={<AccountColorPicker target={{ modelSourceId: source.id }} disabled={disabled} />}
          onSave={(name) => onRename(name ?? source.name)}
        >
          <span className={cn(blurred && "privacy-blur")}>{source.name}</span>
        </AccountNameEditor>
      }
      status={summary.status}
      subline={[summary.models]}
      actions={<AccountPauseButton paused={!source.isEnabled} disabled={disabled} onClick={() => onToggle(!source.isEnabled)} />}
      menu={[
        { key: "edit", label: t("common.actions.edit"), icon: <Pencil />, disabled, onSelect: onEdit },
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
      alerts={error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
      main={
        <>
          <DetailCard title={t("accounts.usage.title")} data-testid="account-usage">
            <div aria-label="Provider usage">
              <ProviderAccountTrends provider="openai_compatible" accountId={source.id} embedded />
            </div>
          </DetailCard>
          <AccountActivityCard activityKey={summary.activityKey} logsAccountId={summary.logsAccountId} color={color} />
          <DetailCard title={"Models · " + t("modelSources.fields.pricing")}>
            <div aria-label="Provider models">
              {source.models.length > 0 ? (
                <ul className="divide-y">
                  {source.models.map((model) => <ModelRow key={model.id} model={model} />)}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">No models configured.</p>
              )}
            </div>
          </DetailCard>
        </>
      }
      side={
        <>
          <DetailCard title={t("providers.detail.connection")} action={editButton}>
            <DetailRows
              rows={[
                { label: "Base URL", value: <span className="break-all">{source.baseUrl}</span> },
                { label: "Protocols", value: sourceProtocols(source).join(", ") || "None" },
                { label: "Timeout", value: source.timeoutSeconds === null ? "Default" : source.timeoutSeconds + " s" },
                { label: "Max concurrency", value: source.maxConcurrency ?? "Unlimited" },
              ]}
            />
          </DetailCard>
          <DetailCard title={t("providers.detail.details")}>
            <AccountNotePanel target={{ modelSourceId: source.id }} readOnly={readOnly} />
          </DetailCard>
        </>
      }
    />
  );
}
