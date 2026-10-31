import { TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { cn } from "@/lib/utils";
import type { HeldReconnect } from "./api";

/** Saved versus incoming identity of a held reconnect, with the differing values highlighted. */
export function IdentityReplaceDialog({
  accountName,
  held,
  busy,
  onConfirm,
  onCancel,
}: {
  accountName: string;
  held: HeldReconnect;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const blurred = usePrivacyStore((s) => s.blurred);
  const unknown = t("accounts.identityReplace.unknown");
  const rows = [
    { label: t("accounts.identityReplace.account"), saved: held.saved.email, incoming: held.incoming.email, private: true },
    {
      label: t("accounts.identityReplace.organization"),
      saved: held.saved.organization,
      incoming: held.incoming.organization,
      private: false,
    },
    {
      label: t("accounts.identityReplace.plan"),
      saved: t(`claude.subscription.${held.saved.plan}`),
      incoming: t(`claude.subscription.${held.incoming.plan}`),
      private: false,
    },
  ];
  const reason = {
    claude_reconnect_account_mismatch: t("accounts.identityReplace.reasons.account"),
    claude_reconnect_organization_changed: t("accounts.identityReplace.reasons.organization"),
    claude_reconnect_identity_unverified: t("accounts.identityReplace.reasons.unverified"),
  }[held.code];

  return (
    <AlertDialog open onOpenChange={(open) => !open && !busy && onCancel()}>
      <AlertDialogContent className="sm:max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <TriangleAlert className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
            {t("accounts.identityReplace.title", { name: accountName })}
          </AlertDialogTitle>
          <AlertDialogDescription>{reason}</AlertDialogDescription>
        </AlertDialogHeader>
        <table className="w-full overflow-hidden rounded-lg border text-xs">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left font-medium" />
              <th className="px-3 py-2 text-left font-medium">{t("accounts.identityReplace.saved")}</th>
              <th className="px-3 py-2 text-left font-medium">{t("accounts.identityReplace.incoming")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const differs = row.saved !== row.incoming;
              const value = (text: string | null) => (
                <span className={row.private && blurred ? "privacy-blur" : undefined}>{text ?? unknown}</span>
              );
              return (
                <tr key={row.label} className="border-t">
                  <td className="px-3 py-2 text-muted-foreground">{row.label}</td>
                  <td className="px-3 py-2">{value(row.saved)}</td>
                  <td
                    className={cn("px-3 py-2", differs && "font-semibold text-amber-700 dark:text-amber-400")}
                    data-differs={differs || undefined}
                  >
                    {value(row.incoming)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="text-xs text-muted-foreground">{t("accounts.identityReplace.consequences")}</p>
        <AlertDialogFooter>
          <Button type="button" variant="outline" disabled={busy} onClick={onCancel}>
            {t("common.cancel")}
          </Button>
          <Button type="button" disabled={busy} onClick={onConfirm}>
            {t("accounts.identityReplace.confirm")}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
