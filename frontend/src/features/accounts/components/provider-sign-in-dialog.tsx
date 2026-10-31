import { Check, CircleAlert, ExternalLink, Loader2 } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { OAuthLinkStage } from "@/features/accounts/components/oauth-link-stage";
import { formatCountdown } from "@/utils/formatters";

export type SignInProvider = "claude" | "antigravity";

export type SignInFlow = { state: string; authorizationUrl: string; expiresAt: string };

/** Account being re-authenticated; absent when a new account is added. */
export type ReauthTarget = { name: string; identity: ReactNode };

type ConnectedAccount = { id: string; name: string };

export type ProviderSignInDialogProps = {
  provider: SignInProvider;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reauth?: ReauthTarget;
  /** Statement the operator must accept before signing in, if the provider requires one. */
  acknowledgement?: string;
  start: (name: string) => Promise<SignInFlow>;
  complete: (flow: SignInFlow, code: string) => Promise<ConnectedAccount>;
  onConnected: (id: string) => void;
};

type Stage = "details" | "link" | "success" | "error";

function useSecondsUntil(iso: string | null): number | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!iso) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [iso]);
  return iso ? Math.max(0, (Date.parse(iso) - now) / 1000) : null;
}

function useProviderCopy(provider: SignInProvider) {
  const { t } = useTranslation();
  return provider === "claude"
    ? {
        title: t("accounts.signIn.claude.title"),
        callback: {
          title: t("accounts.signIn.claude.pasteTitle"),
          aria: t("accounts.signIn.claude.pasteAria"),
          placeholder: "code#state",
        },
        waiting: t("accounts.signIn.claude.waiting"),
      }
    : {
        title: t("accounts.signIn.antigravity.title"),
        callback: {
          title: t("accounts.signIn.antigravity.pasteTitle"),
          aria: t("accounts.signIn.antigravity.pasteAria"),
          placeholder: "https://antigravity.google/…?code=…&state=…",
        },
        waiting: t("accounts.signIn.antigravity.waiting"),
      };
}

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error && cause.message ? cause.message : fallback;
}

/** Browser sign-in for subscription providers, following the stages of the Codex OAuth dialog. */
export function ProviderSignInDialog({
  provider,
  open,
  onOpenChange,
  reauth,
  acknowledgement,
  start,
  complete,
  onConnected,
}: ProviderSignInDialogProps) {
  const { t } = useTranslation();
  const copy = useProviderCopy(provider);
  const [stage, setStage] = useState<Stage>("details");
  const [name, setName] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [flow, setFlow] = useState<SignInFlow | null>(null);
  const [starting, setStarting] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [message, setMessage] = useState("");
  const secondsLeft = useSecondsUntil(stage === "link" && flow ? flow.expiresAt : null);
  const accountName = reauth ? reauth.name : name.trim();

  const close = () => {
    if (completing) return;
    onOpenChange(false);
    setStage("details");
    setName("");
    setAcknowledged(false);
    setFlow(null);
    setMessage("");
  };

  const fail = (cause: unknown) => {
    setMessage(errorMessage(cause, t("common.errors.unknown")));
    setStage("error");
  };

  const begin = async () => {
    setStarting(true);
    try {
      setFlow(await start(accountName));
      setStage("link");
    } catch (cause) {
      fail(cause);
    } finally {
      setStarting(false);
    }
  };

  const submitCode = async (code: string) => {
    if (!flow) return;
    setCompleting(true);
    try {
      const account = await complete(flow, code);
      setMessage(t("accounts.signIn.connected", { name: account.name }));
      setStage("success");
      onConnected(account.id);
    } catch (cause) {
      fail(cause);
    } finally {
      setCompleting(false);
    }
  };

  const restart = () => {
    setFlow(null);
    setMessage("");
    setStage("details");
  };

  const title =
    stage === "success"
      ? t("accounts.signIn.titles.success")
      : stage === "error"
        ? t("accounts.signIn.titles.error")
        : reauth
          ? t("accounts.signIn.titles.reauth", { name: reauth.name })
          : copy.title;
  const waiting =
    secondsLeft === null || secondsLeft > 0
      ? `${copy.waiting} · ${t("accounts.signIn.linkExpiresIn", { time: formatCountdown(secondsLeft ?? 0) })}`
      : t("accounts.signIn.linkExpired");

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ProviderLogo provider={provider} />
            {title}
          </DialogTitle>
          {stage === "details" ? (
            <DialogDescription>
              {reauth ? t("accounts.signIn.reauthDescription") : t("accounts.signIn.description")}
            </DialogDescription>
          ) : null}
        </DialogHeader>

        {stage === "details" ? (
          <div className="space-y-4">
            {reauth ? (
              <div className="space-y-1.5 text-sm">
                <p className="font-medium">{t("accounts.signIn.savedIdentity")}</p>
                <p className="rounded-md border bg-muted/50 px-3 py-2 text-muted-foreground">
                  {reauth.identity ?? t("accounts.signIn.identityUnknown")}
                </p>
              </div>
            ) : (
              <label className="block space-y-1.5 text-sm">
                <span className="font-medium">{t("accounts.signIn.accountName")}</span>
                <Input value={name} disabled={starting} onChange={(event) => setName(event.target.value)} />
              </label>
            )}
            {acknowledgement ? (
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={acknowledged}
                  disabled={starting}
                  onChange={(event) => setAcknowledged(event.target.checked)}
                />
                {acknowledgement}
              </label>
            ) : null}
          </div>
        ) : null}

        {stage === "link" ? (
          <OAuthLinkStage
            authorizationUrl={flow?.authorizationUrl ?? null}
            refreshing={starting}
            onRefresh={() => void begin()}
            callback={copy.callback}
            onSubmitCallback={submitCode}
            waiting={waiting}
          />
        ) : null}

        {stage === "success" ? (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-3 text-sm text-emerald-700 dark:text-emerald-400">
            <Check className="h-4 w-4 shrink-0" />
            <p>{message}</p>
          </div>
        ) : null}

        {stage === "error" ? (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-3 text-sm text-destructive"
          >
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{message}</p>
          </div>
        ) : null}

        <DialogFooter>
          {stage === "details" ? (
            <>
              <Button type="button" variant="outline" disabled={starting} onClick={close}>
                {t("common.cancel")}
              </Button>
              <Button
                type="button"
                disabled={starting || !accountName || (!!acknowledgement && !acknowledged)}
                onClick={() => void begin()}
              >
                {starting ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null}
                {t("accounts.oauth.startSignIn")}
              </Button>
            </>
          ) : null}
          {stage === "link" ? (
            <>
              <Button type="button" variant="outline" disabled={starting || completing} onClick={restart}>
                {t("common.actions.back")}
              </Button>
              {flow && !starting ? (
                <Button type="button" asChild>
                  <a href={flow.authorizationUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    {t("accounts.oauth.openSignInPage")}
                  </a>
                </Button>
              ) : null}
            </>
          ) : null}
          {stage === "success" ? (
            <Button type="button" onClick={close}>
              {t("common.actions.done")}
            </Button>
          ) : null}
          {stage === "error" ? (
            <>
              <Button type="button" variant="outline" onClick={close}>
                {t("common.actions.close")}
              </Button>
              <Button type="button" onClick={restart}>
                {t("common.actions.tryAgain")}
              </Button>
            </>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
