import { LogIn, Upload } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ProviderLogo } from "@/components/brand/provider-account-name";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import type { AccountProvider } from "@/components/brand/account-provider";

/** The two enrollment methods every subscription provider offers. */
export type EnrollmentHandlers = { onSignIn: () => void; onImport: () => void };

export type AddAccountDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  codex: EnrollmentHandlers;
  claude?: EnrollmentHandlers;
  antigravity?: EnrollmentHandlers;
  onOpenRouter?: () => void;
  onOpenAICompatible?: () => void;
};

function AccountOption({ icon, title, description, onClick }: {
  icon: ReactNode;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button type="button" onClick={onClick}
      className="flex w-full cursor-pointer items-start gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border bg-muted/50 text-muted-foreground">
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium">{title}</span>
        <span className="mt-0.5 block text-xs text-muted-foreground">{description}</span>
      </span>
    </button>
  );
}

const methodIcon = (Icon: typeof LogIn) => <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />;

function SubscriptionProvider({ provider, name, handlers, signInDescription, importDescription, select }: {
  provider: AccountProvider;
  name: string;
  handlers: EnrollmentHandlers;
  signInDescription: string;
  importDescription: string;
  select: (action: () => void) => void;
}) {
  const { t } = useTranslation();
  return (
    <fieldset className="min-w-0">
      <legend className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        <ProviderLogo provider={provider} />
        {name}
      </legend>
      <div className="grid gap-2 sm:grid-cols-2">
        <AccountOption icon={methodIcon(LogIn)} title={t("accounts.addDialog.signIn")}
          description={signInDescription} onClick={() => select(handlers.onSignIn)} />
        <AccountOption icon={methodIcon(Upload)} title={t("accounts.addDialog.importFile")}
          description={importDescription} onClick={() => select(handlers.onImport)} />
      </div>
    </fieldset>
  );
}

export function AddAccountDialog({
  open, onOpenChange, codex, claude, antigravity, onOpenRouter, onOpenAICompatible,
}: AddAccountDialogProps) {
  const { t } = useTranslation();
  // Close first so Radix releases its pointer lock before the next modal opens.
  const select = (action: () => void) => {
    onOpenChange(false);
    requestAnimationFrame(() => action());
  };
  const apiProviders = onOpenRouter || onOpenAICompatible;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{t("accounts.addDialog.title")}</DialogTitle>
          <DialogDescription>{t("accounts.addDialog.description")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-5">
          <section className="space-y-3" aria-labelledby="add-account-subscriptions">
            <h3 id="add-account-subscriptions" className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {t("accounts.addDialog.subscriptions")}
            </h3>
            <SubscriptionProvider provider="codex" name="Codex" handlers={codex} select={select}
              signInDescription={t("accounts.addDialog.codex.signIn")}
              importDescription={t("accounts.addDialog.codex.import")} />
            {claude ? (
              <SubscriptionProvider provider="claude" name="Claude" handlers={claude} select={select}
                signInDescription={t("accounts.addDialog.claude.signIn")}
                importDescription={t("accounts.addDialog.claude.import")} />
            ) : null}
            {antigravity ? (
              <SubscriptionProvider provider="antigravity" name="Antigravity" handlers={antigravity} select={select}
                signInDescription={t("accounts.addDialog.antigravity.signIn")}
                importDescription={t("accounts.addDialog.antigravity.import")} />
            ) : null}
          </section>
          {apiProviders ? (
            <fieldset className="min-w-0">
              <legend className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {t("accounts.addDialog.apiProviders")}
              </legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {onOpenRouter ? (
                  <AccountOption icon={<ProviderLogo provider="openrouter" />} title="OpenRouter"
                    description={t("accounts.addDialog.openRouter")} onClick={() => select(onOpenRouter)} />
                ) : null}
                {onOpenAICompatible ? (
                  <AccountOption icon={<ProviderLogo provider="openai_compatible" />} title="OpenAI-compatible"
                    description={t("accounts.addDialog.openAICompatible")} onClick={() => select(onOpenAICompatible)} />
                ) : null}
              </div>
            </fieldset>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
