import { Check, Copy, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useState, type MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { copyToClipboard } from "@/utils/clipboard";

export function CopyButton({ text }: { text: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async (event: MouseEvent<HTMLButtonElement>) => {
    const trigger = event.currentTarget;
    const dialogContainer = trigger.closest("[role='dialog']");
    const blurAfterCopy = event.detail > 0;

    try {
      const copiedToClipboard = await copyToClipboard(text, {
        container: dialogContainer instanceof HTMLElement ? dialogContainer : undefined,
      });
      if (!copiedToClipboard) {
        toast.error(t("components.copyButton.toasts.failed"));
        return;
      }

      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("components.copyButton.toasts.failed"));
    } finally {
      if (blurAfterCopy) {
        trigger.blur();
      }
    }
  }, [text, t]);

  return (
    <Button
      type="button"
      size="sm"
      variant="ghost"
      className="h-7 cursor-pointer gap-1 px-2 text-xs disabled:cursor-not-allowed"
      onMouseDown={(event) => event.preventDefault()}
      onClick={(event) => void handleCopy(event)}
    >
      {copied ? (
        <>
          <Check className="h-3 w-3" />
          {t("components.copyButton.copiedBang")}
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          {t("components.copyButton.copy")}
        </>
      )}
    </Button>
  );
}

/** Labels of the paste field: what the operator pastes back from the provider's page. */
export type CallbackFieldLabels = {
  title: string;
  aria: string;
  placeholder: string;
};

type ManualCallbackInputProps = {
  labels: CallbackFieldLabels;
  onSubmit: (value: string) => Promise<void>;
  disabled?: boolean;
};

function ManualCallbackInput(props: ManualCallbackInputProps) {
  return <ManualCallbackInputBody key={props.disabled ? "disabled" : "enabled"} {...props} />;
}

function ManualCallbackInputBody({ labels, onSubmit, disabled = false }: ManualCallbackInputProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!value.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(value.trim());
      setValue("");
    } catch {
      // Parent state renders the error stage/message.
    } finally {
      setSubmitting(false);
    }
  }, [value, onSubmit]);

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground">{labels.title}</p>
      <div className="flex items-center gap-2">
        <input
          type="text"
          aria-label={labels.aria}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void handleSubmit();
            }
          }}
          disabled={disabled}
          placeholder={labels.placeholder}
          autoComplete="off"
          spellCheck={false}
          className="min-w-0 flex-1 rounded-lg border bg-muted/20 px-3 py-2 font-mono text-xs outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
        />
        <Button
          type="button"
          size="sm"
          className="h-8 cursor-pointer px-3 text-xs disabled:cursor-not-allowed"
          disabled={disabled || !value.trim() || submitting}
          onClick={() => void handleSubmit()}
        >
          {submitting ? t("common.states.submitting") : t("common.actions.submit")}
        </Button>
      </div>
    </div>
  );
}

export type OAuthLinkStageProps = {
  authorizationUrl: string | null;
  /** A new flow is being started; the link box shows progress and the paste field is disabled. */
  refreshing: boolean;
  onRefresh: () => void;
  callback: CallbackFieldLabels;
  onSubmitCallback: (value: string) => Promise<void>;
  /** Waiting line, e.g. including an expiry countdown. */
  waiting: string;
};

/** Browser sign-in stage shared by every provider: link box, paste field and waiting line. */
export function OAuthLinkStage({
  authorizationUrl,
  refreshing,
  onRefresh,
  callback,
  onSubmitCallback,
  waiting,
}: OAuthLinkStageProps) {
  const { t } = useTranslation();
  return (
    <div className="min-w-0 space-y-3 text-sm">
      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium text-muted-foreground">{t("accounts.oauth.authorizationUrl")}</p>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 cursor-pointer gap-1 px-2 text-xs disabled:cursor-not-allowed"
            disabled={refreshing}
            onClick={onRefresh}
          >
            {refreshing ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                {t("common.states.refreshing")}
              </>
            ) : (
              <>
                <RefreshCw className="h-3 w-3" />
                {t("accounts.oauth.refreshLink")}
              </>
            )}
          </Button>
        </div>
        {refreshing ? (
          <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>{t("accounts.oauth.generatingLink")}</span>
          </div>
        ) : authorizationUrl ? (
          <div className="flex min-w-0 items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
            <p className="min-w-0 flex-1 truncate font-mono text-xs">{authorizationUrl}</p>
            <CopyButton text={authorizationUrl} />
          </div>
        ) : null}
        <p className="text-xs text-muted-foreground">{t("accounts.oauth.refreshHint")}</p>
      </div>
      <ManualCallbackInput labels={callback} onSubmit={onSubmitCallback} disabled={refreshing} />
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>{waiting}</span>
      </div>
    </div>
  );
}
