import { useId, useState } from "react";
import { ArrowLeftRight, ArrowRight, CircleAlert, Info, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AlertMessage } from "@/components/alert-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SpinnerBlock } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  useModelCompactionRoutes,
  useModelContextWindowOverrides,
  useModelRedirects,
} from "@/features/settings/hooks/use-settings";
import type { ModelRedirect } from "@/features/settings/schemas";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type Draft = { source: string; target: string; editing: boolean };
type FieldErrors = { source?: string; target?: string };
type ModelOption = { slug: string; displayName: string; hidden: boolean; image: boolean; redirected: boolean };

/** Image redirects serve gpt-image-* requests from an image model; text redirects stay text-only. */
const IMAGE_REDIRECT_SOURCE_PREFIX = "gpt-image-";

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <div id={id} role="alert" className="mt-1 flex items-start gap-1 text-[11px] text-destructive">
      <CircleAlert className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
      {message}
    </div>
  );
}

export function ModelRedirectSettings({ disabled = false }: { disabled?: boolean }) {
  const { t } = useTranslation();
  const { redirectsQuery, upsertMutation, deleteMutation } = useModelRedirects();
  const { overridesQuery } = useModelContextWindowOverrides();
  const { routesQuery } = useModelCompactionRoutes();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const inputId = useId();
  const sourceErrorId = useId();
  const targetErrorId = useId();
  const redirects = redirectsQuery.data?.redirects ?? [];
  const routes = routesQuery.data?.routes ?? [];
  const models = overridesQuery.data?.models ?? [];
  const busy = disabled || upsertMutation.isPending || deleteMutation.isPending;

  const modelsBySlug = new Map(models.filter((model) => !model.retired).map((model) => [model.slug, model.displayName]));
  const groups = new Map<string, ModelOption[]>();
  for (const group of redirectsQuery.data?.targets ?? []) {
    groups.set(group.provider, group.models.map((model) => ({ ...model, redirected: false })));
    for (const model of group.models) modelsBySlug.set(model.slug, model.displayName);
  }
  for (const model of models) {
    if (!model.redirectTargetModel || model.retired) continue;
    const option = { slug: model.slug, displayName: model.displayName, hidden: !model.listed, image: false, redirected: true };
    groups.set(model.provider, [...(groups.get(model.provider) ?? []), option]);
  }

  const displayName = (slug: string) => modelsBySlug.get(slug) ?? slug;
  const modelCell = (slug: string) => (
    <span className="flex flex-col overflow-hidden">
      <span className="truncate text-xs font-medium" title={slug}>{displayName(slug)}</span>
      <span className={cn("truncate text-[11px] text-muted-foreground", modelsBySlug.has(slug) && "font-mono")}>
        {modelsBySlug.has(slug) ? slug : t("settings.modelRedirects.notInCatalogue")}
      </span>
    </span>
  );

  function openForm(next: Draft | null) {
    setFieldErrors({});
    setDraft(next);
  }

  function validate(source: string, target: string, editing: boolean): FieldErrors {
    const errors: FieldErrors = {};
    const feeding = redirects.filter((redirect) => redirect.targetModel === source);
    const targetRedirect = redirects.find((redirect) => redirect.sourceModel === target);
    if (!source) {
      errors.source = t("settings.modelRedirects.validation.sourceRequired");
    } else if (source.length > 256 || /\s|\p{C}/u.test(source)) {
      errors.source = t("settings.modelRedirects.validation.invalidSource");
    } else if (!editing && redirects.some((redirect) => redirect.sourceModel === source)) {
      errors.source = t("settings.modelRedirects.validation.alreadyRedirected");
    } else if (feeding.length) {
      errors.source = t("settings.modelRedirects.validation.chainSource", {
        source: displayName(source),
        requests: feeding.map((redirect) => displayName(redirect.sourceModel)).join(", "),
      });
    } else if (routes.some((route) => route.slug === source || route.compactionModel === source)) {
      errors.source = t("settings.modelRedirects.validation.compactionRoute", { source: displayName(source) });
    }
    if (!target) {
      errors.target = t("settings.modelRedirects.validation.targetRequired");
    } else if (source === target) {
      errors.target = t("settings.modelRedirects.validation.self");
    } else if (targetRedirect) {
      errors.target = t("settings.modelRedirects.validation.chainTarget", {
        target: displayName(target),
        served: displayName(targetRedirect.targetModel),
      });
    }
    return errors;
  }

  async function save(current: Draft) {
    const sourceModel = current.source.trim();
    const targetModel = current.target;
    const errors = validate(sourceModel, targetModel, current.editing);
    setFieldErrors(errors);
    if (errors.source || errors.target) return;
    try {
      await upsertMutation.mutateAsync({ sourceModel, targetModel });
      openForm(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : t("settings.toasts.saveFailed");
      if (error instanceof ApiError && error.code === "model_redirect_conflict") {
        setFieldErrors({ source: message });
      } else {
        setFieldErrors({ target: message });
      }
    }
  }

  const arrow = <ArrowRight className="mx-auto size-3.5 text-muted-foreground" aria-hidden="true" />;
  const formRow = (current: Draft) => {
    const imageSource = current.source.trim().startsWith(IMAGE_REDIRECT_SOURCE_PREFIX);
    const targetGroups = [...groups]
      .map(([provider, options]) => [provider, options.filter((option) => option.image === imageSource)] as const)
      .filter(([, options]) => options.length > 0);
    return (
    <TableRow key={current.editing ? current.source : undefined} className="bg-muted/40">
      <TableCell className="align-top">
        {current.editing ? modelCell(current.source) : (
          <Input
            aria-label={t("settings.modelRedirects.requestedModel")}
            list={inputId}
            value={current.source}
            placeholder={t("settings.modelRedirects.sourcePlaceholder")}
            onChange={(event) => setDraft({ ...current, source: event.target.value })}
            aria-invalid={Boolean(fieldErrors.source)}
            aria-describedby={fieldErrors.source ? sourceErrorId : undefined}
            disabled={busy}
            autoFocus
            className="h-8 min-w-[160px] font-mono text-xs"
          />
        )}
        <FieldError id={sourceErrorId} message={fieldErrors.source} />
      </TableCell>
      <TableCell className="w-7 px-0">{arrow}</TableCell>
      <TableCell className="align-top">
        <select
          aria-label={t("settings.modelRedirects.servedModel")}
          value={current.target}
          onChange={(event) => setDraft({ ...current, target: event.target.value })}
          aria-invalid={Boolean(fieldErrors.target)}
          aria-describedby={fieldErrors.target ? targetErrorId : undefined}
          className={cn(
            "h-8 w-full min-w-[160px] rounded-md border border-input bg-background px-2 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring",
            fieldErrors.target && "border-destructive",
          )}
          disabled={busy}
        >
          <option value="">{t("settings.modelRedirects.chooseModel")}</option>
          {targetGroups.map(([provider, options]) => (
            <optgroup key={provider} label={t(`settings.modelCatalogue.provider.${provider}`, provider)}>
              {options.filter((option) => option.slug !== current.source.trim() || option.slug === current.target).map((option) => (
                <option key={option.slug} value={option.slug} disabled={option.redirected}>
                  {option.redirected
                    ? t("settings.modelRedirects.redirectedOption", { model: option.displayName })
                    : option.hidden
                      ? t("settings.compactionRoutes.hiddenModel", { model: option.displayName })
                      : option.displayName}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <FieldError id={targetErrorId} message={fieldErrors.target} />
      </TableCell>
      <TableCell />
      <TableCell className="text-right">
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => openForm(null)}>{t("common.cancel")}</Button>
        <Button size="sm" disabled={busy} onClick={() => void save(current)}>{t("common.actions.save")}</Button>
      </TableCell>
    </TableRow>
    );
  };

  const redirectRow = (redirect: ModelRedirect) => {
    const { sourceModel, targetModel, status, reason } = redirect;
    const active = status === "active";
    return (
      <TableRow key={sourceModel}>
        <TableCell>{modelCell(sourceModel)}</TableCell>
        <TableCell className="w-7 px-0">{arrow}</TableCell>
        <TableCell>{modelCell(targetModel)}</TableCell>
        <TableCell>
          <Badge
            variant="outline"
            className={active
              ? "border-emerald-500/20 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
              : "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-400"}
          >
            {t(`settings.modelRedirects.status.${status}`)}
          </Badge>
          {reason ? <p className="mt-0.5 text-[11px] text-muted-foreground">{t(`settings.modelRedirects.reason.${reason}`, reason)}</p> : null}
        </TableCell>
        <TableCell className="text-right">
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => openForm({ source: sourceModel, target: active ? targetModel : "", editing: true })}>
            {t("settings.modelRedirects.change")}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive hover:text-destructive"
            disabled={busy}
            onClick={() => deleteMutation.mutate(sourceModel, { onSuccess: () => openForm(null) })}
          >
            {t("common.actions.remove")}
          </Button>
        </TableCell>
      </TableRow>
    );
  };

  const error = redirectsQuery.error ?? deleteMutation.error;
  return (
    <section id="model-redirects" className="scroll-mt-16 space-y-3 rounded-xl border bg-card p-5">
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <ArrowLeftRight className="size-4 text-primary" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold">{t("settings.modelRedirects.title")}</h3>
          <p className="text-xs text-muted-foreground">{t("settings.modelRedirects.description")}</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={busy || !redirectsQuery.data}
          onClick={() => openForm({ source: "", target: "", editing: false })}
        >
          <Plus className="size-3.5" aria-hidden="true" />
          {t("settings.modelRedirects.add")}
        </Button>
      </div>

      {error ? <AlertMessage variant="error">{error.message}</AlertMessage> : null}
      {redirectsQuery.isLoading ? <div className="py-8"><SpinnerBlock /></div> : (
        <div className="overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[32%]">{t("settings.modelRedirects.requestedModel")}</TableHead>
                <TableHead className="w-7 px-0" />
                <TableHead className="w-[32%]">{t("settings.modelRedirects.servedModel")}</TableHead>
                <TableHead>{t("settings.modelRedirects.statusLabel")}</TableHead>
                <TableHead className="text-right">{t("apiKeys.table.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {draft && !draft.editing ? formRow(draft) : null}
              {redirects.map((redirect) => draft?.editing && draft.source === redirect.sourceModel
                ? formRow(draft)
                : redirectRow(redirect))}
              {redirects.length === 0 && !draft ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-6 text-center text-xs text-muted-foreground">
                    {t("settings.modelRedirects.empty")}
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </div>
      )}
      <datalist id={inputId}>
        {[...modelsBySlug].map(([slug, name]) => <option key={slug} value={slug}>{name}</option>)}
      </datalist>
      <p className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
        <Info className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
        {t("settings.modelRedirects.cacheNote")}
      </p>
    </section>
  );
}
