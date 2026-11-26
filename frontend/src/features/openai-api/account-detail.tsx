import { CircleDollarSign, Image, KeyRound, Layers, PauseCircle, RefreshCw, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { AccountPauseButton } from "@/components/account-pause-button";
import { MiniQuotaBar } from "@/components/mini-quota-bar";
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
import { AccountRoutingPolicyControl } from "@/features/accounts/components/routing-policy";
import { useCommonMenuItems } from "@/features/accounts/hooks/use-common-menu-items";
import { useSummaryContext } from "@/features/accounts/hooks/use-summary-context";
import { summarizeEntry } from "@/features/accounts/provider-summary";
import type { AccountRoutingPolicy } from "@/features/accounts/schemas";
import { useDateDisplayFormatStore } from "@/hooks/use-date-format";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import { formatDateTimeInline } from "@/utils/formatters";
import type { OpenAIApiAccount } from "./api";
import { creditExhausted, creditPercentLeft, money, selectionCounts } from "./display-values";

const cycleDate = (value: string) =>
  new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

function Metric({ label, value, tone }: { label: string; value: string; tone?: "bad" }) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("text-sm font-medium tabular-nums", tone === "bad" && "text-destructive")}>{value}</dd>
    </div>
  );
}

/** Monthly credit estimated from spend recorded by codex-lb; an OpenAI billing refusal overrides it. */
export function CreditMetrics({ account }: { account: OpenAIApiAccount }) {
  const { credit } = account;
  const exhausted = creditExhausted(account);
  const percent = exhausted ? 0 : creditPercentLeft(account);
  return (
    <dl className="grid grid-cols-2 gap-3">
      <div>
        <Metric
          label="Credit left (estimate)"
          value={exhausted ? "Used up" : credit.monthlyCreditUsd === null ? "Not set" : money(credit.remainingUsd)}
          tone={exhausted ? "bad" : undefined}
        />
        {percent !== null && (
          <div className="mt-2">
            <MiniQuotaBar aria-label="Monthly credit remaining" percent={percent} testId="openai-api-credit" />
          </div>
        )}
      </div>
      <Metric label="Monthly credit" value={money(credit.monthlyCreditUsd)} />
      <Metric label="Spent this cycle" value={money(credit.spentUsd)} />
      <Metric label="Cycle" value={`${cycleDate(credit.cycleStart)} – ${cycleDate(credit.cycleEnd)}`} />
    </dl>
  );
}

/** Account page of an OpenAI API account. */
export function OpenAIApiAccountDetail({
  account,
  color,
  readOnly,
  busy,
  error,
  onKey,
  onCredit,
  onRename,
  onModels,
  onImageModels,
  onRefresh,
  onToggle,
  onDelete,
  onRoutingPolicy,
}: {
  account: OpenAIApiAccount;
  /** The account's chart colour, used for its logo. */
  color?: string;
  readOnly: boolean;
  busy: boolean;
  error?: string;
  onKey: () => void;
  onCredit: () => void;
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
  const summary = summarizeEntry({ kind: "openai_apikey", account }, useSummaryContext());
  const commonMenu = useCommonMenuItems(account.id, summary.logsAccountId);
  const disabled = readOnly || busy;
  const { state, credit } = account;
  const counts = selectionCounts(account);
  const keyButton = (
    <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onKey}>
      <KeyRound className="h-3.5 w-3.5" />
      Replace key
    </Button>
  );
  return (
    <ProviderDetail
      key={account.id}
      accountId={account.id}
      data-testid="openai-api-account-detail"
      provider="openai_apikey"
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
      plan={null}
      planKey={summary.planKey}
      status={summary.status}
      subline={[summary.subtitle]}
      actions={
        <>
          <AccountPauseButton paused={!account.isEnabled} disabled={disabled} onClick={() => onToggle(!account.isEnabled)} />
          <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onRefresh}>
            <RefreshCw className="h-3.5 w-3.5" />
            {t("providers.detail.refresh")}
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
          {credit.exhaustedUntil && creditExhausted(account) && (
            <AlertMessage variant="error">
              OpenAI reports the API credit as used up. Requests resume on{" "}
              {formatDateTimeInline(credit.exhaustedUntil, dateFormat)} or after a manual refresh.
            </AlertMessage>
          )}
          {state.catalog_error && (
            <p role="alert" className="break-words text-sm text-destructive">
              {state.catalog_error}
            </p>
          )}
        </>
      }
      main={
        <>
          <DetailCard title={t("accounts.usage.title")} data-testid="account-usage">
            <div className="min-w-0 space-y-4" aria-label="OpenAI API credit">
              <CreditMetrics account={account} />
              <p className="text-xs text-muted-foreground">
                Estimated from spend recorded by codex-lb at API prices. Usage of this organization outside codex-lb is
                not included; OpenAI publishes no balance for project keys.
              </p>
              <ProviderAccountTrends provider="openai_apikey" accountId={account.id} embedded />
            </div>
          </DetailCard>
          <AccountActivityCard activityKey={summary.activityKey} logsAccountId={summary.logsAccountId} color={color} />
        </>
      }
      side={
        <>
          <DetailCard title={t("providers.detail.apiKeys")} action={keyButton}>
            <DetailRows
              rows={[
                {
                  label: "Catalog updated",
                  value: state.catalog_updated_at ? formatDateTimeInline(state.catalog_updated_at, dateFormat) : "Never",
                },
                { label: "Models", value: `${counts.text} text · ${counts.image} image` },
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
                    Models ({counts.text})
                  </Button>
                }
              />
              <SettingRow
                label={t("providers.detail.imageModels")}
                control={
                  <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onImageModels}>
                    <Image className="h-3.5 w-3.5" />
                    Image models ({counts.image})
                  </Button>
                }
              />
            </DetailParts>
          </DetailCard>
          <DetailCard title="Monthly credit">
            <DetailParts>
              <SettingRow
                label="Credit amount and renewal day"
                control={
                  <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled} onClick={onCredit}>
                    <CircleDollarSign className="h-3.5 w-3.5" />
                    {state.monthly_credit_usd === null ? "Not set" : money(state.monthly_credit_usd)}
                    {state.credit_renews_on === null ? "" : ` · day ${state.credit_renews_on}`}
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
