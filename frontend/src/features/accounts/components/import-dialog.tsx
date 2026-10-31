import { useState } from "react";
import type { FormEvent } from "react";
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
import { CredentialFileArea } from "@/features/accounts/components/credential-file-area";

export type ImportDialogProps = {
  open: boolean;
  busy: boolean;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onImport: (file: File) => Promise<void>;
};

export function ImportDialog({
  open,
  busy,
  error,
  onOpenChange,
  onImport,
}: ImportDialogProps) {
  const { t } = useTranslation();
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (files.length === 0) {
      return;
    }

    setSubmitting(true);
    try {
      for (const [index, file] of files.entries()) {
        try {
          await onImport(file);
        } catch {
          setFiles(files.slice(index));
          return;
        }
        setFiles(files.slice(index + 1));
      }

      onOpenChange(false);
      setFiles([]);
    } finally {
      setSubmitting(false);
    }
  };

  const importBusy = busy || submitting;

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => {
      if (!importBusy) onOpenChange(nextOpen);
    }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ProviderLogo provider="codex" />
            {t("accounts.importDialog.title")}
          </DialogTitle>
          <DialogDescription>{t("accounts.importDialog.description")}</DialogDescription>
        </DialogHeader>

        <form className="space-y-4" aria-busy={importBusy} onSubmit={handleSubmit}>
          <CredentialFileArea
            files={files}
            multiple
            disabled={importBusy}
            label={t("accounts.importDialog.fileLabel")}
            onChange={setFiles}
          />

          {error ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive">
              {error}
            </p>
          ) : null}

          <DialogFooter>
            <Button type="button" variant="outline" disabled={importBusy} onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={importBusy || files.length === 0}>
              {files.length > 1
                ? t("accounts.importDialog.importCount", { count: files.length })
                : t("common.actions.import")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
