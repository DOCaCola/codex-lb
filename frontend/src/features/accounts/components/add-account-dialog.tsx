import { KeyRound, Plus, Upload, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

export type AddAccountDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: () => void;
  onAddAccount: () => void;
  onOpenRouter?: () => void;
  onClaude?: () => void;
};

function AccountOption({ icon: Icon, title, description, onClick }: {
  icon: LucideIcon;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button type="button" onClick={onClick}
      className="flex w-full cursor-pointer items-start gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border bg-muted/50">
        <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-muted-foreground" />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium">{title}</span>
        <span className="mt-0.5 block text-xs text-muted-foreground">{description}</span>
      </span>
    </button>
  );
}

export function AddAccountDialog({
  open, onOpenChange, onImport, onAddAccount, onOpenRouter, onClaude,
}: AddAccountDialogProps) {
  const { t } = useTranslation();
  // Close first so Radix releases its pointer lock before the next modal opens.
  const handleSelect = (action: () => void) => {
    onOpenChange(false);
    requestAnimationFrame(() => action());
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t("accounts.addDialog.title")}</DialogTitle>
          <DialogDescription>
            {t("accounts.addDialog.providerDescription", "Choose a provider and how to connect your account.")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-5">
          <fieldset className="min-w-0 space-y-2">
            <legend className="mb-2 text-xs font-semibold text-muted-foreground">Codex</legend>
            <AccountOption icon={Plus} title={t("accounts.addDialog.oauthTitle")}
              description={t("accounts.addDialog.oauthDescription")} onClick={() => handleSelect(onAddAccount)} />
            <AccountOption icon={Upload} title={t("common.actions.import")}
              description={t("accounts.addDialog.importDescription")} onClick={() => handleSelect(onImport)} />
          </fieldset>
          {onClaude && (
            <fieldset className="min-w-0 space-y-2">
              <legend className="mb-2 text-xs font-semibold text-muted-foreground">Claude</legend>
              <AccountOption icon={KeyRound} title={t("accounts.addDialog.claudeTitle", "OAuth or file import")}
                description={t("accounts.addDialog.claudeDescription", "Sign in with OAuth or import a Claude Code credential file.")}
                onClick={() => handleSelect(onClaude)} />
            </fieldset>
          )}
          {onOpenRouter && (
            <fieldset className="min-w-0 space-y-2">
              <legend className="mb-2 text-xs font-semibold text-muted-foreground">OpenRouter</legend>
              <AccountOption icon={KeyRound} title={t("accounts.addDialog.openRouterTitle", "API key")}
                description={t("accounts.addDialog.openRouterDescription", "Connect an API key and choose models to make available to clients.")}
                onClick={() => handleSelect(onOpenRouter)} />
            </fieldset>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
