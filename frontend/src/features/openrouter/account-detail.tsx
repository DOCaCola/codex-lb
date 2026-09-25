import { Layers, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AccountPauseButton } from "@/components/account-pause-button";
import { useTranslation } from "react-i18next";
import { StatusBadge } from "@/components/status-badge";
import { AlertMessage } from "@/components/alert-message";
import type { OpenRouterAccount } from "./api";
import {
  OpenRouterName,
  OpenRouterMetrics,
  OpenRouterFreshness,
} from "./account-display";
import { openRouterStatus } from "./display-values";

export function OpenRouterAccountDetail({
  account,
  readOnly,
  busy,
  error,
  onEdit,
  onModels,
  onRefresh,
  onToggle,
  onDelete,
}: {
  account: OpenRouterAccount;
  readOnly: boolean;
  busy: boolean;
  error?: string;
  onEdit: () => void;
  onModels: () => void;
  onRefresh: () => void;
  onToggle: (enabled: boolean) => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="min-w-0 space-y-4" data-testid="openrouter-account-detail">
      <div className="rounded-xl border bg-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="break-words text-lg font-semibold">
              <OpenRouterName account={account} />
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">OpenRouter</p>
          </div>
          <StatusBadge status={openRouterStatus(account)} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-4">
          <AccountPauseButton
            paused={!account.isEnabled}
            disabled={readOnly || busy}
            onClick={() => onToggle(!account.isEnabled)}
          />
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            disabled={readOnly || busy}
            onClick={onModels}
          >
            <Layers className="h-3.5 w-3.5" />
            Models ({account.state.selections.length})
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={readOnly || busy}
            onClick={onRefresh}
            className="h-8 gap-1.5 text-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={readOnly || busy}
            onClick={onEdit}
            className="h-8 gap-1.5 text-xs"
          >
            <Pencil className="h-3.5 w-3.5" />
            {t("common.actions.edit")}
          </Button>
          <Button
            size="sm"
            variant="destructive"
            className="h-8 gap-1.5 text-xs"
            disabled={readOnly || busy}
            onClick={onDelete}
          >
            <Trash2 className="h-3.5 w-3.5" />
            {t("common.actions.delete")}
          </Button>
        </div>
      </div>
      {error && <AlertMessage variant="error">{error}</AlertMessage>}
      <section
        className="space-y-5 rounded-xl border bg-card p-5"
        aria-label="OpenRouter usage"
      >
        <h3 className="text-sm font-semibold">Usage &amp; balance</h3>
        <OpenRouterMetrics account={account} detailed />
        <div className="border-t pt-4">
          <OpenRouterFreshness account={account} />
        </div>
      </section>
    </div>
  );
}
