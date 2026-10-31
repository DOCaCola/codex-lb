import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { heldReconnectFrom, type ClaudeAccount, type HeldReconnect } from "./api";
import { IdentityReplaceDialog } from "./identity-replace-dialog";
import { useClaude } from "./use-claude";

type Pending = {
  accountId: string;
  accountName: string;
  held: HeldReconnect;
  resolve: (account: ClaudeAccount) => void;
  reject: (cause: Error) => void;
};

/**
 * Reconnects whose identity differs are held by the server. `guard` turns that hold into a
 * confirmation: it resolves with the replaced account once confirmed and rejects once discarded.
 */
export function useIdentityConfirmation(): {
  guard: (accountId: string, accountName: string, reconnect: () => Promise<ClaudeAccount>) => Promise<ClaudeAccount>;
  dialog: ReactNode;
} {
  const { t } = useTranslation();
  const api = useClaude();
  const [pending, setPending] = useState<Pending | null>(null);
  const busy = api.confirmReconnect.isPending || api.discardReconnect.isPending;

  const guard = async (accountId: string, accountName: string, reconnect: () => Promise<ClaudeAccount>) => {
    try {
      return await reconnect();
    } catch (cause) {
      const held = heldReconnectFrom(cause);
      if (!held) throw cause;
      return new Promise<ClaudeAccount>((resolve, reject) =>
        setPending({ accountId, accountName, held, resolve, reject }),
      );
    }
  };

  const settle = async (confirm: boolean) => {
    if (!pending) return;
    const { accountId, held, resolve, reject } = pending;
    const target = { id: accountId, pendingId: held.pendingId };
    try {
      if (confirm) {
        resolve(await api.confirmReconnect.mutateAsync(target));
      } else {
        await api.discardReconnect.mutateAsync(target);
        reject(new Error(t("accounts.identityReplace.discarded")));
      }
    } catch (cause) {
      reject(cause instanceof Error ? cause : new Error(t("common.errors.unknown")));
    } finally {
      setPending(null);
    }
  };

  const dialog = pending ? (
    <IdentityReplaceDialog
      accountName={pending.accountName}
      held={pending.held}
      busy={busy}
      onConfirm={() => void settle(true)}
      onCancel={() => void settle(false)}
    />
  ) : null;
  return { guard, dialog };
}
