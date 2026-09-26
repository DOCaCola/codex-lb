import { useEffect, useId, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff, Webhook } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { ApiError, get, post, put } from "@/lib/api-client";

const path = "/api/settings/quota-reset-webhook";
const key = ["settings", "quota-reset-webhook"];
const schema = z.object({
  enabled: z.boolean(), kinds: z.array(z.enum(["scheduled", "unexpected"])),
  urlConfigured: z.boolean(), signingSecretConfigured: z.boolean(), pending: z.number(),
  lastDelivery: z.object({ eventId: z.string(), status: z.string(), attempts: z.number(),
    createdAt: z.string(), httpStatus: z.number().nullable(), error: z.string().nullable(),
  }).nullable(),
});

export function QuotaResetWebhookSettings({ disabled = false }: { disabled?: boolean }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const query = useQuery({ queryKey: key, queryFn: () => get(path, schema), refetchInterval: 10000 });
  const [draft, setDraft] = useState<{ enabled: boolean; kinds: ("scheduled" | "unexpected")[] } | null>(null);
  const [urlDraft, setUrlDraft] = useState<string | null>(null);
  const [showUrl, setShowUrl] = useState(false);
  const [savedUrl, setSavedUrl] = useState<string | null>(null);
  const [destinationError, setDestinationError] = useState<Error | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  useEffect(() => {
    if (disabled) return;
    const controller = new AbortController();
    void get(`${path}/destination`, z.object({ url: z.string().nullable() }), {
      cache: "no-store", signal: controller.signal,
    }).then((result) => {
      if (!controller.signal.aborted) { setSavedUrl(result.url ?? ""); setDestinationError(null); }
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setDestinationError(error);
    });
    return () => controller.abort();
  }, [disabled, loadAttempt]);
  const url = urlDraft ?? savedUrl ?? "";
  const clearUrl = urlDraft === "" && !!savedUrl;
  const urlInputId = useId();
  const [secret, setSecret] = useState("");
  const [clearSecret, setClearSecret] = useState(false);
  const save = useMutation({ mutationFn: () => put(path, schema, { body: {
    enabled: clearUrl ? false : draft?.enabled ?? query.data?.enabled ?? false,
    kinds: draft?.kinds ?? query.data?.kinds ?? ["scheduled", "unexpected"],
    ...(urlDraft !== null && url ? { url } : {}), ...(secret ? { signingSecret: secret } : {}),
    clearUrl, clearSigningSecret: clearSecret,
  }}), onSuccess: async () => {
    setDraft(null); setSavedUrl(url); setUrlDraft(null); setSecret(""); setClearSecret(false);
    setShowUrl(false);
    await client.invalidateQueries({ queryKey: key });
  }});
  const test = useMutation({ mutationFn: () => post(`${path}/test`, z.object({ eventId: z.string() })),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  const data = query.data;
  const enabled = clearUrl ? false : draft?.enabled ?? data?.enabled ?? false;
  const kinds = draft?.kinds ?? data?.kinds ?? ["scheduled", "unexpected"];
  const busy = disabled || save.isPending || test.isPending || savedUrl === null || !data;
  const dirty = draft !== null || (urlDraft !== null && urlDraft !== savedUrl) || !!secret || clearSecret;
  const failed = query.isError || save.isError || test.isError || destinationError !== null;
  const error = save.error ?? test.error ?? destinationError ?? query.error;
  const errorMessage = error instanceof ApiError && error.code === "step_up_unavailable"
    ? t("settings.quotaWebhook.stepUpUnavailable", "Identity verification is unavailable. Set up two-factor authentication or a local password to continue.")
    : error instanceof ApiError && error.code === "step_up_required"
      ? t("settings.quotaWebhook.stepUpRequired", "Confirm your identity to continue.")
      : error instanceof ApiError && error.status === 401
        ? t("settings.quotaWebhook.signIn", "Your session has expired. Sign in again.")
        : error instanceof ApiError && error.status === 403
          ? t("settings.quotaWebhook.permission", "You do not have permission to manage webhook settings.")
          : error instanceof ApiError && (error.status === 400 || error.status === 422)
            ? t("settings.quotaWebhook.invalid", "Invalid webhook settings. Check the HTTP or HTTPS URL, secret length and event selection.")
            : t("settings.quotaWebhook.failed", "Unable to complete the webhook request. Try again.");
  return <section className="rounded-xl border bg-card p-5 space-y-4" aria-label={t("settings.quotaWebhook.title", "Quota reset webhook")}>
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10"><Webhook className="h-4 w-4 text-primary" aria-hidden="true" /></div>
      <div><h3 className="text-sm font-semibold">{t("settings.quotaWebhook.title", "Quota reset webhook")}</h3>
        <p className="text-xs text-muted-foreground">{t("settings.quotaWebhook.description", "Receive JSON notifications via HTTP POST when OpenAI account quotas reset. Delivery may retry with the same event ID.")}</p></div>
    </div>
    <label className="flex items-center justify-between gap-3 text-sm">{t("settings.quotaWebhook.enabled", "Enable notifications")}
      <Switch aria-label={t("settings.quotaWebhook.enabled", "Enable notifications")} checked={enabled} disabled={busy || clearUrl}
        onCheckedChange={(value) => setDraft({ enabled: value, kinds })} /></label>
    <div className="space-y-1">
      <label htmlFor={urlInputId} className="text-sm">{t("settings.quotaWebhook.url", "Webhook URL")}</label>
      <div className="relative">
      <Input id={urlInputId} type={showUrl ? "text" : "password"} autoComplete="off" value={url} disabled={busy}
        className="pr-10" spellCheck={false}
        placeholder="https://example.com/webhook"
        onChange={(event) => setUrlDraft(event.target.value)} />
      <Button type="button" variant="ghost" size="icon" className="absolute right-0 top-0 h-full"
        disabled={busy} aria-controls={urlInputId} aria-pressed={showUrl}
        aria-label={showUrl ? t("settings.quotaWebhook.hideUrl", "Hide webhook URL") : t("settings.quotaWebhook.showUrl", "Show webhook URL")}
        onClick={() => setShowUrl((value) => !value)}>
        {showUrl ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
      </Button>
      </div>
    </div>
    {clearUrl && <p role="status" className="text-xs">{t("settings.quotaWebhook.urlRemoval", "Saving an empty URL removes the destination and disables delivery.")}</p>}
    <label className="block text-sm space-y-1">{t("settings.quotaWebhook.secret", "Optional signing secret (16+ characters)")}
      <Input type="password" autoComplete="new-password" value={secret} disabled={busy || clearSecret}
        placeholder={data?.signingSecretConfigured ? t("settings.quotaWebhook.keep", "Configured — leave blank to keep") : ""}
        onChange={(event) => setSecret(event.target.value)} /></label>
    {data?.signingSecretConfigured && <Button type="button" variant="outline" disabled={busy}
      onClick={() => { setSecret(""); setClearSecret((value) => !value); }}>
      {clearSecret ? t("settings.quotaWebhook.undoRemoveSecret", "Undo signing secret removal") : t("settings.quotaWebhook.removeSecret", "Remove signing secret")}
    </Button>}
    {clearSecret && <p role="status" className="text-xs">{t("settings.quotaWebhook.secretRemoval", "Signing secret will be removed when you save.")}</p>}
    <div className="flex flex-wrap gap-4">{(["scheduled", "unexpected"] as const).map((kind) => <label key={kind} className="flex gap-2 text-sm">
      <input type="checkbox" checked={kinds.includes(kind)} disabled={busy} onChange={(event) => setDraft({ enabled,
        kinds: event.target.checked ? [...kinds, kind] : kinds.filter((item) => item !== kind) })} />
      {kind === "scheduled" ? t("settings.quotaWebhook.scheduled", "Scheduled resets") : t("settings.quotaWebhook.unexpected", "Unexpected resets")}
    </label>)}</div>
    <p className="text-xs text-muted-foreground">{t("settings.quotaWebhook.security", "HTTP and HTTPS destinations supported, including internal addresses. HTTP is unencrypted. Saving clears detection baselines and cancels queued events. First observations do not notify.")}</p>
    {failed && <p role="alert" className="text-sm text-destructive">{errorMessage}</p>}
    {query.isError && <Button variant="outline" onClick={() => void query.refetch()}>{t("common.retry", "Retry")}</Button>}
    {destinationError && <Button variant="outline" onClick={() => setLoadAttempt((value) => value + 1)}>{t("settings.quotaWebhook.retryUrl", "Retry loading URL")}</Button>}
    <div className="flex flex-wrap gap-2">
      <Button disabled={busy || !dirty || kinds.length === 0} onClick={() => save.mutate()}>{t("common.save", "Save")}</Button>
      <Button variant="outline" disabled={busy || dirty || !data?.enabled} onClick={() => test.mutate()}>{t("settings.quotaWebhook.test", "Test delivery")}</Button>
    </div>
    {test.isSuccess && <p role="status" className="text-xs">{t("settings.quotaWebhook.queued", "Test queued; delivery status updates automatically.")}</p>}
    {data && <p className="text-xs text-muted-foreground" role="status">
      {t("settings.quotaWebhook.pending", "Pending: {{count}}", { count: data.pending })}
      {data.lastDelivery && <> · {t("settings.quotaWebhook.last", "Last delivery")}: {data.lastDelivery.status} · {data.lastDelivery.attempts} {t("settings.quotaWebhook.attempts", "attempts")}
        {data.lastDelivery.httpStatus !== null && <> · HTTP {data.lastDelivery.httpStatus}</>}
        {data.lastDelivery.error && <> · {data.lastDelivery.error}</>}</>}
    </p>}
  </section>;
}
