import { Check, CircleAlert, ExternalLink, Loader2 } from "lucide-react";
import { useState } from "react";
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
import { cn } from "@/lib/utils";
import type { OAuthState } from "@/features/accounts/schemas";
import { CopyButton, OAuthLinkStage } from "@/features/accounts/components/oauth-link-stage";
import { formatCountdown } from "@/utils/formatters";

type Stage = "intro" | "browser" | "device" | "success" | "error";

function getStage(state: OAuthState): Stage {
  if (state.status === "success") return "success";
  if (state.status === "error") return "error";
  if (state.method === "browser" && (state.status === "pending" || state.status === "starting")) return "browser";
  if (state.method === "device" && (state.status === "pending" || state.status === "starting")) return "device";
  return "intro";
}

export type OauthDialogProps = {
  open: boolean;
  state: OAuthState;
  onOpenChange: (open: boolean) => void;
  onStart: (method?: "browser" | "device") => Promise<void>;
  onComplete: () => Promise<void>;
  onManualCallback: (callbackUrl: string) => Promise<void>;
  onReset: () => void;
};

export function OauthDialog({
  open,
  state,
  onOpenChange,
  onStart,
  onManualCallback,
  onReset,
}: OauthDialogProps) {
  const { t } = useTranslation();
  const [selectedMethod, setSelectedMethod] = useState<"browser" | "device">("browser");
  const stage = getStage(state);
  const browserRefreshInProgress = stage === "browser" && state.status === "starting";

  const close = (next: boolean) => {
    onOpenChange(next);
    if (!next) {
      onReset();
      setSelectedMethod("browser");
    }
  };

  const handleStart = () => {
    void onStart(selectedMethod);
  };

  const handleRefreshBrowserLink = () => {
    void onStart("browser");
  };

  const handleChangeMethod = () => {
    onReset();
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ProviderLogo provider="codex" />
            {stage === "success"
              ? t("accounts.oauth.titles.success")
              : stage === "error"
                ? t("accounts.oauth.titles.error")
                : t("accounts.oauth.titles.intro")}
          </DialogTitle>
          {stage === "intro" ? (
            <DialogDescription>{t("accounts.oauth.introDescription")}</DialogDescription>
          ) : null}
        </DialogHeader>

        {/* Intro stage */}
        {stage === "intro" ? (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setSelectedMethod("browser")}
              className={cn(
                "w-full cursor-pointer rounded-lg border p-3 text-left transition-colors",
                selectedMethod === "browser"
                  ? "border-primary bg-primary/5"
                  : "hover:bg-muted/50",
              )}
            >
              <p className="text-sm font-medium">{t("accounts.oauth.methods.browser.title")}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {t("accounts.oauth.methods.browser.description")}
              </p>
            </button>
            <button
              type="button"
              onClick={() => setSelectedMethod("device")}
              className={cn(
                "w-full cursor-pointer rounded-lg border p-3 text-left transition-colors",
                selectedMethod === "device"
                  ? "border-primary bg-primary/5"
                  : "hover:bg-muted/50",
              )}
            >
              <p className="text-sm font-medium">{t("accounts.oauth.methods.device.title")}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {t("accounts.oauth.methods.device.description")}
              </p>
            </button>
          </div>
        ) : null}

        {/* Browser stage */}
        {stage === "browser" ? (
          <OAuthLinkStage
            authorizationUrl={state.authorizationUrl}
            refreshing={browserRefreshInProgress}
            onRefresh={handleRefreshBrowserLink}
            callback={{
              title: t("accounts.oauth.manualCallback.title"),
              aria: t("accounts.oauth.manualCallback.aria"),
              placeholder: "http://localhost:1455/auth/callback?code=...&state=...",
            }}
            onSubmitCallback={onManualCallback}
            waiting={t("accounts.oauth.waitingComplete")}
          />
        ) : null}

        {/* Device stage */}
        {stage === "device" ? (
          <div className="space-y-3 text-sm">
            <ol className="list-inside list-decimal space-y-1 text-xs text-muted-foreground">
              <li>{t("accounts.oauth.deviceSteps.open")}</li>
              <li>{t("accounts.oauth.deviceSteps.code")}</li>
              <li>{t("accounts.oauth.deviceSteps.complete")}</li>
            </ol>

            {state.userCode ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">{t("accounts.oauth.userCode")}</p>
                <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
                  <p className="min-w-0 flex-1 font-mono text-lg font-bold tracking-widest">{state.userCode}</p>
                  <CopyButton text={state.userCode} />
                </div>
              </div>
            ) : null}

            {state.verificationUrl ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">{t("accounts.oauth.verificationUrl")}</p>
                <div className="flex min-w-0 items-center gap-2 overflow-hidden rounded-lg border bg-muted/20 px-3 py-2">
                  <p className="min-w-0 flex-1 truncate break-all font-mono text-xs">{state.verificationUrl}</p>
                  <CopyButton text={state.verificationUrl} />
                </div>
              </div>
            ) : null}

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>
                {t("accounts.oauth.waiting")}
                {state.expiresInSeconds != null && state.expiresInSeconds > 0
                  ? ` · ${t("accounts.oauth.expiresIn", { time: formatCountdown(state.expiresInSeconds) })}`
                  : "..."}
              </span>
            </div>
          </div>
        ) : null}

        {/* Success stage */}
        {stage === "success" ? (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-3 text-sm text-emerald-700 dark:text-emerald-400">
            <Check className="h-4 w-4 shrink-0" />
            <p>{t("accounts.oauth.successMessage")}</p>
          </div>
        ) : null}

        {/* Error stage */}
        {stage === "error" ? (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-3 text-sm text-destructive">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{state.errorMessage || t("common.errors.unknown")}</p>
          </div>
        ) : null}

        <DialogFooter>
          {stage === "intro" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={() => close(false)}
              >
                {t("common.cancel")}
              </Button>
              <Button
                type="button"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={handleStart}
              >
                {t("accounts.oauth.startSignIn")}
              </Button>
            </>
          ) : null}

          {stage === "browser" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                disabled={browserRefreshInProgress}
                onClick={handleChangeMethod}
              >
                {t("accounts.oauth.changeMethod")}
              </Button>
              {state.authorizationUrl && !browserRefreshInProgress ? (
                <Button
                  type="button"
                  className="cursor-pointer disabled:cursor-not-allowed"
                  asChild
                >
                  <a href={state.authorizationUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    {t("accounts.oauth.openSignInPage")}
                  </a>
                </Button>
              ) : null}
            </>
          ) : null}

          {stage === "device" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={handleChangeMethod}
              >
                {t("accounts.oauth.changeMethod")}
              </Button>
              {state.verificationUrl ? (
                <Button
                  type="button"
                  className="cursor-pointer disabled:cursor-not-allowed"
                  asChild
                >
                  <a href={state.verificationUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    {t("accounts.oauth.openLink")}
                  </a>
                </Button>
              ) : null}
            </>
          ) : null}

          {stage === "success" ? (
            <Button
              type="button"
              className="cursor-pointer disabled:cursor-not-allowed"
              onClick={() => close(false)}
            >
              {t("common.actions.done")}
            </Button>
          ) : null}

          {stage === "error" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={handleChangeMethod}
              >
                {t("common.actions.tryAgain")}
              </Button>
              <Button
                type="button"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={() => close(false)}
              >
                {t("common.actions.close")}
              </Button>
            </>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
