import { Fragment, type KeyboardEvent, useMemo, useState } from "react";
import { ArrowRight, BookOpen, Info, Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SpinnerBlock } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { type ModelCatalogueEdit, useModelContextWindowOverrides } from "@/features/settings/hooks/use-settings";
import type { ModelCatalogueEntry, ModelContextWindowOverride } from "@/features/settings/schemas";
import { cn } from "@/lib/utils";
import { getErrorMessageOrNull } from "@/utils/errors";

export type ModelCatalogueSettingsProps = {
  disabled?: boolean;
};

type Draft = { slug: string; name: string; contextWindow: string };

type ListFilter = "all" | "listed" | "hidden";

const LIST_FILTERS: ListFilter[] = ["all", "listed", "hidden"];
// Providers in the order clients list their models; other kinds follow.
const PROVIDER_ORDER = ["subscription", "claude", "antigravity", "openai_apikey", "openrouter", "openai_compatible"];

function providerRank(provider: string): number {
  const index = PROVIDER_ORDER.indexOf(provider);
  return index === -1 ? PROVIDER_ORDER.length : index;
}

function parseContextWindow(value: string): number | null {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) && parsed >= 1 ? parsed : null;
}

function dashboardWindow(override: ModelContextWindowOverride | undefined): number | null {
  return override?.source === "dashboard" ? override.contextWindow : null;
}

type SegmentedOption = { value: string; label: string; count: number };

function Segmented({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: SegmentedOption[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="inline-flex h-8 items-center rounded-md border bg-background p-0.5" role="radiogroup" aria-label={label}>
      {options.map((option) => {
        const selected = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              "inline-flex h-6 items-center gap-1.5 rounded-[5px] px-2.5 text-xs text-muted-foreground transition-colors",
              selected ? "bg-accent text-accent-foreground shadow-sm" : "hover:bg-accent/60 hover:text-accent-foreground",
            )}
          >
            {option.label} <span className="text-[11px] tabular-nums text-muted-foreground">{option.count}</span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * Settings -> Model catalogue: one row per model currently offered to clients,
 * from every provider, grouped by provider.
 *
 * Edit opens one inline editor per row for the model's name and context
 * window. A name replaces the provider's name wherever the model is shown:
 * client model lists, the redirect and compaction pickers and the dashboard.
 * Clients compact at 90% of the context window. A dashboard window wins for
 * its slug; one inherited from `CODEX_LB_MODEL_CONTEXT_WINDOW_OVERRIDES` is
 * read-only until overridden, and clearing a dashboard window returns the
 * model to the environment entry or to its default. Image models have no
 * context window.
 *
 * The "Client lists" switch hides a model from client model pickers; hidden
 * models stay usable by name.
 */
export function ModelCatalogueSettings({ disabled = false }: ModelCatalogueSettingsProps) {
  const { t } = useTranslation();
  const { overridesQuery, saveMutation, visibilityMutation } = useModelContextWindowOverrides();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [listFilter, setListFilter] = useState<ListFilter>("all");
  const [providerFilter, setProviderFilter] = useState("all");
  const [search, setSearch] = useState("");

  const error = useMemo(
    () =>
      getErrorMessageOrNull(overridesQuery.error) ||
      getErrorMessageOrNull(saveMutation.error) ||
      getErrorMessageOrNull(visibilityMutation.error),
    [overridesQuery.error, saveMutation.error, visibilityMutation.error],
  );

  const models = useMemo(() => overridesQuery.data?.models ?? [], [overridesQuery.data?.models]);
  const displayNames = new Map(models.map((model) => [model.slug, model.displayName]));
  const overrides = useMemo(
    () => new Map((overridesQuery.data?.overrides ?? []).map((override) => [override.slug, override])),
    [overridesQuery.data?.overrides],
  );
  const busy = disabled || saveMutation.isPending || visibilityMutation.isPending;

  const providers = useMemo(
    () => [...new Set(models.map((model) => model.provider))].sort((a, b) => providerRank(a) - providerRank(b)),
    [models],
  );
  const providerOptions: SegmentedOption[] = [
    { value: "all", label: t("settings.modelCatalogue.providerFilter.all"), count: models.length },
    ...providers.map((provider) => ({
      value: provider,
      label: t(`settings.modelCatalogue.provider.${provider}`, provider),
      count: models.filter((model) => model.provider === provider).length,
    })),
  ];
  const listOptions: SegmentedOption[] = LIST_FILTERS.map((option) => ({
    value: option,
    label: t(`settings.modelCatalogue.filter.${option}`),
    count:
      option === "all"
        ? models.length
        : models.filter((model) => model.listed === (option === "listed")).length,
  }));

  const needle = search.trim().toLowerCase();
  const shownGroups = providers
    .filter((provider) => providerFilter === "all" || provider === providerFilter)
    .map((provider) => {
      const entries = models.filter((model) => model.provider === provider);
      return {
        provider,
        hiddenCount: entries.filter((model) => !model.listed).length,
        models: entries.filter(
          (model) =>
            (listFilter === "all" || (listFilter === "listed") === model.listed) &&
            (!needle ||
              [model.displayName, model.providerDisplayName, model.slug].some((text) =>
                text.toLowerCase().includes(needle),
              )),
        ),
      };
    })
    .filter((group) => group.models.length > 0);

  const draftModel = draft ? models.find((model) => model.slug === draft.slug) : undefined;
  const windowEditable = draftModel !== undefined && !draftModel.image && !draftModel.redirectTargetModel;
  const draftWindowText = draft?.contextWindow.trim() ?? "";
  const draftWindow = draftWindowText ? parseContextWindow(draftWindowText) : null;
  const invalidWindow = windowEditable && draftWindowText !== "" && draftWindow === null;
  const aboveMaximum =
    windowEditable &&
    draftWindow !== null &&
    draftModel.maxContextWindow !== null &&
    draftWindow > draftModel.maxContextWindow;
  const canSave = !busy && draft !== null && !invalidWindow && !aboveMaximum;

  const startEditing = (model: ModelCatalogueEntry) => {
    const window = dashboardWindow(overrides.get(model.slug));
    setDraft({
      slug: model.slug,
      name: model.renamed ? model.displayName : "",
      contextWindow: window !== null ? String(window) : "",
    });
  };

  const handleSave = async () => {
    if (!draft || !draftModel || !canSave) {
      return;
    }
    const name = draft.name.trim();
    const wantedName = name && name !== draftModel.providerDisplayName ? name : null;
    const edit: ModelCatalogueEdit = { slug: draft.slug };
    if (wantedName !== (draftModel.renamed ? draftModel.displayName : null)) {
      edit.displayName = wantedName;
    }
    if (windowEditable && draftWindow !== dashboardWindow(overrides.get(draft.slug))) {
      edit.contextWindow = draftWindow;
    }
    if (edit.displayName !== undefined || edit.contextWindow !== undefined) {
      await saveMutation.mutateAsync(edit);
    }
    setDraft(null);
  };

  const handleEditorKeys = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      void handleSave();
    } else if (event.key === "Escape") {
      setDraft(null);
    }
  };

  const windowSummary = (model: ModelCatalogueEntry, override: ModelContextWindowOverride | undefined) => {
    const defaultWindow = model.defaultContextWindow ?? 0;
    const parts = [
      override ? t("settings.modelCatalogue.window.default", { value: defaultWindow.toLocaleString() }) : null,
      model.maxContextWindow !== null
        ? t("settings.modelCatalogue.window.maximum", { value: model.maxContextWindow.toLocaleString() })
        : null,
    ].filter((part) => part !== null);
    return (
      <span className="flex flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-1.5 text-xs tabular-nums">
          {(override?.contextWindow ?? defaultWindow).toLocaleString()}
          {override ? (
            <Badge variant={override.source === "dashboard" ? "secondary" : "outline"} className="text-[10px] font-normal">
              {t(`settings.modelCatalogue.source.${override.source === "dashboard" ? "dashboard" : "environment"}`)}
            </Badge>
          ) : null}
        </span>
        {parts.length > 0 ? (
          <span className="text-[11px] tabular-nums text-muted-foreground">{parts.join(" · ")}</span>
        ) : null}
      </span>
    );
  };

  const editorRow = (model: ModelCatalogueEntry, override: ModelContextWindowOverride | undefined) => {
    if (!draft) {
      return null;
    }
    const savedWindow = dashboardWindow(override);
    const defaultWindow = model.defaultContextWindow ?? 0;
    return (
      <TableRow className="bg-muted/30 hover:bg-muted/30">
        <TableCell colSpan={4}>
          <div className="flex flex-wrap items-start gap-4 py-1">
            <label className="flex min-w-[220px] flex-1 flex-col gap-1">
              <span className="text-[11px] font-medium text-muted-foreground">{t("settings.modelCatalogue.editor.name")}</span>
              <Input
                aria-label={t("settings.modelCatalogue.form.nameLabel", { model: model.slug })}
                value={draft.name}
                placeholder={model.providerDisplayName}
                maxLength={255}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                onKeyDown={handleEditorKeys}
                className="h-8 text-xs"
                disabled={busy}
                autoFocus
              />
              <span className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                {t("settings.modelCatalogue.editor.nameHint", { name: model.providerDisplayName })}
                {draft.name ? (
                  <button
                    type="button"
                    className="text-primary hover:underline"
                    onClick={() => setDraft({ ...draft, name: "" })}
                    disabled={busy}
                  >
                    {t("settings.modelCatalogue.editor.useProviderName")}
                  </button>
                ) : null}
              </span>
            </label>
            <label className="flex min-w-[220px] flex-col gap-1">
              <span className="text-[11px] font-medium text-muted-foreground">
                {t("settings.modelCatalogue.table.contextWindow")}
              </span>
              {model.image ? (
                <span className="pt-2 text-[11px] text-muted-foreground">
                  {t("settings.modelCatalogue.editor.notApplicable")}
                </span>
              ) : model.redirectTargetModel ? (
                <span className="pt-2 text-[11px] text-muted-foreground">
                  {t("settings.modelCatalogue.redirectOverrideDisabled")}
                </span>
              ) : (
                <>
                  <Input
                    aria-label={t("settings.modelCatalogue.form.contextWindowLabel", { model: model.slug })}
                    value={draft.contextWindow}
                    placeholder={(override?.source === "env" ? override.contextWindow : defaultWindow).toLocaleString()}
                    onChange={(event) => setDraft({ ...draft, contextWindow: event.target.value })}
                    onKeyDown={handleEditorKeys}
                    inputMode="numeric"
                    className="h-8 max-w-[160px] text-xs tabular-nums"
                    disabled={busy}
                  />
                  {aboveMaximum && model.maxContextWindow !== null ? (
                    <span className="text-[11px] text-destructive">
                      {t("settings.modelCatalogue.aboveMaximum", { value: model.maxContextWindow.toLocaleString() })}
                    </span>
                  ) : invalidWindow ? (
                    <span className="text-[11px] text-destructive">{t("settings.modelCatalogue.editor.invalidWindow")}</span>
                  ) : (
                    <span className="flex flex-wrap items-center gap-1.5 text-[11px] tabular-nums text-muted-foreground">
                      {[
                        t("settings.modelCatalogue.editor.default", { value: defaultWindow.toLocaleString() }),
                        model.maxContextWindow !== null
                          ? t("settings.modelCatalogue.editor.maximum", { value: model.maxContextWindow.toLocaleString() })
                          : null,
                        override?.envValue != null
                          ? t("settings.modelCatalogue.editor.environment", { value: override.envValue.toLocaleString() })
                          : null,
                      ]
                        .filter((part) => part !== null)
                        .join(" · ")}
                      {savedWindow !== null && draft.contextWindow ? (
                        <button
                          type="button"
                          className="text-primary hover:underline"
                          onClick={() => setDraft({ ...draft, contextWindow: "" })}
                          disabled={busy}
                        >
                          {override?.envValue != null
                            ? t("settings.modelCatalogue.editor.useEnvironment")
                            : t("settings.modelCatalogue.editor.useDefault")}
                        </button>
                      ) : null}
                    </span>
                  )}
                </>
              )}
            </label>
            <div className="ml-auto flex items-center gap-1.5 self-end pb-5">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-8 text-xs"
                disabled={busy}
                onClick={() => setDraft(null)}
              >
                {t("common.cancel")}
              </Button>
              <Button type="button" size="sm" className="h-8 text-xs" disabled={!canSave} onClick={() => void handleSave()}>
                {t("common.actions.save")}
              </Button>
            </div>
          </div>
        </TableCell>
      </TableRow>
    );
  };

  return (
    <section id="model-catalogue" className="scroll-mt-16 space-y-3 rounded-xl border bg-card p-5">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
          <BookOpen className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">{t("settings.modelCatalogue.title")}</h3>
          <p className="text-xs text-muted-foreground">{t("settings.modelCatalogue.description")}</p>
        </div>
      </div>

      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}

      {overridesQuery.isLoading && !overridesQuery.data ? (
        <div className="py-8">
          <SpinnerBlock />
        </div>
      ) : models.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={t("settings.modelCatalogue.empty.title")}
          description={t("settings.modelCatalogue.empty.description")}
        />
      ) : (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[200px] flex-1">
              <Search
                className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("settings.modelCatalogue.search.placeholder")}
                aria-label={t("settings.modelCatalogue.search.label")}
                className="h-8 pl-8 text-xs"
              />
            </div>
            <Segmented
              label={t("settings.modelCatalogue.providerFilter.label")}
              options={providerOptions}
              value={providerFilter}
              onChange={setProviderFilter}
            />
            <Segmented
              label={t("settings.modelCatalogue.filter.label")}
              options={listOptions}
              value={listFilter}
              onChange={(value) => setListFilter(value as ListFilter)}
            />
          </div>
          <div className="overflow-x-auto rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("settings.modelCatalogue.table.model")}</TableHead>
                  <TableHead className="w-[240px]">{t("settings.modelCatalogue.table.contextWindow")}</TableHead>
                  <TableHead className="w-[130px]">{t("settings.modelCatalogue.table.clientLists")}</TableHead>
                  <TableHead className="w-[80px] text-right">{t("apiKeys.table.actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shownGroups.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-6 text-center text-xs text-muted-foreground">
                      {t("settings.modelCatalogue.filter.empty")}
                    </TableCell>
                  </TableRow>
                ) : null}
                {shownGroups.map((group) => (
                  <Fragment key={group.provider}>
                    <TableRow className="bg-muted/40 hover:bg-muted/40">
                      <TableCell
                        colSpan={4}
                        className="py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                      >
                        {t(`settings.modelCatalogue.provider.${group.provider}`, group.provider)}
                        {group.hiddenCount > 0 ? (
                          <span className="ml-1.5 font-normal normal-case tracking-normal">
                            {t("settings.modelCatalogue.groupHidden", { count: group.hiddenCount })}
                          </span>
                        ) : null}
                      </TableCell>
                    </TableRow>
                    {group.models.map((model) => {
                      const override = overrides.get(model.slug);
                      const editing = draft?.slug === model.slug;
                      const targetName = model.redirectTargetModel
                        ? displayNames.get(model.redirectTargetModel) ?? model.redirectTargetModel
                        : null;
                      const dimmed = !model.listed && "opacity-60";
                      return (
                        <Fragment key={model.slug}>
                          <TableRow className={cn(editing && "border-b-0")}>
                            <TableCell>
                              <span className={cn("flex flex-col", dimmed)}>
                                <span className="flex flex-wrap items-center gap-1.5 text-xs font-medium">
                                  {model.displayName}
                                  {model.image ? (
                                    <Badge variant="outline" className="text-[10px] font-normal">
                                      {t("settings.modelCatalogue.badge.image")}
                                    </Badge>
                                  ) : null}
                                  {model.renamed ? (
                                    <Badge variant="secondary" className="text-[10px] font-normal">
                                      {t("settings.modelCatalogue.badge.renamed")}
                                    </Badge>
                                  ) : null}
                                  {targetName ? (
                                    <Badge variant="outline" className="bg-primary/10 text-[10px] text-primary">
                                      <ArrowRight className="size-2.5" aria-hidden="true" />
                                      {t("settings.modelCatalogue.redirectsTo", { target: targetName })}
                                    </Badge>
                                  ) : null}
                                </span>
                                <span className={cn("text-[11px] text-muted-foreground", !model.retired && "font-mono")}>
                                  {model.retired ? t("settings.modelCatalogue.notInRegistry") : model.slug}
                                </span>
                                {model.renamed ? (
                                  <span className="text-[11px] text-muted-foreground">
                                    {t("settings.modelCatalogue.providerName", { name: model.providerDisplayName })}
                                  </span>
                                ) : null}
                              </span>
                            </TableCell>
                            <TableCell className={cn(dimmed)}>
                              {model.image ? (
                                <span className="text-xs text-muted-foreground">—</span>
                              ) : targetName ? (
                                <span className="text-xs text-muted-foreground">
                                  {model.redirectTargetOverrideTokens !== null
                                    ? `${model.redirectTargetOverrideTokens.toLocaleString()} · `
                                    : null}
                                  {t("settings.modelRedirects.servedModel")}
                                </span>
                              ) : (
                                windowSummary(model, override)
                              )}
                            </TableCell>
                            <TableCell>
                              <span className="flex items-center gap-2 text-[11px] text-muted-foreground">
                                <Switch
                                  checked={model.listed}
                                  onCheckedChange={(listed) => visibilityMutation.mutate({ slug: model.slug, listed })}
                                  disabled={busy}
                                  aria-label={t("settings.modelCatalogue.form.listedLabel", { model: model.slug })}
                                />
                                {model.listed ? t("settings.modelCatalogue.listed") : t("settings.modelCatalogue.hidden")}
                              </span>
                            </TableCell>
                            <TableCell className="text-right">
                              {editing ? null : (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  disabled={busy}
                                  onClick={() => startEditing(model)}
                                  aria-label={t("settings.modelCatalogue.form.editLabel", { model: model.slug })}
                                >
                                  {t("common.actions.edit")}
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                          {editing ? editorRow(model, override) : null}
                        </Fragment>
                      );
                    })}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
            <Info className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
            {t("settings.modelCatalogue.cacheNote")}
          </p>
        </div>
      )}
    </section>
  );
}
