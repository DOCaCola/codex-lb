import { Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AccountPauseButton } from "@/components/account-pause-button";
import { AlertMessage } from "@/components/alert-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AccountColorPicker } from "@/features/accounts/components/account-color-picker";
import { AccountInfoPanel } from "@/features/accounts/components/account-info-panel";
import { AccountNameEditor } from "@/features/accounts/components/account-name-editor";
import { ProviderAccountTrends } from "@/features/accounts/components/provider-account-trends";
import { ModelSourceName } from "./account-display";
import { OPENAI_COMPATIBLE_LABEL, modelCountLabel, sourceProtocols } from "./display-values";
import type { ModelSource, ModelSourceModel } from "./schemas";

const price = (value: number | null) => (value === null ? "—" : `$${value}`);

function ModelRow({ model }: { model: ModelSourceModel }) {
  const { t } = useTranslation();
  return (
    <li className="space-y-1 rounded-md bg-background/60 p-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="break-all font-medium">{model.displayName || model.model}</span>
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
  return (
    <section
      className="animate-fade-in-up min-w-0 space-y-4 rounded-xl border bg-card p-4 sm:p-5"
      data-testid="model-source-account-detail"
    >
      <div>
        <AccountNameEditor
          key={source.id}
          value={source.name}
          labels={{ edit: "Rename provider", input: "Provider name", save: "Save name", cancel: t("common.cancel") }}
          disabled={readOnly || busy}
          accessory={<AccountColorPicker target={{ modelSourceId: source.id }} disabled={readOnly || busy} />}
          onSave={(name) => onRename(name ?? source.name)}
        >
          <ModelSourceName source={source} color={color} />
        </AccountNameEditor>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {OPENAI_COMPATIBLE_LABEL} | {modelCountLabel(source)}
        </p>
      </div>
      {error && <AlertMessage variant="error">{error}</AlertMessage>}
      <section className="min-w-0 space-y-4 rounded-lg border bg-muted/30 p-4" aria-label="Provider usage">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Usage</h3>
        <ProviderAccountTrends provider="openai_compatible" accountId={source.id} embedded />
      </section>
      <section className="min-w-0 space-y-3 rounded-lg border bg-muted/30 p-4" aria-label="Provider models">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Models · {t("modelSources.fields.pricing")}
        </h3>
        {source.models.length > 0 ? (
          <ul className="space-y-2">
            {source.models.map((model) => <ModelRow key={model.id} model={model} />)}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground">No models configured.</p>
        )}
      </section>
      <AccountInfoPanel title="Connection" rows={[
        { label: "Base URL", value: <span className="break-all">{source.baseUrl}</span> },
        { label: "Protocols", value: sourceProtocols(source).join(", ") || "None" },
        { label: "Timeout", value: source.timeoutSeconds === null ? "Default" : `${source.timeoutSeconds} s` },
        { label: "Max concurrency", value: source.maxConcurrency ?? "Unlimited" },
      ]} />
      {/* Actions last, matching the Codex account detail. */}
      <div className="flex flex-wrap gap-2 border-t pt-4">
        <AccountPauseButton
          paused={!source.isEnabled}
          disabled={readOnly || busy}
          onClick={() => onToggle(!source.isEnabled)}
        />
        <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={readOnly || busy} onClick={onEdit}>
          <Pencil className="h-3.5 w-3.5" />
          {t("common.actions.edit")}
        </Button>
        <Button size="sm" variant="destructive" className="h-8 gap-1.5 text-xs" disabled={readOnly || busy} onClick={onDelete}>
          <Trash2 className="h-3.5 w-3.5" />
          {t("common.actions.delete")}
        </Button>
      </div>
    </section>
  );
}
