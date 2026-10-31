import { useState, type FormEvent } from "react";
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
import { CredentialFileArea } from "@/features/accounts/components/credential-file-area";
import { CredentialFileError, readCredentialFile } from "@/features/accounts/credential-file";
import type { ReauthTarget, SignInProvider } from "@/features/accounts/components/provider-sign-in-dialog";

export type CredentialImportDialogProps = {
  provider: SignInProvider;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reauth?: ReauthTarget;
  acknowledgement?: string;
  importCredentials: (name: string, credentials: unknown) => Promise<{ id: string }>;
  onImported: (id: string) => void;
};

/** Single-file credential import for a subscription provider; errors stay inline, as in the Codex import. */
export function CredentialImportDialog({
  provider,
  open,
  onOpenChange,
  reauth,
  acknowledgement,
  importCredentials,
  onImported,
}: CredentialImportDialogProps) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const accountName = reauth ? reauth.name : name.trim();
  const [file] = files;

  const reset = () => {
    setName("");
    setFiles([]);
    setAcknowledged(false);
    setError(null);
  };

  const close = () => {
    if (submitting) return;
    onOpenChange(false);
    reset();
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const account = await importCredentials(accountName, await readCredentialFile(file));
      onOpenChange(false);
      reset();
      onImported(account.id);
    } catch (cause) {
      setError(
        cause instanceof CredentialFileError
          ? t(cause.message)
          : cause instanceof Error && cause.message
            ? cause.message
            : t("common.errors.unknown"),
      );
    } finally {
      setSubmitting(false);
    }
  };

  const copy =
    provider === "claude"
      ? { title: t("accounts.credentialImport.claude.title"), description: t("accounts.credentialImport.claude.description") }
      : {
          title: t("accounts.credentialImport.antigravity.title"),
          description: t("accounts.credentialImport.antigravity.description"),
        };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ProviderLogo provider={provider} />
            {reauth ? t("accounts.signIn.titles.reauth", { name: reauth.name }) : copy.title}
          </DialogTitle>
          <DialogDescription>{copy.description}</DialogDescription>
        </DialogHeader>

        <form className="space-y-4" aria-busy={submitting} onSubmit={(event) => void submit(event)}>
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
              <Input value={name} disabled={submitting} onChange={(event) => setName(event.target.value)} />
            </label>
          )}
          <CredentialFileArea
            files={files}
            disabled={submitting}
            label={t("accounts.credentialImport.fileLabel")}
            onChange={setFiles}
          />
          {acknowledgement ? (
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={acknowledged}
                disabled={submitting}
                onChange={(event) => setAcknowledged(event.target.checked)}
              />
              {acknowledgement}
            </label>
          ) : null}
          {error ? (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive"
            >
              {error}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" disabled={submitting} onClick={close}>
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              disabled={submitting || !file || !accountName || (!!acknowledgement && !acknowledged)}
            >
              {t("common.actions.import")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
