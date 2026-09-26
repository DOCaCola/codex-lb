import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { useTranslation } from "react-i18next";
import { Webhook } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { get, post, put } from "@/lib/api-client";

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
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [clearUrl, setClearUrl] = useState(false);
  const [clearSecret, setClearSecret] = useState(false);
  const save = useMutation({ mutationFn: () => put(path, schema, { body: {
    enabled: draft?.enabled ?? query.data?.enabled ?? false,
    kinds: draft?.kinds ?? query.data?.kinds ?? ["scheduled", "unexpected"],
    ...(url ? { url } : {}), ...(secret ? { signingSecret: secret } : {}),
    clearUrl, clearSigningSecret: clearSecret,
  }}), onSuccess: async () => {
    setDraft(null); setUrl(""); setSecret(""); setClearUrl(false); setClearSecret(false);
    await client.invalidateQueries({ queryKey: key });
  }});
  const test = useMutation({ mutationFn: () => post(`${path}/test`, z.object({ eventId: z.string() })),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  const data = query.data;
  const enabled = draft?.enabled ?? data?.enabled ?? false;
  const kinds = draft?.kinds ?? data?.kinds ?? ["scheduled", "unexpected"];
  const busy = disabled || save.isPending || test.isPending || !data;
  const dirty = draft !== null || !!url || !!secret || clearUrl || clearSecret;
  const failed = query.isError || save.isError || test.isError;
  return <section className="rounded-xl border bg-card p-5 space-y-4" aria-label={t("settings.quotaWebhook.title", "Quota reset webhook")}>
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10"><Webhook className="h-4 w-4 text-primary" aria-hidden="true" /></div>
      <div><h3 className="text-sm font-semibold">{t("settings.quotaWebhook.title", "Quota reset webhook")}</h3>
        <p className="text-xs text-muted-foreground">{t("settings.quotaWebhook.description", "Receive notifications when OpenAI account quotas reset. Delivery may retry with the same event ID.")}</p></div>
    </div>
    <label className="flex items-center justify-between gap-3 text-sm">{t("settings.quotaWebhook.enabled", "Enable notifications")}
      <Switch aria-label={t("settings.quotaWebhook.enabled", "Enable notifications")} checked={enabled} disabled={busy}
        onCheckedChange={(value) => setDraft({ enabled: value, kinds })} /></label>
    <label className="block text-sm space-y-1">{t("settings.quotaWebhook.url", "HTTPS webhook URL")}
      <Input type="password" autoComplete="off" value={url} disabled={busy || clearUrl}
        placeholder={data?.urlConfigured ? t("settings.quotaWebhook.keep", "Configured — leave blank to keep") : "https://example.com/webhook"}
        onChange={(event) => setUrl(event.target.value)} /></label>
    <label className="flex gap-2 text-sm"><input type="checkbox" checked={clearUrl} disabled={busy || !!url}
      onChange={(event) => { setClearUrl(event.target.checked); if (event.target.checked) setDraft({ enabled: false, kinds }); }} />
      {t("settings.quotaWebhook.removeUrl", "Remove destination (disables delivery)")}</label>
    <label className="block text-sm space-y-1">{t("settings.quotaWebhook.secret", "Optional signing secret (16+ characters)")}
      <Input type="password" autoComplete="new-password" value={secret} disabled={busy || clearSecret}
        placeholder={data?.signingSecretConfigured ? t("settings.quotaWebhook.keep", "Configured — leave blank to keep") : ""}
        onChange={(event) => setSecret(event.target.value)} /></label>
    <label className="flex gap-2 text-sm"><input type="checkbox" checked={clearSecret} disabled={busy || !!secret}
      onChange={(event) => setClearSecret(event.target.checked)} />{t("settings.quotaWebhook.removeSecret", "Remove signing secret")}</label>
    <div className="flex flex-wrap gap-4">{(["scheduled", "unexpected"] as const).map((kind) => <label key={kind} className="flex gap-2 text-sm">
      <input type="checkbox" checked={kinds.includes(kind)} disabled={busy} onChange={(event) => setDraft({ enabled,
        kinds: event.target.checked ? [...kinds, kind] : kinds.filter((item) => item !== kind) })} />
      {kind === "scheduled" ? t("settings.quotaWebhook.scheduled", "Scheduled resets") : t("settings.quotaWebhook.unexpected", "Unexpected resets")}
    </label>)}</div>
    <p className="text-xs text-muted-foreground">{t("settings.quotaWebhook.security", "Public HTTPS destinations only. Saving clears detection baselines and cancels queued events. First observations do not notify.")}</p>
    {failed && <p role="alert" className="text-sm text-destructive">{t("settings.quotaWebhook.error", "Webhook operation failed. Check the URL, secret length and event selection.")}</p>}
    {query.isError && <Button variant="outline" onClick={() => void query.refetch()}>{t("common.retry", "Retry")}</Button>}
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
